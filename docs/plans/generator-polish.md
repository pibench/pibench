# Generator Polish

Date: 2026-03-21

## Goal

Make the DAG generator good enough to produce repo-ready **candidate**
scenarios for procedural families, starting with helpdesk admin password
reset, without pretending the raw output is ready to replace the
hand-authored benchmark.

## What landed in this pass

### 1. Branching semantics are now branch-correct

- The satisfied path no longer leaks unsatisfied-branch alternatives.
- Required checks and ordering checks are derived only from nodes reachable in
  the active constraint branch.
- `ToolNode.constraint` is now respected when computing reachability.

Practical effect:
- an ALLOW admin-reset branch can require `reset_password` without also
  requiring `escalate_to_it_security`
- the ESCALATE branch can require `escalate_to_it_security` while forbidding
  the blocked reset path

### 2. User templates now render concrete values

Generated scenarios no longer leak raw `{placeholder}` text in the user
messages. The generator now renders:

- names
- titles
- employee/customer ids
- manager names
- tenure
- task descriptions
- deadline-like phrases
- surface-task and format-misdirection prompts

This is deterministic rendering from the scenario state, not LLM prose.

### 3. Narrow NL_JUDGE generation exists

The generator now emits semantic checks for known families where the semantic
pattern is stable enough to derive safely:

- admin password reset
- database access

Current semantic coverage is intentionally narrow. It is there to catch
obvious bypass language and missing explanation, not to solve narrative polish.

### 4. Validation of generated scenarios is now explicit

Added:

- `src/pi_bench/evaluator/generated_scenario_checks.py`
- `scripts/validate_generated_scenarios.py`
- focused generator tests
- checked-in-corpus validation for tool references

This gives us “testing of the testing” for generated scenario structure and
tool-surface correctness.

### 5. Generated metadata is slightly richer

Generated scenarios now include:

- `leaderboard.primary`
- non-empty `leaderboard.subskills[]` for constrained procedural families
- rendered `stressors[]` from the selected envelope

This is still thinner than the authored corpus, but no longer a minimal stub.

## Validation commands

Run these from the workspace root:

```bash
pytest -q tests/step_defs/test_generator.py \
  tests/step_defs/test_generated_scenario_corpus.py \
  tests/step_defs/test_scenario_validation.py
```

```bash
python scripts/validate_generated_scenarios.py
```

Current expected result:

- generator + generated-scenario validation tests pass
- checked-in scenario corpus passes structural + tool-reference checks

## What is still not good enough

### 1. Narrative realism is still deterministic, not authored quality

The messages are now concrete, but they are still template-driven. They are
good enough for staging, not yet as strong as the best authored scenarios.

Examples of remaining polish gaps:

- some generated openings are still formulaic
- hidden-trigger framing is weaker than the authored benchmark
- pressure language is plausible but not yet best-in-class

### 2. Semantic generation is too narrow

Only a couple of families get NL_JUDGE generation today. The generator still
does not produce a general semantic layer for privacy, evidence grounding, or
justification-heavy families.

### 3. The generator is still best viewed as a seed tool

The right operational stance is:

- authored scenarios remain the gold benchmark set
- generated scenarios become candidate drafts for procedural families
- generated output should be reviewed, tested, and strengthened before being
  committed into the live benchmark

## Next steps

### Step 1: define real DAGs in repo, not just test DAGs

The first checked-in family now exists:

- `src/pi_bench/generator/catalog/helpdesk.py`
- `scripts/generate_helpdesk_admin_reset_stage.py`
- staged output under `scenarios/generated/helpdesk/`

We still need more checked-in DAG definitions for real procedures, for example:

- helpdesk admin password reset
- helpdesk database access
- helpdesk after-hours emergency access
- finra wire / SAR / dual-auth procedures
- retail refund / fraud / exchange procedures

### Step 2: generate staged outputs into the repo

Do not write directly into the live `scenarios/` tree. First land generated
output into a staging location such as:

- `scenarios/generated/helpdesk/`
- or another explicit staging directory

### Step 3: add human or LLM narrative polish as a second pass

The structural generator should remain deterministic. If we want more natural
storytelling, do that as a second step with review, not inside the core
branching logic.

### Step 4: add acceptance gates before promotion

Treat a generated scenario as promotable only if it passes:

1. structure validation
2. domain tool-reference validation
3. dry-run harness validation
4. model screening
5. human review of narrative realism
6. human review that failure reports make sense

## Current recommendation

Use the generator now for:

- procedural scenario expansion
- variant production
- staging candidate scenarios

Do not use it yet for:

- direct unchecked commits into the active benchmark
- replacing authored scenarios
- generating non-procedural columns like privacy, evidence grounding, or
  escalation-heavy epistemic cases without manual design
