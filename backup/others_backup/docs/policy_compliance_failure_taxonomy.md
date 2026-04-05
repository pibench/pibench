# First-Principles Taxonomy of Policy Compliance Failure in AI Agent Systems

AI agents fail at policy compliance through three independent layers
— interpretation, orchestration, and execution — and current
benchmarks test barely half the failure surface.

This report provides a complete decomposition of how policy compliance
breaks in AI agent systems, maps 19 existing benchmarks against that
taxonomy, and designs six ablation studies that isolate each failure
axis independently.

Sources: tau2-bench methodology, OWASP Top 10 for Agentic Applications
(2026), NIST AI 600-1, pi-bench specification, and the research cited
throughout.

---

## Part 1: The Ten Policy Surfaces

Enterprise AI agents don't operate under a single policy regime. They
operate under overlapping, sometimes contradictory layers of obligation
spanning legal mandates, industry certifications, internal procedures,
and ad hoc business rules.

### 1. Regulatory Mandates

HIPAA, FINRA, EU AI Act, GDPR, SOX, AML/KYC, FDA. Backed by legal
penalties — up to 35M EUR or 7% global turnover under the EU AI Act.
FINRA's 2026 Regulatory Oversight Report names AI agent autonomy,
auditability of multi-step reasoning, and unintentional data exposure
as top risks. HIPAA demands 6-7 year log retention for every PHI
access.

Key properties: temporal dependencies (staggered EU AI Act deadlines
from Feb 2025 through Aug 2027), cross-references between regulatory
documents, and jurisdictional scope rules that vary by user location.

### 2. Industry Standards

PCI-DSS 4.0, SOC 2, ISO 27001, NIST frameworks. PCI-DSS 4.0 now
mandates MFA for all Cardholder Data Environment access and requires
remediation of all vulnerabilities (not just critical/high). ISO
42001 (Dec 2023) is the first certifiable AI management system
standard with 38 specific controls. SOC 2 and ISO 27001 share
53-95% control overlap — creating a compliance challenge where agents
must reason about the same constraint expressed in different
vocabularies across different policy documents.

### 3. Standard Operating Procedures

Step-by-step workflows with verification gates, approval chains, and
conditional branching. SOPBench (2025) found even frontier agents
score poorly: FC agents 27% and ReAct agents 48% on SOP compliance.

The distinctive challenge is ordering: calling a service function
before its prerequisite verification function is a hard failure
regardless of the final outcome. SOPs also embed implicit domain
knowledge — a refund SOP may assume understanding of product tiers,
seasonal promotions, and customer segmentation that is never stated.

### 4. Enterprise Organizational Policies

Data handling, access control, escalation procedures, customer
interaction guidelines. Only 29% of organizations have comprehensive
AI governance plans (Diligent Q4 2025), and 82% deploy AI agents
while only 44% have security policies. Shadow AI compounds the
problem: 65% of enterprise AI tools operate without IT approval,
each creating unmonitored policy violations.

### 5. Authorization Policies

RBAC, ABAC, Cedar, OPA/Rego. These differ from other surfaces because
they have mature formal enforcement mechanisms. Cedar provides
sub-millisecond, formally verified authorization decisions with
deny-by-default semantics. OPA/Rego handles complex policy logic but
Trail of Bits found it "expressive but error-prone, failing several
tests due to runtime exceptions, non-determinism, and extensibility
risks."

Key challenge for AI agents: authorization governs what tools the
agent may call, but most agent harnesses don't integrate authorization
checks into the tool-call pipeline.

### 6. Workflow / State-Transition Policies

Unlike SOPs (which prescribe steps), workflow policies define
constraints on valid state transitions. An agent may not issue a
refund after a chargeback has been filed; a support ticket cannot be
closed without customer confirmation. These require the agent to track
state across the conversation and reason about preconditions before
acting.

### 7. User-Defined and Contractual Policies

The fastest-growing surface. Emerging AI contract provisions include
kill-switch rights, shadow-mode operation requirements, retraining
windows, and regulatory-change allocation clauses. These policies are
unique: negotiated per-customer, create non-standard constraint sets,
and may directly conflict with the vendor's default policy config.

### 8. Safety / Harm Policies

Hierarchical harm taxonomies (SALAD-Bench defines 6 domains, 16
tasks, 66 categories). Models are generally good at refusing obviously
harmful content but struggle with nuanced, context-dependent harm.

### 9. Code-of-Conduct Policies

Involve subjective judgment (brand voice, cultural sensitivity). The
hardest to evaluate deterministically — pi-bench defers these to
future work where deterministic checks are insufficient.

### 10. Nondisclosure Policies

Create binary constraints (never reveal X) but fail under indirect
inference chains. Doc-PP demonstrated a "Reasoning-Induced Safety
Gap" where models leak sensitive information through multi-step
reasoning even when they correctly refuse direct queries.

---

## Part 2: The Three-Layer Failure Taxonomy

The critical insight from tau2-bench: observed failures are composites
of independent causes. A policy violation in a customer service
interaction may be caused by misinterpretation (Layer 1), loss of
policy context during conversation (Layer 2), or a tool call that
bypasses the policy constraint (Layer 3). These are independent —
fixing one doesn't fix the others.

### Layer 1 — The Mind: Model Reasoning Failures

**Interpretation failures:** Multi-clause conditional interactions
(nested IF/UNLESS/EXCEPT chains), conflict resolution when policies
overlap without explicit precedence, scope misapplication where
semantic reasoning overrides literal requirements. KAMI v0.1: models
interpret "East" as including Northeast and Southeast when the policy
requires exact-match filtering — applying plausible semantic reasoning
that violates the literal requirement. RuleArena: systematic
mathematical computation errors and "rule confusion" between similar
regulations.

**Hallucinated policy:** More dangerous than misinterpretation because
invisible to the user. NIST AI 600-1 formally categorizes this as
"confabulation." Stanford: LLMs hallucinate legal facts 58-88% of the
time across verifiable legal queries. Air Canada chatbot: invented a
bereavement fare policy that didn't exist; airline held legally liable.

**Training data knowledge override:** Model's parametric knowledge
contradicts user-defined policy. GuideBench: when domain guidelines
conflict with commonsense knowledge, most LLMs score below 60%.
KAMI: "wrong adaptation" — models acknowledge a substitution in
reasoning but still produce output that violates the explicit
requirement. Distinct from hallucination: the model "knows" the policy
exists but priors overwhelm the instruction.

**Temporal reasoning failures:** LLM agents are "temporally blind"
— without explicit timestamps, models perform ~55% alignment with
human time perception (barely above random). Even with timestamps,
frontier models peak at ~65%. Policies with effective dates, grace
periods, and retroactive clauses are unreliable.

**Architectural reasoning limits:** TMLR 2026 survey "Large Language
Model Reasoning Failures": LLMs exhibit shallow disjunctive reasoning
— perform well on single-path chains but fail on multi-path
intersection tasks. Policy compliance frequently requires multi-path
reasoning — simultaneously checking authorization, data constraints,
temporal conditions, and procedural requirements. Structural
limitation of current architectures, not a training deficiency.

### Layer 2 — The Body: Harness and Orchestration Failures

**System prompt dilution:** As conversations extend, policy
instructions in system prompts compete for attention with growing
conversation history. "Lost in the middle" research: 20-50 percentage
point accuracy gaps between information at beginning versus middle of
context. A 50-turn conversation may effectively eliminate awareness
of policy constraints from the system prompt.

**Prompt injection:** OWASP #1 for LLM Applications (2025). OpenAI
acknowledged Dec 2025 it "is unlikely to ever be fully solved."
EchoLeak vulnerability (CVE-2025-32711, CVSS 9.3): zero-click
exploitation of Microsoft 365 Copilot — single crafted email
exfiltrated internal files. Any user input is a potential override
vector for policy instructions.

**Memory poisoning:** Unit 42 (Palo Alto Networks) demonstrated
indirect prompt injection can poison Amazon Bedrock Agents' session
memory persistently. Once malicious instructions are stored, they
persist across sessions. An attacker in one session permanently
degrades compliance in all future sessions.

**Multi-agent handoff failures:** OWASP ASI07 (Insecure Inter-Agent
Communication). "Agent Drift" paper: coordination drift causes router
agents to develop bias toward certain sub-agents, behavioral drift
causes agents to develop novel strategies not in initial interactions
— across 847 enterprise workflows. Policy context does not transfer
reliably across agent boundaries.

**Retry/fallback logic:** When a tool call fails, the harness may
retry with different parameters or fall back to an alternative path
— without re-evaluating policy constraints against the new execution
context. The retry may be compliant under original conditions but
violate policy under the modified conditions that triggered the retry.

### Layer 3 — The Hands: Tool Call and Action Failures

**Tool call policy bypass:** Tools are black boxes to policy
enforcement. OWASP ASI02 (Tool Misuse): agents using legitimate tools
with destructive parameters. Pi-bench research: agent says "I cannot
export full dataset" but simultaneously calls export_all_records() —
text-action misalignment where reasoning trace shows compliance but
action trace shows violation.

**Argument-level violations:** Correct tool, wrong parameters — amount
exceeding policy limits, unauthorized recipient, date outside valid
range. Detectable through pi-bench's tool_called_with check type.

**Ordering violations:** SOPBench: near 100% incorrect tool invocation
when tool registry is much larger than necessary — agents select tools
at random from large registries. JourneyBench: strict evaluation
— any SOP tool-ordering violation gives entire conversation score 0.

**Tool composition violations:** The least-tested and most dangerous
failure class. Each individual tool call may be compliant, but the
combination violates policy. OWASP ASI08 (Cascading Failures): "what
begins as a minor misalignment in one agent can trigger system-wide
outage." PolicyGuardBench uniquely targets this: items individually
under budget limits that together exceed total budget. No other
benchmark systematically tests composition violations.

**Missing tool calls:** Agent skips required verification, logging,
or audit steps. Hardest to detect because they are absences.
Detectable through pi-bench's tool_called and tool_not_called checks.

**Irreversible actions:** Highest-stakes failure class. OWASP ASI06
(Uncontrolled Autonomy): without sandboxing, "a compromised agent has
free rein over the host system." Wrong database deletion, unauthorized
communication, financial transaction — cannot be rolled back. No
benchmark tests irreversibility because benchmarks operate in
sandboxed environments.

---

## Part 3: Pressure Amplification

A study analyzing 200,000+ simulated conversations across 15 LLMs
found an average 39% performance drop in multi-turn versus single-turn
settings. Claude 3.7 Sonnet, Gemini 2.5 Pro, and GPT-4.1 all lost
30-40%, and reasoning models (o3, DeepSeek-R1) degrade equally. Key
finding: "When LLMs take a wrong turn in a conversation, they get lost
and do not recover."

The interaction between pressure conditions and failure modes is
**multiplicative, not additive.**

| Pressure | What It Amplifies |
|---|---|
| Baseline | Establishes floor — even here tau2 shows 34% pass^1 |
| Ambiguous | Primarily amplifies Layer 1 interpretation failures |
| Conflicting | Forces conflict resolution without precedence — correct response usually ESCALATE |
| User Pressure | Exploits helpfulness training; Crescendo achieves jailbreak in avg 42 seconds / 5 interactions |
| Novel | Tests over-refusal / under-refusal boundary |
| Long Trajectory | Amplifies Layer 2 context dilution; compounds: minor aptitude loss + major increase in unreliability |
| Policy Update | Old policy may be internalized through training or system prompt caching |

---

## Part 4: Six Ablation Modes

### Mode 1: Structured Policy (removes interpretation difficulty)

Replace free-form policy prose with explicit, numbered, machine-
readable rules. Keep same user situation, pressure, expected outcomes.

**Delta:** Default - Structured Policy = Interpretation Difficulty
Contribution. This is the single most diagnostic ablation for pi-bench
because the core hypothesis — that messy prose is the hard part — can
be directly measured. If an agent scores 60% on Default but 90% on
Structured Policy, then 30 points of failure are interpretation alone.

**Design note:** tau2 found that more structured policy documents
actually HURT performance in Oracle Plan mode — "when the agent
already has the ground truth solution, additional workflow instructions
cause confusion." Structured Policy must preserve semantic content
while removing ambiguity, not add additional structure.

### Mode 2: No Pressure (removes adversarial dynamics)

Replace adversarial user simulator with cooperative one. User states
request clearly, provides all information, accepts decisions without
pushback.

**Delta:** Default - No Pressure = Adversarial Pressure Contribution.

### Mode 3: Oracle Verdict (agent told what to do)

Inject ground-truth verdict and required action sequence into system
prompt. Agent knows exactly what to do but must still execute under
pressure through the tool interface.

**Delta:** Default - Oracle Verdict = Reasoning Load Contribution.
tau2's analogous ablation (Oracle Plan) improved O4-mini from 42% to
96% — a 54-point improvement. Additionally, Oracle Verdict - 100% =
Irreducible Execution Error — the floor of failures that persist even
when the agent knows exactly what to do.

### Mode 4: Default (full difficulty)

Free-form policy prose, adversarial user simulator, realistic tool
environment. This is pi-bench's standard operating mode.

### Mode 5: Harness-Isolated (tests orchestration independently)

Replace the LLM with a scripted oracle that always produces correct
responses. Run the oracle through the actual harness being tested
(LangChain, CrewAI, AutoGen, custom). Check whether the harness:
(a) maintains policy text in context across all turns,
(b) preserves tool-call ordering,
(c) handles retries without re-violating policy,
(d) manages context window limits without truncating policy text.

**Delta:** Oracle Through Harness - Oracle Without Harness =
Harness-Induced Violation Rate. The most novel ablation — no existing
benchmark isolates harness effects. If a policy-perfect oracle
produces violations through a harness, those violations are entirely
attributable to orchestration.

### Mode 6: Tool-Isolated (tool-call patterns only)

Extract tool-call traces from Default runs. Evaluate policy compliance
using only (tool_name, arguments, ordering, state_changes) — ignoring
natural language entirely.

**Delta:** Default Compliance - Tool-Trace Compliance = Text-Action
Misalignment Rate. When the agent says the right thing but does the
wrong thing, this delta captures it.

### Complete Delta Analysis

| Comparison | Measures |
|---|---|
| Default - Structured Policy | Cost of policy ambiguity |
| Default - No Pressure | Cost of adversarial users |
| Default - Oracle Verdict | Cost of reasoning/interpretation |
| Oracle Verdict - 100% | Irreducible execution error |
| Oracle Through Harness - Oracle Alone | Harness-induced violations |
| Default - Tool-Trace Only | Text-action misalignment |
| Structured + No Pressure - Oracle Verdict | Interaction effects (compounding) |

The interaction term in the last row is critical: if interpretation
difficulty and adversarial pressure interact multiplicatively (as the
multi-turn degradation research suggests), the combined effect exceeds
the sum of individual contributions.

---

## Part 5: Benchmark Coverage Analysis (19 Benchmarks)

### What Is Well-Tested

**Single-rule interpretation (saturated):** CoPriva, PAMBench,
POLIS-Bench, RuleArena, GuideBench. Frontier models score near-ceiling
on clean, structured rule-following.

**Safety content filtering (saturated):** SALAD-Bench (66 categories,
21K questions), GUARDSET-X (8 domains, 400+ risk categories),
ShieldAgent-Bench, DynaGuard (~5K guardrail rules).

**SOP/procedural compliance (adequate):** SOPBench (7 domains, 167
tools, 903 test cases, deterministic verification), JourneyBench
(strict tool-trace evaluation), LogiSafetyBench (LTL model checking
for temporal compliance).

**Multi-turn safety erosion (partial):** SAGE (personality-based
adversarial users), DynaBench (jailbreak behaviors).

### The Eight Critical Gaps

| Gap | Description | Severity |
|---|---|---|
| 1. Messy prose interpretation | Every benchmark presents policies as structured rules — none tests free-form enterprise prose | Critical |
| 2. Policy conflict resolution | No benchmark tests contradictory policies without explicit precedence | Critical |
| 3. Harness-induced violations | No benchmark isolates whether orchestration layer introduces violations | Critical |
| 4. Tool composition violations | Only PolicyGuardBench partially tests; no systematic evaluation | Critical |
| 5. Temporal policy reasoning | No benchmark tests effective dates, grace periods, retroactive clauses | Critical |
| 6. Text-action misalignment | No benchmark measures gap between what agent says and what it does | Critical |
| 7. Social engineering on operational policies | SAGE/DynaBench test safety only, not enterprise operational policies | High |
| 8. Policy updates mid-conversation | GuideBench tests between rounds only, not during active conversation | High |

### Coverage Matrix

| Failure Mode | Tested By | Gap |
|---|---|---|
| Single-rule interpretation | CoPriva, PAM, POLIS, RuleArena, GuideBench | Saturated |
| Safety content filtering | SALAD, GUARDSET-X, ShieldAgent, DynaGuard | Saturated |
| SOP/procedure ordering | SOPBench, JourneyBench, LogiSafety | Adequate |
| Multi-turn safety erosion | SAGE, DynaBench | Partial |
| Tool-call policy compliance | tau-bench, tau2-bench, ShieldAgent, ST-WebAgent | Partial |
| Enterprise trust dimensions | ST-WebAgentBench (6 dimensions) | Partial |
| Dual-control coordination | tau2-bench only | Minimal |
| Free-form prose interpretation | None | Critical |
| Policy conflict resolution | None | Critical |
| Harness-induced violations | None | Critical |
| Tool composition violations | PolicyGuardBench (partial) | Critical |
| Temporal reasoning | None | Critical |
| Text-action misalignment | None | Critical |
| Social engineering on ops policies | None | High |
| Policy update mid-interaction | GuideBench (between rounds) | High |

---

## Part 6: What Makes Enterprise Testing Fundamentally Different

The CLEAR framework's analysis of 12 major agentic benchmarks found a
37% performance gap between lab tests and production deployment.
Enterprise experts (N=15) valued reliability most, followed by policy
compliance and cost-efficiency. Core quote: "A 70% agent that works
reliably is far more deployable than an 80% agent that is
unpredictable and expensive."

Seven structural differences between benchmarks and reality:

1. **Real policies are distributed.** An agent handling a customer
   refund may consult the return policy, VIP exception list, seasonal
   promotion rules, and fraud thresholds — stored in four systems.
   Benchmarks provide single, complete text blocks.

2. **Real policy interactions are emergent.** An agent simultaneously
   satisfies HIPAA, SOC 2, internal escalation procedures, customer
   SLA terms, and department SOPs. The interaction creates constraints
   no individual document specifies. Benchmarks test policies in
   isolation.

3. **Real tools have irreversible side effects.** Sending an email,
   initiating a wire transfer, deleting a record — cannot be undone.
   Benchmarks assume state can always be compared/reset.

4. **Real harnesses introduce their own failures.** Every production
   agent runs through orchestration (LangChain, CrewAI, etc.) that
   manages context windows, handles retries, routes between agents.
   These harnesses have bugs that create policy violations independent
   of model capability. No benchmark tests the harness.

5. **Real users apply sustained, strategic pressure.** Crescendo
   achieves jailbreak in 42 seconds / 5 interactions on average. Real
   users combine multiple pressure tactics across many turns. 200K
   conversation study: models that take a wrong turn "get lost and do
   not recover."

6. **Real deployments have scale effects.** A single conversation
   involves dozens of model invocations, DB queries, API calls. OWASP
   ASI08: small inaccuracies compound across chained decisions.
   Benchmark scenarios are isolated; production scenarios cascade.

7. **Real governance is immature.** Only 29% of organizations have
   comprehensive AI governance, yet 82% deploy agents. Gartner: 40%
   of enterprise apps will integrate agents by end of 2026 (up from
   <5%). The policy documents agents must follow may themselves be
   incomplete, outdated, or contradictory.

---

## Part 7: Design Principles for pi-bench

### Principle 1: Every scenario evaluable in all six ablation modes

Each scenario requires:
- Free-form policy prose (for Default and No Pressure)
- Structured-rule equivalent (for Structured Policy mode)
- Ground-truth verdict with required action sequence (for Oracle
  Verdict mode)
- Tool-call-only evaluation specification (for Tool-isolated mode)
- Compatibility with harness-pass-through testing (for Harness-
  isolated mode)

Upfront cost per scenario is high but diagnostic power is
multiplicative.

### Principle 2: Matrix computed per ablation mode

The pressure x surface matrix should be computed separately for each
ablation mode. The difference between matrices across modes is more
informative than any single matrix:
- Default - Structured Policy heatmap: which surfaces suffer most
  from interpretation difficulty
- Default - No Pressure heatmap: which surfaces are most vulnerable
  to social engineering

### Principle 3: Harness testing requires harness diversity

Mode 5 is only valuable across multiple real harnesses — LangChain,
CrewAI, AutoGen, OpenAI Assistants API, custom implementations. Same
oracle across all harnesses; only the harness varies. Produces the
first empirical measurement of harness-induced policy violations.

### The Hardest Remaining Problem

Scenario creation at scale. Pi-bench requires Krippendorff's alpha
>= 0.80 among minimum 3 domain experts per scenario. Most productive
path: start with the eight critical gaps, create 10-15 scenarios per
gap x pressure combination, validate with domain experts, use IRT
discrimination analysis to retire scenarios that lose diagnostic
power. tau2's approach of composing atomic subtasks into composite
scenarios (15 atomic groups -> 2,285 possible tasks) offers a
combinatorial approach that could accelerate scenario generation while
maintaining expert validation at the atomic level.

---

## Key Finding

Model scale does not predict policy compliance reliability. Llama 4
Maverick (400B parameters) performs marginally better than Granite 4
Small (32B) on key scenarios. Claude 3.7, Gemini 2.5 Pro, and GPT-4.1
all show identical 30-40% multi-turn degradation. The path to reliable
policy compliance runs not through bigger models but through better
isolation of failure causes, deterministic enforcement at the tool
layer, and harness-level guarantees that policy context survives the
full conversation trajectory.
