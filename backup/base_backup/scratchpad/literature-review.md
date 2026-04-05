# Literature Review: Policy Intelligence Under Operational Pressure

> **Living document.** Updated as new papers, insights, and connections are found.
> Last updated: 2026-02-25

## Research Question

**Can the model understand, interpret, and reason about messy policy text — and act correctly under operational pressure?**

This decomposes into three layers that map directly to pi-bench's evaluation structure:

| Layer | Question | pi-bench connection |
|---|---|---|
| **Interpretation** | Can the model parse ambiguous, real-world policy text? | Structured Policy ablation, Layer A categories (Policy Activation, Norm Interpretation, Norm Resolution) |
| **Decision** | Can the model apply rules correctly to novel situations? | ALLOW/DENY/ESCALATE verdicts, compliance rate |
| **Execution** | Does the model hold up under pressure, conflicts, edge cases? | Pressure conditions, over-refusal, under-refusal |

---

## Coverage at a Glance

### The Reliability Cliff (cross-cutting finding)

Surface-level competence does NOT predict operational reliability. Models pass bar exams (90th percentile) but fail basic legal text lookup. Models classify clauses correctly but give different answers when you rephrase the question. Models follow rules in chat but violate them when given tools and KPI pressure.

**This gap — between "passes a test" and "works safely under pressure" — is what pi-bench exists to measure.**

### Layer 1: Interpretation

| Finding | Evidence | Implication for pi-bench |
|---|---|---|
| LLMs pass bar exams at 90th percentile | Katz et al. 2024 (GPT-4 Bar Exam) | Passing exams ≠ reliable interpretation |
| But fail basic textual lookup in legal docs | Blair-Stanek et al. 2023 (BLT) | Must test granular operations, not just comprehension |
| Interpretation is **unstable** across prompt variants | Waldon et al. 2025 (Not Ready for the Bench) | Same policy, different phrasing → different verdict = critical failure mode |
| RAG eliminates hallucination in legal concepts | Savelka et al. 2023 (Augmented LLMs) | Retrieval-augmented policy reading may be needed |
| ~27% of regulatory text contains ambiguities | Hassani & Jalali 2024 | Ambiguous policy scenarios are realistic, not edge cases |
| Multi-step open-ended reasoning remains weak | Fan et al. 2025 (LEXam) | Chain-of-reasoning policy scenarios will be hardest |
| Domain-specific pretraining helps significantly | Colombo et al. 2024 (SaulLM) | General-purpose LLMs may underperform on specialized policies |
| Plain language prompts outperform legal jargon | Guha et al. 2023 (LegalBench) | Policy format matters — messy real-world text is harder than cleaned-up versions |

### Layer 2: Decision

| Finding | Evidence | Implication for pi-bench |
|---|---|---|
| Rule-following fails 50-75% on policy tasks | Yao et al. 2024 (Tau-Bench); Zhou et al. 2025 (RuleArena) | Baseline compliance will be low even for frontier models |
| Agentic contexts degrade compliance | Andriushchenko et al. 2025 (AgentHarm); Ruan et al. 2024 (ToolEmu) | Tool-use + multi-step = compliance drops sharply |
| No agent scores >60% on safety benchmarks | Zhang et al. 2024 (Agent-SafetyBench) | Safety is unsolved across the board |
| Rule-following can be superficial (backdoors) | Hubinger et al. 2024 (Sleeper Agents) | Behavioral consistency across conditions must be measured |
| Refusal is bidirectional: over-refuse AND under-refuse | Xie et al. 2025 (SORRY-Bench) | Both false positives and false negatives matter — pi-bench's over-refusal metric captures this |
| LLM-as-judge shows systematic biases | Zheng et al. 2023 (MT-Bench) | Automated evaluation of policy compliance needs careful calibration |
| Formal methods (logic) improve compliance | (LogiSafetyBench 2025) | Structured policy → better compliance; messy policy → worse. The delta is the interpretation tax |

### Layer 3: Execution Under Pressure

| Finding | Evidence | Implication for pi-bench |
|---|---|---|
| **Agents cheat under KPI pressure** (30-50%) | Li et al. 2025 (ODCV-Bench) | Pressure scenarios are essential — agents cut corners to hit targets |
| Instruction hierarchy adherence: 14-47% | (Control Illusion 2025) | System prompt policies get overridden by user instructions |
| Automated jailbreaking needs only 20 queries | Chao et al. 2023 (PAIR) | Adversarial users can break policy compliance cheaply |
| Sycophancy rate ~58% | (Sycophancy Survey 2024) | Confident/pushy users cause agents to abandon correct policy positions |
| Real-world task success is abysmal (14-50%) | Zhou et al. 2024 (WebArena); Yao et al. 2024 (Tau-Bench) | Production reliability is far below demo quality |
| Deceptive behaviors persist through safety training | Hubinger et al. 2024 (Sleeper Agents) | Cannot assume safety training = safe behavior |
| Monitoring with weaker trusted models helps | Greenblatt et al. 2024 (AI Control) | Layered oversight may mitigate execution failures |
| Adversarial attacks transfer across models | Zou et al. 2023 (GCG) | A jailbreak found on one model works on others |

---

## Paper Registry

All papers are downloaded to `papers/policy-intelligence/` with numbered filenames.

### Interpretation (16 papers)

| # | File | Paper | Year | Venue |
|---|------|-------|------|-------|
| 1 | `01-legalbench-2308.11462.pdf` | LegalBench: Collaboratively Built Benchmark for Legal Reasoning | 2023 | NeurIPS |
| 2 | `02-lexglue-2110.00976.pdf` | LexGLUE: Benchmark for Legal Language Understanding | 2022 | ACL |
| 3 | `03-cuad-2103.06268.pdf` | CUAD: Expert-Annotated NLP Dataset for Contract Review | 2021 | NeurIPS |
| 4 | `04-maud-2301.00876.pdf` | MAUD: Expert-Annotated Dataset for Merger Agreement Understanding | 2023 | EMNLP |
| 5 | `05-contractnli-2110.01799.pdf` | ContractNLI: Document-level NLI for Contracts | 2021 | EMNLP Findings |
| 6 | — | GPT-4 Passes the Bar Exam (Katz et al.) | 2024 | Phil. Trans. Royal Soc. A |
| 7 | — | Not Ready for the Bench: LLM Legal Interpretation is Unstable (Waldon et al.) | 2025 | NLLP Workshop |
| 8 | `06-blt-basic-legal-text-2311.09693.pdf` | BLT: Can LLMs Handle Basic Legal Text? | 2023 | arXiv |
| 9 | — | Explaining Legal Concepts with Augmented LLMs (Savelka et al.) | 2023 | ICAIL |
| 10 | — | LLMs as Corporate Lobbyists (Nay) | 2023 | arXiv |
| 11 | `33-saullm-2403.03883.pdf` | SaulLM-7B: A Pioneering LLM for Law | 2024 | arXiv |
| 12 | `37-multilegal-2306.02069.pdf` | MultiLegalPile: 689GB Multilingual Legal Corpus | 2024 | ACL |
| 13 | `36-lawbench-2309.16289.pdf` | LawBench: Benchmarking Legal Knowledge of LLMs | 2024 | EMNLP |
| 14 | `31-regnlp-2409.05677.pdf` | RegNLP: Compliance Through Automated Info Retrieval | 2024 | COLING |
| 15 | `32-lexam-2505.12864.pdf` | LEXam: Benchmarking Legal Reasoning on 340 Law Exams | 2025 | arXiv |
| 16 | `38-legal-compliance-2404.17522.pdf` | Enhancing Legal Compliance and Regulation Analysis with LLMs | 2024 | arXiv |

### Decision (14 papers)

| # | File | Paper | Year | Venue |
|---|------|-------|------|-------|
| 17 | `07-constitutional-ai-2212.08073.pdf` | Constitutional AI: Harmlessness from AI Feedback | 2022 | arXiv |
| 18 | `08-ifeval-2311.07911.pdf` | IFEval: Instruction-Following Evaluation for LLMs | 2023 | arXiv |
| 19 | `09-reflexion-2303.11366.pdf` | Reflexion: Language Agents with Verbal Reinforcement Learning | 2023 | NeurIPS |
| 20 | `30-llm-judge-2306.05685.pdf` | LLM-as-a-Judge with MT-Bench and Chatbot Arena | 2023 | NeurIPS |
| 21 | `10-sleeper-agents-2401.05566.pdf` | Sleeper Agents: Deceptive LLMs that Persist Through Safety Training | 2024 | arXiv |
| 22 | `11-toolemu-2309.15817.pdf` | ToolEmu: Identifying Risks of LM Agents | 2024 | ICLR Spotlight |
| 23 | `12-tau-bench-2406.12045.pdf` | Tau-Bench: Tool-Agent-User Interaction in Real-World Domains | 2024 | arXiv |
| 24 | `13-rulearena-2412.08972.pdf` | RuleArena: Rule-Guided Reasoning with LLMs | 2025 | ACL |
| 25 | `14-sorry-bench-2406.14598.pdf` | SORRY-Bench: Evaluating LLM Safety Refusal | 2025 | ICLR |
| 26 | `15-agentharm-2410.09024.pdf` | AgentHarm: Measuring Harmfulness of LLM Agents | 2025 | ICLR |
| 27 | `40-compliance-rethinking-2404.14356.pdf` | Rethinking Legal Compliance Automation with LLMs | 2024 | IEEE RE |
| 28 | `39-critical-domains-survey-2405.01769.pdf` | Survey: LLMs for Finance, Healthcare, and Law | 2024 | arXiv |
| 29 | `16-agent-safetybench-2412.14470.pdf` | Agent-SafetyBench: Evaluating Safety of LLM Agents | 2024 | arXiv |
| 30 | `34-logisafetybench-2601.08196.pdf` | LogiSafetyBench: Implicit Regulatory Compliance via Logic | 2025 | arXiv |

### Execution Under Pressure (14 papers)

| # | File | Paper | Year | Venue |
|---|------|-------|------|-------|
| 31 | `17-gcg-adversarial-2307.15043.pdf` | GCG: Universal Adversarial Attacks on Aligned LLMs | 2023 | arXiv |
| 32 | `29-do-anything-now-2308.03825.pdf` | "Do Anything Now": In-The-Wild Jailbreak Prompts | 2024 | ACM CCS |
| 33 | `28-pair-jailbreak-2310.08419.pdf` | PAIR: Jailbreaking Black Box LLMs in 20 Queries | 2023 | arXiv |
| 34 | `18-instruction-hierarchy-2404.13208.pdf` | Instruction Hierarchy: Training LLMs to Prioritize | 2024 | NeurIPS |
| 35 | `19-control-illusion-2502.15851.pdf` | Control Illusion: Failure of Instruction Hierarchies | 2025 | arXiv |
| 36 | `20-harmbench-2402.04249.pdf` | HarmBench: Standardized Red Teaming Evaluation | 2024 | ICML |
| 37 | `35-jailbreak-survey-2407.04295.pdf` | Jailbreak Attacks and Defenses: A Survey | 2024 | arXiv |
| 38 | `21-agentbench-2308.03688.pdf` | AgentBench: Evaluating LLMs as Agents | 2023 | ICLR 2024 |
| 39 | `22-webarena-2307.13854.pdf` | WebArena: Realistic Web Environment for Agents | 2024 | ICLR |
| 40 | `23-swe-bench-2310.06770.pdf` | SWE-bench: Resolving Real-world GitHub Issues | 2024 | ICLR |
| 41 | `25-ai-control-2312.06942.pdf` | AI Control: Safety Despite Intentional Subversion | 2024 | ICML |
| 42 | `26-sycophancy-survey-2411.15287.pdf` | Sycophancy in LLMs: Causes and Mitigations | 2024 | arXiv |
| 43 | `24-odcv-bench-2512.20798.pdf` | ODCV-Bench: Outcome-Driven Constraint Violations | 2025 | arXiv |
| 44 | `27-lat-robustness-2407.15549.pdf` | Targeted Latent Adversarial Training for LLM Robustness | 2024 | arXiv |

---

## Individual Paper Summaries

Detailed summaries for each paper are in separate files:
- `legalbench-paper-summary.md` — deep summary of LegalBench (Paper #1)
- *(add more as papers are read in depth)*

---

## Open Questions for Further Research

- [ ] Are there benchmarks specifically testing **policy ambiguity resolution** (not just comprehension)?
- [ ] What work exists on **multi-policy conflict** — when two valid policies contradict?
- [ ] How do models perform on **temporal policy changes** — old policy vs new policy on same scenario?
- [ ] Is there work on **cross-jurisdictional policy reasoning** — same situation, different rules by region?
- [ ] What benchmarks test **escalation judgment** — when to hand off vs when to decide?

---

## Changelog

| Date | Change |
|---|---|
| 2026-02-25 | Initial creation. 44 papers across 3 layers. 40 PDFs downloaded. |
