# PI-BENCH Evaluation Alignment Blueprint

> Bring the evaluation codebase into full alignment with `pi-bench-evaluation-spec.md`.
> tau2-bench is the North Star reference, but pi-bench diverges intentionally:
> single environment, policy-focused scoring, no dual-control model.

---

## Context

The evaluation spec defines what pi-bench's scoring system SHOULD do.
A trace audit (2026-03-08) found 8 concrete gaps between spec and code.
The codebase is well-structured (~7K LOC, 22 modules, BDD tests) — this
is alignment work, not a rewrite.

**Reference system:** tau2-bench (dual environment, bilateral task completion)
**This system:** pi-bench (single environment, policy compliance testing)

---

## Goals

1. Every spec claim is either implemented or the spec is corrected
2. Zero code duplication between evaluate() and scenario_checker paths
3. scenario_validator runs in the runtime path (not dead code)
4. LLM judge meets its bounding contract (retry, timeout, caching)

## Non-goals

- Merging evaluate() and scenario_checker paths (spec Section 5 says "don't merge yet")
- Adding dual-environment support (deliberate pi-bench design decision)
- Rewriting the orchestrator or agent protocols
- Adding new evaluator types

---

## Phase 1: Fix Spec/Code Disagreements (Day 1)

Two places where spec and code disagree. Decide which is right, update the wrong one.

### 1A. Decision Recording: "first wins" vs "last wins"

**Spec says:** first call wins if values agree; InvalidRun if values conflict.
**Code does:** last call wins, always. Comment explains why: "Models legitimately
update their decision as conversations evolve."

**Recommendation:** Code is right. Update spec Section 4.2 to match.
The "last wins" design handles real-world agent behavior where the agent
refines its decision as the conversation progresses.

**File:** `~/Spaces/vjl/zpersonal_workspace/zpersonal_analysis/pi-bench-evaluation-spec.md`
**Change:** Section 4.2 — replace "first call wins" with "last call wins"
and remove mention of `MULTIPLE_DECISIONS_TOOL` for tool-channel decisions.

### 1B. Remove dead InvalidRun reason

**File:** `src/pi_bench/decision/__init__.py`
**Change:** Remove or document that `MULTIPLE_DECISIONS_TOOL` is only
for JSON-channel decisions (which IS still used at line 64-65).
Actually — no change needed in code. The reason string exists in the
dataclass and IS used for JSON-channel. Just clarify in spec.

**Effort:** ~30 min. No code changes needed, just spec update.

---

## Phase 2: Wire Up Scenario Validation (Day 1)

The validator exists but nobody calls it. Fix that.

### 2A. Call validator before evaluation

**Where to wire it in:** Two call sites need validation:
1. `run_scenarios.py:run_scenario()` — after `load()`, before `run()`
2. `a2a/assessment.py:_run_single_scenario()` — after `load()`, before `orchestrator_run()`

**Function:** `scenario_validator.validate_scenario(scenario_data)`

**Behavior on validation failure:**
- Log all errors
- Return an error result (don't run the scenario)
- Status: `"validation_error"`

**Files to modify:**
- `src/pi_bench/run_scenarios.py` — add import + validation call in `run_scenario()`
- `src/pi_bench/a2a/assessment.py` — add import + validation call in `_run_single_scenario()`

**Test:** Add a BDD scenario: "Given a scenario with empty args_match / When
validated / Then validation rejects it before running"

**Effort:** ~1 hour

---

## Phase 3: LLM Judge Bounding (Day 1-2)

Three missing capabilities in `llm_judge.py`.

### 3A. Add retry on parse failure

**File:** `src/pi_bench/evaluator/llm_judge.py`
**Function:** `judge_nl_assertion()` — after `_parse_judge_response()` returns None,
retry the LLM call once before returning failure.

```python
# Signature stays the same
def judge_nl_assertion(assistant_text, question, expected_answer) -> tuple[bool, str]:
    ...
    answer, reasoning = _parse_judge_response(raw)
    if answer is None:
        # ONE retry on parse failure
        raw = _call_judge(messages)  # extract the litellm call
        answer, reasoning = _parse_judge_response(raw)
    if answer is None:
        return False, f"llm_judge unparseable after retry: {raw[:200]}"
    ...
```

### 3B. Add timeout

**File:** `src/pi_bench/evaluator/llm_judge.py`
**Change:** Pass `timeout=30` to `litellm.completion()`.

```python
response = litellm.completion(
    model=_JUDGE_MODEL,
    messages=messages,
    temperature=0.0,
    max_tokens=512,
    timeout=30,  # spec: 30s per assertion
)
```

### 3C. Add per-run caching

**File:** `src/pi_bench/evaluator/llm_judge.py`
**Design:** Simple dict cache keyed on `(text_hash, question)`. Cache lives
for the duration of one scenario evaluation (not persisted).

```python
_judge_cache: dict[tuple[str, str], tuple[bool, str]] = {}

def clear_judge_cache() -> None:
    _judge_cache.clear()

def judge_nl_assertion(...) -> tuple[bool, str]:
    cache_key = (hashlib.md5(assistant_text.encode()).hexdigest(), question)
    if cache_key in _judge_cache:
        return _judge_cache[cache_key]
    ...
    result = (passed, detail)
    _judge_cache[cache_key] = result
    return result
```

**Cache clearing:** Call `clear_judge_cache()` at the start of each scenario run
in `run_scenarios.py:run_scenario()` and `a2a/assessment.py:_run_single_scenario()`.

**Test:** BDD scenario: "Given the same NL assertion called twice / When judge
evaluates / Then LLM is called only once"

**Effort:** ~2 hours

---

## Phase 4: Eliminate Code Duplication (Day 2)

### 4A. Extract `_outcomes_to_policy_checks()`

**Current:** Duplicated identically in `run_scenarios.py` and `a2a/assessment.py`.

**Move to:** `src/pi_bench/evaluator/scenario_checker.py` (it already handles outcomes)

```python
# New public function in scenario_checker.py
def outcomes_to_policy_checks(outcomes: list[dict]) -> list[dict]:
    """Convert scenario outcomes to policy_checks format for event_flags."""
    ...  # existing logic, unchanged
```

**Then update:**
- `run_scenarios.py` — `from pi_bench.evaluator.scenario_checker import outcomes_to_policy_checks`
- `a2a/assessment.py` — same import

Delete the private `_outcomes_to_policy_checks()` from both files.

### 4B. Extract `_extract_content()`

**Current:** Duplicated in `scenario_checker.py` and `nl_assertion.py`.

**Move to:** `src/pi_bench/types.py` (it already has message factory functions)

```python
# New function in types.py
def extract_message_content(msg: dict) -> str:
    """Extract text content from a message, handling string and list formats."""
    content = msg.get("content", "")
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return content if isinstance(content, str) else ""
```

**Then update:**
- `scenario_checker.py` — import and use `extract_message_content`
- `nl_assertion.py` — import and use `extract_message_content`

### 4C. Fix COMMUNICATE list content handling

**File:** `src/pi_bench/evaluator/communicate.py`
**Change:** Use the new `extract_message_content()` instead of inline string check.

```python
from pi_bench.types import extract_message_content

def evaluate_communicate(communicate_info, trajectory):
    ...
    for msg in trajectory:
        if msg.get("role") == "assistant" and msg.get("content"):
            agent_text += " " + extract_message_content(msg)
    ...
```

This fixes the inconsistency where COMMUNICATE silently skipped list content
while all other evaluators handled it.

**Effort:** ~1.5 hours

---

## Phase 5: Test Coverage for Gaps (Day 2-3)

### 5A. Scenario validation BDD feature

**File:** `tests/features/scenario_validation.feature`

Scenarios:
- Valid scenario passes validation
- Missing decision_equals → rejected
- Empty args_match on tool_called_with → rejected
- Missing expected_answer on nl_assertion_llm_judge → rejected
- Invalid label → rejected
- Validation runs before evaluation in runtime path

### 5B. LLM judge bounding tests

**File:** `tests/step_defs/test_llm_judge.py`

Scenarios:
- Retry on unparseable response
- Timeout enforcement (mock slow response)
- Cache hit on repeated (text, question) pair
- Cache cleared between scenarios

### 5C. COMMUNICATE list content test

Add to existing `tests/features/evaluation.feature`:
- "Given assistant messages in Anthropic list format / When COMMUNICATE
  evaluates / Then required strings are found"

**Effort:** ~3 hours

---

## Phase Summary

| Phase | What | Files Changed | Effort | Risk |
|-------|------|--------------|--------|------|
| 1 | Fix spec/code disagreement | spec only | 30 min | None |
| 2 | Wire up validator | run_scenarios.py, assessment.py | 1 hr | Low |
| 3 | LLM judge bounding | llm_judge.py, run_scenarios.py, assessment.py | 2 hr | Medium (litellm timeout behavior) |
| 4 | DRY violations + COMMUNICATE fix | scenario_checker.py, nl_assertion.py, types.py, communicate.py, run_scenarios.py, assessment.py | 1.5 hr | Low |
| 5 | Test coverage | 3 new test files | 3 hr | None |

**Total estimated effort:** ~8 hours across 2-3 days

---

## Contract Coverage

Every spec section mapped to a phase:

| Spec Section | Status Before | Phase | Status After |
|---|---|---|---|
| 1.1 Determinism | ✅ Implemented | — | ✅ |
| 1.2 Two-Tier Scoring | ✅ Implemented | — | ✅ |
| 1.3 NL Judge Bounding | ⚠️ Partial (2/5) | 3 | ✅ |
| 1.4 Single Environment | ✅ Implemented | — | ✅ |
| 2.1 ACTION | ✅ Implemented | — | ✅ |
| 2.2 DB | ✅ Implemented | — | ✅ |
| 2.3 COMMUNICATE | ⚠️ List content gap | 4C | ✅ |
| 2.4 ENV_ASSERTION | ✅ Implemented (F2,F3) | — | ✅ |
| 2.5 NL_ASSERTION | ✅ Implemented | — | ✅ |
| 2.6 POLICY | ✅ Implemented (D1-D3) | — | ✅ |
| 3.x Scoring Functions | ✅ Implemented | — | ✅ |
| 4.1 Pressure Clause | ✅ In policy docs | — | ✅ |
| 4.2 Decision Recording | ❌ Spec wrong | 1 | ✅ (spec fixed) |
| 4.3 Audit/Hard-Gate | ✅ Implemented | — | ✅ |
| 5 Merge Decision | ✅ Both paths exist | — | ✅ |
| 6 Scenario Validation | ❌ Dead code | 2 | ✅ |
| 7 Implementation | ⚠️ DRY violations | 4 | ✅ |

## NOT Building

- Dual environment (tau2-bench has this; pi-bench deliberately doesn't — Spec 1.4)
- Gold action sequences (not needed for policy compliance testing)
- Weighted average scoring (spec Section 3.4 explains why multiplicative is correct)
- evaluate() + scenario_checker merge (spec Section 5 says "don't merge yet")
- New evaluator types or outcome types
