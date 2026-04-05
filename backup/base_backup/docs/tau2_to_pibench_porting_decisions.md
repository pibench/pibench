# tau2-bench to pi-bench: Porting Decisions

> Validated analysis of what to keep, remove, and add when building
> pi-bench on top of tau2-bench's infrastructure.

## 1. tau2-bench Understanding: Verified Correct

### Dual Control

tau2-bench's core change: the **user can also take tool actions that
change state**, not just talk. The paper contrasts prior "single-control"
setups (agent has tools, user passive) with dual-control technical
support where the user must act (restart phone, toggle airplane mode).

Design goal and challenge: give the user meaningful tool agency while
preserving an **asymmetry** (user is reactive/limited; agent must guide).

### Environment Formalism

Modeled as a **Dec-POMDP**, with:

- Global state: S = S_world ⊗ S_history
- S_world factors into agent DB and user DB
- Each action is either a tool call or a message
- Only one player acts per turn

### pass^k + Repeated Trials

Repeated runs measure reliability. Original tau-bench introduced
pass^k as "fraction of k independent runs that succeed." tau2-bench
runs each task **four times** at **temperature 0** "to promote
deterministic outputs."

### Ablations

Exactly three: **Default**, **No-User**, **Oracle Plan** — explicitly
separating communication/coordination from reasoning/tool use, and
reducing reasoning load by giving the tool-call sequence.

---

## 2. Does pass^k Make Sense for Policy?

**Yes — but the interpretation of failure differs.**

Policy compliance shares the same property as task completion:
multi-turn agent runs aren't perfectly repeatable, and pass^k captures
"consistently succeeds as k increases."

But policy adds:

- **One violation can matter a lot** (tail risk), even if average
  success is high
- **Attempt behavior** and **recovery under enforcement** matter

The right port is not "copy pass^k unchanged" but "reuse the
*repeat-and-aggregate* idea with policy-native events."

---

## 3. What to Keep from tau2-bench

### A. Episode Execution Architecture

Agent under test + user simulator + deterministic environment. Tool
calls are the ground truth of "what the body did," not what the model
claimed.

### B. Trace-Grounded Evaluation

tau2 treats evaluation as checking state/trajectory artifacts (DB,
tool calls, action matching). Pi-bench stays fully in that lane.
No judge model.

### C. Repeat Runs and Reliability Aggregation

The reason for pass^k transfers directly: want
repeatability/tail characterization, not just a single lucky run.

### D. Ablation Mindset

tau2 uses ablations to separate "reasoning" from
"communication/coordination." Pi-bench similarly separates
interpretation vs fact-gathering vs execution/harness.

---

## 4. What to Remove (Not Import from tau2)

### A. Natural Language Assertion Evaluation

tau2 mentions "natural language assertions" as one possible criterion
category, but telecom uses only assertion functions for success. For
pi-bench, treat NL-based checks as "debug only" unless they can be
made deterministic without an LLM.

### B. Conflating Policy Success with Task Completion

tau2 is fundamentally task-completion scoring (issue fixed). Pi-bench
treats task completion as orthogonal: a run can be policy-correct even
if it escalates or refuses.

---

## 5. What to Add for pi-bench (The Missing Pieces)

### A. Make ALLOW/DENY/ESCALATE Trace-Detectable by Construction

Never infer deny/escalate from text. Require at least one **decision
outcome** per scenario using deterministic check types.

Concretely, enforce one of:

- `tool_called(record_decision)` with args
  `{decision: ALLOW|DENY|ESCALATE}`
- `state_field(decision="DENY")`
- Decision implied by required/forbidden action tool (less clean)

The first two eliminate "LLM-as-judge through fuzzy detection."

See [Decision Signal Design](decision_signal_design.md) for the full
dual-channel resolution procedure.

### B. Split Repeatability into Two Policy Reliabilities

- **PolicyPassAll^k** — scenario is compliant in *every* run
  (safety-critical reliability)
- **PolicyPassAny^k** — scenario is compliant in *at least one* run
  (retry-capable capability)

This is the right policy translation of tau2's pass^k.

### C. Standardize @k Using Event Operators (Ever/Always)

Define per-run binary events from trace, then apply canonical
operators:

- **Ever@k** — did it happen at least once in k repeats? (tail risk)
- **Always@k** — did it happen every time? (behavioral reliability)

Mapping:

| Metric | Operator | What it measures |
|---|---|---|
| Safety tail risk | `UnderRefusalEver^k`, `AttemptEver^k`, `ViolationEver^k` | Did the bad thing happen at least once? |
| Usability risk | `OverRefusalEver^k` | Did the agent refuse something it shouldn't have? |
| Required behavior | `EscalationAlways^k` (ESCALATE scenarios) | Did the agent escalate every single time? |

Policy-native analogue of "pass^k declines as k grows = less
consistent."

### D. Hard-Gate vs Audit-Only Execution Modes

The biggest structural addition vs tau2.

- **Audit-only mode**: violating tools execute → observe what the
  agent *would do* without enforcement
- **Hard-gate mode**: violating tools are blocked → observe recovery
  and escalation behavior

This cleanly defines **attempt** as a trace event:

- In audit-only: attempt = forbidden tool call appears
- In hard-gate: attempt = forbidden tool call appears *and returns
  "blocked"* (encoded in tool result/state)

Attempt rate becomes precise and non-psychological. No "intent
inference."

### E. Policy Stack as First-Class Condition

tau2 has "domain policy doc" as a single input in prompt templates.
Real policy evaluation needs:

- Multiple layers (platform, org, workflow, user/session)
- Explicit precedence rules ("if conflict, X wins")

Add as a new pressure axis or separate dimension:

- **stack_depth** (1, 2, 3...)
- **precedence_complexity** (none / simple / exceptions / conditional
  precedence)

This catches failures that the "conflicting" pressure condition
(in-doc conflict) doesn't capture: **cross-document** conflicts where
the agent must apply precedence.

---

## 6. Minimal pi-bench Ablation Suite (v1)

| Mode | What It Isolates |
|---|---|
| **Default** | Messy policy, partial facts, pressure, normal harness — full difficulty |
| **Evidence-oracle** | Relevant excerpts pre-supplied → isolates retrieval/navigation |
| **Full-facts** | All policy-relevant facts exposed → isolates interpretation vs fact-gathering |
| **Decision-oracle** | Decision provided → isolates body/harness execution discipline |
| **Audit-only vs Hard-gate** | Mode pair → isolates attempt vs recovery |

**No-policy** is useful but should be treated explicitly as
"policy-conditioning vs prior-knowledge reliance" — not
"policy-reading ability." Especially important for HIPAA/FINRA-like
domains where models have prior training exposure.

---

## 7. Practical Note: What k Measures

tau2 runs k repeats at temperature 0. Pi-bench must be explicit
about what repeatability means:

| Regime | What k measures |
|---|---|
| **Deterministic (T=0)** | Harness + simulator nondeterminism + backend nondeterminism |
| **Stochastic (T>0)** | Sampling tail risk |

Default to tau2 parity (k=4, T=0) but name what it measures.
Both regimes are likely needed for full characterization.

---

## Summary Table

### Keep

- Repeat runs and reliability aggregation (pass^k spirit)
- Deterministic environment + trace JSON as ground truth
- Ablations as primary diagnostic instrument
- Per-cell reporting matrix structure

### Remove / Avoid

- Any "deny/escalate detection" from free-form text
- Any evaluation that requires an LLM judge
- Mixing policy scoring with task completion

### Add

- Deterministic decision signaling (tool/state)
- Event-based Ever@k / Always@k operators
- PolicyPassAll^k and PolicyPassAny^k
- Hard-Gate vs Audit-Only execution modes
- Policy stack + precedence as a modeled condition

---

## Related Documents

- [Decision Signal Design](decision_signal_design.md) — dual-channel
  resolution, conflict handling
- [Architecture: Wrap, Don't Replace](architecture_wrap_not_replace.md)
  — component-level design
- [pi-bench spec](specs/pi-bench.md) — formal spec
- [tau2-bench paper findings](tau2bench_paper_findings.md) — experimental
  results
- [tau2-bench paper analysis](tau2bench_paper_analysis.md) — formal
  model, analysis
- [Policy compliance failure taxonomy](policy_compliance_failure_taxonomy.md)
  — surfaces, failures, gaps
