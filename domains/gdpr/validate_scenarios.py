"""Validate GDPR scenarios by construction (no model involved).

For each scenarios/gdpr/*.json:
  1. schema/consistency rules (pi_bench scenario_validator);
  2. the scenario's `validation.gold` trajectory, executed against the real
     environment and scored by the real evaluator, passes every
     deterministic (Tier-1) check;
  3. every `validation.violations[]` trajectory fails, and fails exactly the
     checks it lists in `must_fail`;
  4. leakage lint on the user-simulation fields and the agent-visible task;
  5. coverage tags point at real ontology ids;
  6. distinctness: no two scenarios share the same construct signature.

Usage: python3 domains/gdpr/validate_scenarios.py [scenario.json ...]
Exit code 0 = all valid.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from pi_bench.evaluator import evaluate  # noqa: E402
from pi_bench.evaluator.scenario_validator import validate_scenario  # noqa: E402
from pi_bench.observer import create_observer, observed_tool_call  # noqa: E402
from pi_bench.orchestrator.core import build_benchmark_context  # noqa: E402
from pi_bench.scenario_loader import load  # noqa: E402
from pi_bench.trace import TraceRecorder  # noqa: E402

ONTOLOGY = json.load(open(ROOT / "domains/gdpr/ontology/gdpr_ontology.json"))
ONT_IDS = {n["id"] for n in ONTOLOGY["nodes"]}
TOOLS = {t["name"] for t in json.load(open(ROOT / "domains/gdpr/tools.json"))["tool_definitions"]}
PLAN = {t["id"]: t for p in sorted((ROOT / "domains/gdpr/coverage/waves").glob("wave*_plan.json"))
        for t in json.load(open(p))["targets"]}
ROLE_LEAK = re.compile(r"\b(ALLOW|DENY|ESCALATE)\b|should refuse|must refuse|correct answer|be careful")
LEAK = re.compile(r"\b(ALLOW|DENY|ESCALATE|escalat\w*|the agent should|should refuse|should deny|must refuse|correct answer)\b", re.I)
TIER2 = {"NL_JUDGE", "NL_ASSERTION"}


def run(path: Path, trajectory: dict) -> dict:
    loaded = load(path, ROOT)
    env, task = loaded["env"], copy.deepcopy(loaded["task"])
    trace = TraceRecorder()
    obs = create_observer(env, trace, forbidden_tools=set(loaded["forbidden_tools"] or []))
    for i, call in enumerate(trajectory.get("calls", [])):
        observed_tool_call(obs, call["tool"], call_id=f"c{i}", arguments=call.get("args", {}))
    messages = [{"role": "assistant", "content": m} for m in trajectory.get("messages", [])]
    for m in messages:
        trace.add_message("assistant", m["content"])
    ec = task["evaluation_criteria"]
    ec["reward_basis"] = [b for b in ec.get("reward_basis", []) if b not in TIER2]
    sim = {"termination_reason": "user_stop", "trace": trace, "messages": messages, "env": env}
    return evaluate(task, sim, domain={"get_environment": lambda *_a, **_k: load(path, ROOT)["env"]})


def failed_ids(result: dict) -> set[str]:
    return {r.get("outcome_id") for r in result.get("outcome_results", []) if not r.get("passed")}


def check(path: Path) -> list[str]:
    errors: list[str] = []
    sc = json.loads(path.read_text())
    errors += [f"schema: {e}" for e in validate_scenario(sc)]
    v = sc.get("validation") or {}
    if not v.get("gold") or not v.get("violations"):
        errors.append("validation: needs a gold trajectory and at least one violation")
        return errors
    try:
        gold = run(path, v["gold"])
        if not gold["all_passed"]:
            errors.append(f"gold trajectory fails: {sorted(failed_ids(gold))}")
        for viol in v["violations"]:
            res = run(path, viol)
            got = failed_ids(res)
            if res["all_passed"]:
                errors.append(f"violation '{viol.get('name')}' passes all checks")
            missing = set(viol.get("must_fail", [])) - got
            if missing:
                errors.append(f"violation '{viol.get('name')}' should fail {sorted(missing)} but failed {sorted(got)}")
    except Exception as exc:  # environment or evaluator error is a scenario defect
        errors.append(f"execution error: {type(exc).__name__}: {exc}")
    planned = PLAN.get(sc.get("meta", {}).get("scenario_id"))
    if planned and planned.get("label") != sc.get("label"):
        errors.append(f"plan: label {sc.get('label')} differs from the wave plan ({planned.get('label')})")
    ec = sc.get("evaluation_criteria", {})
    for chk in ec.get("policy_checks", []) + ec.get("state_field_checks", []):
        names = [chk.get(k) for k in ("tool_name", "first_tool", "second_tool") if chk.get(k)]
        names += list(chk.get("tool_names", []) or []) + list(chk.get("first_tools", []) or [])
        for name in names:
            if name not in TOOLS:
                errors.append(f"check {chk.get('outcome_id')}: unknown tool '{name}'")
    for chk in ec.get("nl_judge_checks", []):
        scope = chk.get("scope", "assistant_messages")
        if scope.startswith("tool_call:") and scope.split(":", 1)[1] not in TOOLS:
            errors.append(f"check {chk.get('outcome_id')}: judge scope names unknown tool")
    m = ROLE_LEAK.search(str(sc.get("environment_setup", {}).get("agent_role", "")))
    if m:
        errors.append(f"leak lint: agent_role contains '{m.group(0)}'")
    for call in [c for t in [v.get("gold", {})] + v.get("violations", []) for c in t.get("calls", [])]:
        if call.get("tool") not in TOOLS:
            errors.append(f"validation: unknown tool '{call.get('tool')}' in a trajectory")
    us = sc.get("user_simulation", {})
    for field in ("goal", "rules", "known_facts", "initial_user_message", "pressure"):
        m = LEAK.search(json.dumps(us.get(field, ""), ensure_ascii=False) if isinstance(us.get(field), dict) else str(us.get(field, "")))
        if m:
            errors.append(f"leak lint: user_simulation.{field} contains '{m.group(0)}'")
    try:
        loaded = load(path, ROOT)
        visible = "\n".join(n["content"] for n in build_benchmark_context(loaded["env"], loaded["task"]) if n["kind"] != "policy")
        if sc["meta"]["scenario_id"] in visible or (sc["meta"].get("notes") and sc["meta"]["notes"] in visible):
            errors.append("leak: scenario id or notes visible to the agent")
    except Exception as exc:
        errors.append(f"load error: {exc}")
    cov = sc.get("coverage") or {}
    for key in ("rules", "conditions_true", "conditions_false", "failure_modes_nodes"):
        for ref in cov.get(key, []) or []:
            if ref not in ONT_IDS:
                errors.append(f"coverage: unknown ontology id {ref} in {key}")
    for edge in cov.get("rule_edges", []) or []:
        if not any(e["source"] == edge[0] and e["type"] == edge[1] and e["target"] == edge[2] for e in ONTOLOGY["edges"]):
            errors.append(f"coverage: edge {edge} not in ontology")
    if not cov.get("construct"):
        errors.append("coverage: missing construct statement")
    return errors


def signature(sc: dict) -> tuple:
    c = sc.get("coverage", {})
    return (sc.get("label"), tuple(sorted(c.get("rules", []))), tuple(sorted(c.get("conditions_true", []))),
            tuple(sorted(c.get("conditions_false", []))), tuple(sorted(c.get("difficulty", []))))


def main(paths: list[Path]) -> int:
    paths = paths or sorted((ROOT / "scenarios" / "gdpr").glob("*.json"))
    bad = 0
    sigs: dict[tuple, str] = {}
    for p in paths:
        errs = check(p)
        sc = json.loads(p.read_text())
        sig = signature(sc)
        if sig in sigs:
            errs.append(f"duplicate construct signature with {sigs[sig]}")
        sigs[sig] = p.name
        status = "OK " if not errs else "BAD"
        print(f"{status} {p.name}")
        for e in errs:
            print(f"     - {e}")
        bad += bool(errs)
    print(f"\n{len(paths) - bad}/{len(paths)} valid")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main([Path(a) for a in sys.argv[1:]]))
