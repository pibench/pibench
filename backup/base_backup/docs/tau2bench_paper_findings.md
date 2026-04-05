# tau2-bench Paper: Experimental Findings

Source: τ2-Bench — Evaluating Conversational Agents in Dual-Control
Settings (2025)

## The Central Idea

Both the agent and the user can mutate the shared world state. Neither
can do the other's job. The agent can't reach through and toggle the
user's airplane mode. The user can't reach into the CRM and enable
roaming. Solving problems requires coordinated actions from both
sides, mediated entirely through natural language conversation.

Everything in the paper flows from this one design choice.

## Experiments

### 1. Main Benchmark Evaluation

**Setup:**
- Domains: retail, airline (from τ-bench), plus new telecom domain
  (dual-control)
- Models tested as agents: gpt-4.1-mini, gpt-4.1, o4-mini,
  claude-3.7-sonnet
- User simulator: gpt-4.1
- 4 runs per task, temperature 0
- Metric: pass^k = fraction of tasks solved in k independent runs
  (pass^1 = solved on one try; pass^4 = solved reliably across 4 tries)

**Findings:**
- Telecom is significantly harder than retail or airline
- gpt-4.1 pass^1 drops from 74% (retail) to 34% (telecom)
- As reliability demand increases (higher k), telecom performance
  drops faster

### 2. Ablation: Reasoning vs Coordination

**Three modes tested on telecom:**

| Mode | Description |
|---|---|
| **Default** | Dual-control: agent + user collaborate, user has own tools |
| **No-User** | Agent uses all tools (including user-side). Isolates reasoning from coordination |
| **Oracle Plan** | Agent receives the correct tool call sequence. Tests execution + collaboration |

**Key result:** No-User → Default causes 18-25% pass^1 drop.
- gpt-4.1: ~18% drop
- o4-mini: ~25% drop

**Interpretation:** Models reason through problems fine when they
control both sides. The act of communicating intent, delegating
actions, interpreting feedback, and adapting across the agent/user
boundary is what breaks them. World-state mutation isn't hard.
Coordination of who mutates what and when is what's hard.

### 3. Policy Document Variant

**Setup:** Compare "original" policy vs more step-by-step
"workflow-based" policy.

**Findings:**
- Workflow policy slightly helps in Default and No-User modes
- Workflow policy can *hurt* in Oracle Plan mode
- Hypothesis: explicit workflow confuses the agent when it already
  has the gold plan — the rigid text becomes noise that conflicts
  with the correct sequence

**Implication for pi-bench:** More explicit/structured policy text
doesn't always help. Messy, realistic policy text is the right test
condition. Over-structuring can actually degrade performance.

### 4. Difficulty Scaling

Performance broken down by task complexity:

**By action count:**
- Success falls as required actions increase
- Default mode approaches zero success beyond ~7 actions
- Each step across the coordination boundary compounds failure
  probability — it's not that step 7 is harder than step 1, it's
  that the probability of staying coordinated multiplies down

**By number of sub-issues (subtasks):**
- More combined issues → lower success
- Compositional tasks are harder than simple ones

**By issue type:**
- service_issue: easiest
- mobile_data_issue: harder (often depends on solving service first)
- mms_issue: hardest (requires fixing service, then data, then
  MMS-specific config)

**By user persona:**
- "Easy" personas (tech-comfortable users) yield better scores
- "Hard" personas (tech-anxious elderly users) yield worse scores
- "None" (no persona) is often as bad or worse than "Hard"
- Interpretation: a hard persona gives the agent something to
  calibrate against. No persona means unpredictable behavior, which
  is harder to coordinate with

### 5. User Simulator Reliability

**Setup:** Manual review of conversations, labeling simulator errors
as critical (break the task) vs benign.

**Findings:**
- Telecom user simulator: 16% error rate (6% critical)
- Retail/airline user simulators: 40-47% error rate

**Why the difference:** In telecom, the user's behavior is
constrained by actual tools and observable state — the user *can*
toggle airplane mode or *can't*, and the simulator respects that. In
retail/airline, the user relies entirely on natural language
prompting, which allows more drift.

**Implication:** Giving users real tools (the dual-control design)
doesn't just make the benchmark harder — it makes the user simulation
more reliable as a methodology.

## Paper's Conclusions

1. **Dual-control is a missing piece in agent evaluation.** It better
   matches real support settings where resolution requires actions
   from both parties.

2. **Coordination/communication is a primary weakness of today's
   models**, not only reasoning. The 18-25% ablation gap proves this.

3. **Constraining the user via tools + observable state** makes user
   simulation more reliable (16% vs 40-47% error rate), but more
   work remains.

4. **Limitations acknowledged:**
   - Domain creation still requires significant human effort
   - The benchmark doesn't fully capture the "expert explaining to
     novice" gap
   - Extending dual-control to other domains is future work

## What This Means for pi-bench

**What carries over:**
- The dual-control environment structure — we need it, we're building it
- Difficulty scaling by action count — useful for calibrating scenario
  complexity
- User persona dimension — maps to our "pressure conditions" column
  in the evaluation matrix
- User simulator reliability finding — tools constrain behavior
  better than prompts alone

**What doesn't carry over:**
- pass^k as primary metric — we use compliance rate, over/under-refusal,
  escalation accuracy, attempt rate
- Task completion framing — we care about judgment under ambiguity,
  not task success
- Oracle Plan mode — irrelevant when the question is "should you do
  this at all?" rather than "can you do this?"

**The distinction:** tau2 asks "can the agent solve this task through
coordination?" Pi-bench asks "does the agent comply with policy
constraints while attempting to coordinate?" The environment primitive
is the same. The question we ask inside that environment is different.
