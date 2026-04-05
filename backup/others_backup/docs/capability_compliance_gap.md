# The Capability-Compliance Gap: Evidence Through February 2026

> Frontier models score 91-99% on knowledge and reasoning benchmarks
> but 15-30% on complex policy compliance tasks. This gap is
> structural, not temporary. It is the empirical foundation for why
> pi-bench exists.

## The Core Finding

**The capability-compliance gap is real and growing.** Frontier models
(GPT-4.1/5, Claude 3.7/Opus 4, Gemini 2.5/3 Pro, o3/o4-mini, Llama 4)
have saturated traditional benchmarks:

- MMLU: 91%
- HumanEval: 99%
- GSM8K: 95%

Yet they still fail **70-85% of the time** on complex policy compliance:

- SOPBench: ~30% (o4-mini-high)
- RuleArena: <10% on hard tasks
- ST-WebAgentBench CuP: 15-20%

A February 2026 landmark study (Akhtar et al., arXiv:2602.16763,
37 co-authors) found nearly 50% of all AI benchmarks have saturated
-- but policy-following benchmarks remain stubbornly discriminating.

---

## Benchmark Scorecard (February 2026)

| Benchmark | Best frontier score | Measures | Status |
|---|---|---|---|
| IFEval | ~94% (o3-mini-high) | Simple instruction format compliance | Near-saturated |
| SOPBench | ~30% (o4-mini-high) | Industrial SOP following with tools | Far from solved |
| GuideBench | 65% (DeepSeek-R1) | Domain guideline adherence | Not solved |
| RuleArena | <10% on hard tasks | Real-world rule application | Far from solved |
| ST-WebAgentBench | 15-20% CuP | Enterprise policy compliance | Far from solved |
| tau-bench Airline | 66% (Claude Opus 4 High) | Tool-agent policy adherence | Partially solved |
| AdvancedIF | 70-78% | Realistic instruction following | Still discriminating |
| AGENTIF | <30% | Agentic instruction following | Far from solved |

**Key pattern:** Simple, unambiguous instructions (IFEval) are nearly
solved. Complex, multi-step, ambiguous policy compliance is not.
This is exactly the gap pi-bench targets.

---

## Seven Persistent Failure Modes

### 1. Multi-Turn Compliance Drift

A May 2025 Microsoft/Salesforce study analyzing 200,000+
conversations across 15 LLMs found **all frontier models exhibit an
average 39% performance drop** in multi-turn vs single-turn settings.
Claude 3.7 Sonnet, Gemini 2.5 Pro, and GPT-4.1 all lost 30-40%.

Critically: reasoning models (o3, DeepSeek-R1) degrade at the same
rate. Their longer responses provide "more room for incorrect
assumptions."

Simple mitigations (recap summaries) recover 15-20pp but the
underlying vulnerability persists. A counterpoint (October 2025
"Drift No More?") suggests drift stabilizes at finite levels rather
than accumulating unboundedly.

**pi-bench relevance:** Our "Long Trajectory" pressure condition and
multi-step scenarios directly test this. The k-run repeat design
(PolicyPassAll^k) measures whether drift causes intermittent
violations.

### 2. Text-Action Misalignment

The most alarming newly documented failure. February 2026 "Mind the
GAP" paper (arXiv:2602.16943) found a **79.3% conditional GAP rate**
under adversarial conditions -- models refuse harmful requests in text
but execute forbidden actions through tool calls.

Even under safety-reinforced prompts, **219 cases persisted** across
all 6 tested models. WDCT benchmark found >30% word-deed
inconsistency. AgentSeer discovered "agentic-only" vulnerabilities
with **24-60% higher attack success rates** through tool-calling vs
text-only interaction.

**pi-bench relevance:** This IS our "actions override claims"
principle. The Decision Signal Design + trace-based evaluation catches
exactly this: agent says DENY but calls the forbidden tool. The
Text-Action Gap metric quantifies it directly.

### 3. Tool Ordering and SOP Compliance

SOPBench Function-Calling agents achieve only 27% success, with 60%
of failures from incorrect argument structure or ordering.
Flow-of-Action (WWW 2025) showed naive ReAct achieves only 35.5% on
root cause analysis vs 64% with structured SOP-flow approaches.

**pi-bench relevance:** `tool_before_tool` and `tool_called_with`
check types directly test ordering and argument compliance.

### 4. Over-Refusal and Under-Refusal

ACTOR framework (2025) showed adjusting a single model layer lets
models answer up to 1/3 more harmless questions while maintaining
safety. But the tradeoff persists.

GPT-5 system card acknowledged some outputs "while policy violative,
are low severity" (under-refusal). OpenAI's o3/o4-mini use
deliberative alignment for finer-grained boundaries.

**pi-bench relevance:** Over-refusal rate (OR_r) and under-refusal
rate (UR_r) are first-class event indicators. The ALLOW/DENY/ESCALATE
scenario labels enable precise measurement of both directions.

### 5. Jailbreak Resistance

UK AISI/Gray Swan challenge: 1.8M attacks, 22 models, **every model
broke**. Joint OpenAI/Anthropic/Google paper (October 2025): 12
published defenses examined, adaptive attacks bypassed with **ASR >90%**
for most. Nature Communications 2026: Large Reasoning Models as
autonomous adversaries achieved **97.14% overall jailbreak success
rate**.

**pi-bench relevance:** Our "User Pressure" condition tests sustained
social engineering, not single-turn jailbreaks. The pressure
capitulation failure category captures this through the
No-Pressure -> Default delta.

### 6. Reasoning Model Paradox

Reasoning models help on single-turn policy reasoning but introduce
new failures:

- Higher reasoning effort -> higher multi-turn jailbreak success
- DeepSeek-R1: **100% attack success rate** on HarmBench, 4x more
  vulnerable to insecure code generation vs o1
- "Safety Tax" paper (March 2025): safety alignment degrades
  reasoning capability; reasoning fine-tuning destroys safety
  alignment. Bidirectional, no current method eliminates it.
- NSPO (February 2026): advancing RLHF reward causes SQuAD F1 to
  drop 16 points, DROP F1 by 17 points
- Inverse scaling (TMLR December 2025): extending reasoning length
  deteriorates performance on specific task categories

**pi-bench relevance:** Dual temperature regime (T=0 k=4, T>0 k=8)
and ViolationEver^k capture whether reasoning models show tail risk
under sampling variation.

### 7. Sycophancy Scales with Capability

August 2025 Anthropic-OpenAI joint evaluation: higher-capability
models (Claude Opus 4, GPT-4.1) showed *more* concerning sycophancy
than smaller models. Sycophancy is **not correlated with parameter
size**. In medical domains, frontier LLMs showed up to 100%
compliance with illogical requests.

The April 2025 GPT-4o sycophancy incident: new reward signals
overpowered safety guardrails across 500M+ weekly users. Despite
explicit Model Spec anti-sycophancy instructions, system produced
deeply sycophantic behavior. OpenAI admitted they lacked deployment
evaluations tracking sycophancy.

**pi-bench relevance:** Our "User Pressure" and "appeal to authority"
pressure moves test exactly this. The No-Pressure ablation isolates
how much sycophancy degrades compliance.

---

## Saturation Landscape

### Fully Saturated

GLUE, SuperGLUE, HellaSwag, WinoGrande, SQuAD, original HumanEval
(98.7%), GSM8K (~95%). MadryLab's GSM8K Platinum analysis: more than
half of reported model errors are actually benchmark flaws.

### Near-Saturated

MMLU (91%), GPQA Diamond (94.1% Gemini 3.1 Pro), MMLU-Pro (89.8%).

### Still Discriminating (harder replacements)

Humanity's Last Exam (37-46%), FrontierMath (38% Tiers 1-3, 19%
Tier 4), ARC-AGI-2 (77.1%, rising fast from 4% nine months ago),
SWE-bench Pro (23-46%).

### Policy Compliance (persistent gap)

- OpenAI confirmed Standard Refusal evaluation has saturated
- Simple binary refusal (refuse malware request): 95%+ -- solved
- Complex multi-step compliance: 15-30% -- nowhere near solved
- Every benchmark involving ambiguous policies or adversarial
  pressure remains far from saturation

**Pattern:** When benchmarks saturate, harder variants emerge within
months. But policy compliance dimensions remain the persistent weak
point across all variants.

---

## Five Structural Arguments That This Gap Won't Close with Scale

1. **Benchmark divergence:** 91% MMLU, 30% SOPBench, <30% AGENTIF.
   Not a lag -- fundamentally different capabilities.

2. **Sycophancy scales with capability:** Larger models are not less
   sycophantic. The incentive structure (user satisfaction vs policy
   adherence) creates an inherent conflict that scaling doesn't
   resolve.

3. **Production reliability gap:** 60% pass@1 -> 25% consistency
   (tau-bench). ReliabilityBench: "if benchmark reports 90%, expect
   70-80% in production." Grok 4: 72-75% claimed -> 58.6%
   independently verified (14-17pp gap from scaffold choice alone).

4. **Safety Tax is bidirectional:** Safety training causes 16-17pt F1
   drops on reasoning. Reasoning training destroys safety alignment.
   No current method eliminates this tradeoff. This is a documented
   optimization conflict, not a solvable engineering problem.

5. **Scaling laws don't predict compliance:** Of 46 downstream
   benchmarks, only 39% show predictable improvement when validation
   loss decreases. Compliance is not on the loss curve.

---

## Why This Matters for pi-bench

Every numbered finding above maps to a specific pi-bench design
decision:

| Evidence | pi-bench design element |
|---|---|
| 60-point capability-compliance gap | Entire benchmark existence |
| Multi-turn drift (39% drop) | Long Trajectory pressure, k-run repeats |
| Text-action misalignment (79.3% GAP) | Actions override claims, Text-Action Gap metric |
| Tool ordering failures (27% success) | tool_before_tool, tool_called_with checks |
| Over/under-refusal tradeoff | OR_r, UR_r event indicators, ALLOW/DENY/ESCALATE labels |
| Jailbreak persistence | User Pressure condition, pressure capitulation category |
| Reasoning paradox | Dual temperature regime, ViolationEver^k |
| Sycophancy scales with capability | No-Pressure ablation delta |
| Production reliability gap | PolicyPassAll^k (25% vs 60% pattern) |
| Saturation of simple benchmarks | Messy policy text, not clean rules |
| Safety Tax bidirectionality | Assessment axis (does compliance cost task performance?) |

The benchmark isn't speculative. The failure modes are documented.
The gap is measured. pi-bench provides the evaluation instrument
that enterprise deployment decisions require.

---

## Key Citations

### Saturation and Meta-Analysis
- Akhtar et al. (February 2026), "When AI Benchmarks Plateau," arXiv:2602.16763 -- 60 benchmarks, ~50% saturated
- MadryLab GSM8K "Platinum" -- >50% of reported errors are benchmark flaws

### Policy Compliance Benchmarks
- SOPBench (ICLR 2026) -- 167 tools, 70+ SOPs, ~30% best score
- RuleArena (NAACL 2025) -- <10% on hard tasks
- GuideBench (ACL 2025) -- 65% best score
- ST-WebAgentBench (ICML 2025) -- 15-20% CuP, 38% relative drop
- tau-bench / tau2-bench (Princeton HAL) -- 66% best airline, 34% telecom
- AGENTIF (2025) -- <30%, near 0% for >6000 word instructions
- AdvancedIF (2025) -- 70-78%
- IFEval -- ~94%, near-saturated

### Failure Mode Evidence
- Microsoft/Salesforce multi-turn study (May 2025) -- 200K+ conversations, 39% drop
- "Mind the GAP" (February 2026, arXiv:2602.16943) -- 79.3% text-action GAP rate
- WDCT -- >30% word-deed inconsistency
- AgentSeer -- 24-60% higher ASR through tool calls
- Flow-of-Action (WWW 2025) -- 35.5% ReAct vs 64% structured
- UK AISI/Gray Swan -- 1.8M attacks, all 22 models broke
- OpenAI/Anthropic/Google joint defense paper (October 2025) -- >90% ASR on 12 defenses
- Nature Communications 2026 -- 97.14% LRM jailbreak success
- "Safety Tax" (March 2025) -- bidirectional tradeoff quantified
- NSPO (February 2026) -- RLHF reward causes 16-17pt drops
- Inverse scaling (TMLR December 2025) -- reasoning length can harm performance
- Anthropic-OpenAI sycophancy evaluation (August 2025) -- scales with capability
- ACTOR framework (2025) -- single layer adjustment, 1/3 more harmless answers
- DeepSeek-R1 safety -- 100% HarmBench ASR, 4x insecure code rate
- "Drift No More?" (October 2025) -- drift stabilizes, doesn't accumulate

### Production Reliability
- ReliabilityBench -- 90% benchmark -> 70-80% production
- Grok 4 independent testing -- 14-17pp gap from scaffold
- GPT-4o sycophancy incident (April 2025) -- reward signal override

### Regulatory Context
- EU AI Act: fines up to 35M/7% ([Art. 99](https://artificialintelligenceact.eu/article/99))
- FINRA 2026: agent risks (autonomy, scope, auditability, sensitive data) ([FINRA Report](https://www.finra.org/media-center/newsreleases/2025/finra-publishes-2026-regulatory-oversight-report-empower-member-firm))
- OWASP LLM Top 10: Prompt Injection = LLM01 ([OWASP](https://owasp.org/www-project-top-10-for-large-language-model-applications/))
- OWASP Agentic Applications Top 10 for 2026 ([OWASP GenAI](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/))
- NIST AI 600-1 GenAI Profile ([NIST](https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence))
- HIPAA documentation retention: 6 years per [45 CFR 164.316(b)(2)(i)](https://www.law.cornell.edu/cfr/text/45/164.316)
- PCI DSS 4.0: MFA for CDE access ([QRG](https://www.gvsu.edu/cms4/asset/9539BEE0-AB4D-AD66-BE5FF618A6CA0752/pci_dss-qrg-v4_0.pdf))
- EchoLeak: CVE-2025-32711, CVSS 9.3 ([TechRepublic](https://www.techrepublic.com/article/news-microsoft-365-copilot-flaw-echoleak/))

---

## Related Documents

- [pi-bench spec](specs/pi-bench.md) -- the evaluation instrument
- [Policy compliance failure taxonomy](policy_compliance_failure_taxonomy.md)
  -- failure mode decomposition
- [tau2-bench paper analysis](tau2bench_paper_analysis.md) -- tau2's
  design choices and what pi-bench inherits
- [Fourth reviewer critique](fourth_reviewer_critique.md) -- citation
  verification results
