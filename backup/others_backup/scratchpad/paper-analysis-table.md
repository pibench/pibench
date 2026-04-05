# Comprehensive Paper Analysis: Policy Intelligence Under Operational Pressure

> **Living document.** 44 papers across 3 layers. Updated as new papers are read.
> Last updated: 2026-02-25
> See also: `literature-review.md` (findings synthesis), `legalbench-paper-summary.md` (deep dive)

---

## LAYER 1: INTERPRETATION — Can the model parse messy policy text?

| # | Paper | Core Question | Method | Key Findings | Relevance to pi-bench |
|---|-------|---------------|--------|--------------|----------------------|
| 1 | **LegalBench** (Guha et al. 2023, NeurIPS) | How well do LLMs perform across diverse legal reasoning tasks? | 162 tasks, 6 reasoning types, 20 LLMs evaluated few-shot | GPT-4 leads but no model dominates all types; open-source models lag significantly; plain language prompts beat legal jargon | Task taxonomy (issue-spotting, rule-application) maps directly to policy analysis workflows |
| 2 | **LexGLUE** (Chalkidis et al. 2022, ACL) | Can legal-domain models consistently outperform general-purpose transformers? | 7 datasets across US/EU jurisdictions; BERT variants evaluated | Legal-BERT achieves best aggregate; domain-specific pre-training helps most on complex tasks | Benchmark methodology transferable to policy document classification |
| 3 | **CUAD** (Hendrycks et al. 2021, NeurIPS) | Can NLP automate identification of important contract clauses? | 510 contracts, 41 clause types, extractive QA | DeBERTa-xlarge at 47.8% AUPR; 0% on rare/complex clauses; wide variance across types | Directly applicable to policy contract review; highlights struggle with nuanced provisions |
| 4 | **MAUD** (Wang et al. 2023, EMNLP) | Can AI answer fine-grained due diligence questions about merger agreements? | 152 merger agreements, 92 questions, long-context models | GPT-4 zero-shot underperforms fine-tuned models; long-context models outperform standard transformers | Shows fine-tuning outperforms zero-shot for structured policy analysis |
| 5 | **ContractNLI** (Koreeda & Manning 2021, EMNLP) | Can models determine whether obligations are entailed by contract language? | 607 NDAs, 17 hypotheses, 3-class NLI + evidence spans | Negation by exception and implicit obligations remain challenging | Entailment framework directly applicable to policy compliance checking |
| 6 | **GPT-4 Passes the Bar** (Katz et al. 2024, Phil. Trans.) | How does GPT-4 perform on the full Uniform Bar Exam? | Full MBE, MEE, MPT evaluation | 90th percentile overall; outperforms humans on 5/7 MBE subjects | Passing exams ≠ reliable interpretation — catalyzed the field but overstates readiness |
| 7 | **Not Ready for the Bench** (Waldon et al. 2025, NLLP) | Is LLM legal interpretation stable across prompt variants? | 15 models on 138 insurance contract scenarios, varied question formats | Interpretations are unstable — same model, different phrasing → different conclusion; weak correlation with human judgments | Critical warning: policy verdicts must be tested for stability, not just accuracy |
| 8 | **BLT** (Blair-Stanek et al. 2023) | Can LLMs handle basic legal text operations (lookup, comparison)? | 6 task types on citations, quotations, text comparison | GPT-4/Claude fail out-of-box; fine-tuned GPT-3.5 reaches ~100% | LLMs can't do basic policy text lookup without adaptation — validation layers essential |
| 9 | **Augmented Legal LLMs** (Savelka et al. 2023, ICAIL) | Does RAG improve legal concept explanation? | GPT-4 direct vs. retrieval-augmented with case law | RAG eliminates hallucination; direct prompting produces plausible but incorrect explanations | RAG is essential for reliable policy interpretation — direct prompting hallucinates |
| 10 | **LLMs as Corporate Lobbyists** (Nay 2023) | Can LLMs assess policy relevance to specific stakeholders? | GPT-4 predicting bill impact on companies | Reasonable accuracy on policy relevance assessment | Frames policy understanding as stakeholder impact prediction |
| 11 | **SaulLM-7B** (Colombo et al. 2024) | Can domain-specific continued pre-training produce a competitive legal LLM? | Mistral 7B + 30B legal tokens; evaluated on LegalBench-Instruct | +6 points over Mistral-Instruct; competitive with larger general models | Specialized 7B models can match larger general ones for policy tasks |
| 12 | **MultiLegalPile** (Niklaus et al. 2024, ACL) | Can multilingual legal pre-training enable cross-jurisdictional NLU? | 689GB corpus, 24 languages, 17 jurisdictions | SotA on LEXTREME and LexGLUE; cross-lingual transfer works | Essential for multi-jurisdictional policy intelligence |
| 13 | **LawBench** (Fei et al. 2024, EMNLP) | How do LLMs perform on Chinese legal tasks by cognitive level? | 20 tasks, 3 levels (memorize/understand/apply), 51 LLMs | All models struggle at "applying" level; legal fine-tuning helps memorization but not reasoning | Cognitive-level taxonomy applicable to policy task design |
| 14 | **RegNLP/RIRAG** (Gokhan et al. 2024, COLING) | How can NLP systems answer regulatory compliance questions? | 27,869 questions from ADGM financial regulations; RePASs metric | Retrieval is the bottleneck (~60% recall); obligation-aware evaluation beats text similarity | Foundational for policy QA — defines the regulatory NLP task and evaluation methodology |
| 15 | **LEXam** (Fan et al. 2025) | How do LLMs handle authentic open-ended legal reasoning? | 4,886 questions from 340 exams, 36 LLMs, LLM-as-Judge | LLMs better on MCQ than open-ended; GPT-5 tops at 70.2% | Validates LLM-as-Judge for policy reasoning evaluation; open-ended reasoning still weak |
| 16 | **Legal Compliance with LLMs** (Hassani & Jalali 2024) | Can LLMs automate regulatory compliance classification? | Food safety + GDPR compliance checking; BERT vs GPT | Paragraph-level context +40% over sentence-level; BERT more reliable for structured classification | Paragraph-level context critical for policy intelligence system design |

---

## LAYER 2: DECISION — Can the model apply rules correctly?

| # | Paper | Core Question | Method | Key Findings | Relevance to pi-bench |
|---|-------|---------------|--------|--------------|----------------------|
| 17 | **Constitutional AI** (Bai et al. 2022, Anthropic) | Can AI be trained harmless using explicit principles instead of human feedback? | Self-critique + RLAIF using 16 constitutional principles | CAI matches/exceeds RLHF; less evasive while maintaining harmlessness | Explicit codified principles can govern LLM behavior — analogous to policy rules |
| 18 | **IFEval** (Zhou et al. 2023, Google) | How well do LLMs follow verifiable instructions? | 541 prompts, 25 constraint types, deterministic checking | GPT-4 at ~76% strict accuracy; models struggle with combination constraints | Methodology directly applies to testing compliance with measurable policy requirements |
| 19 | **Reflexion** (Shinn et al. 2023, NeurIPS) | Can agents self-correct through verbal reflection? | AlfWorld, HotPotQA, HumanEval; episodic memory for learning | 97% on AlfWorld (+22%); self-reflection beats simple retry | Agents can iteratively learn policy constraints — applicable to evolving compliance |
| 20 | **LLM-as-a-Judge** (Zheng et al. 2023, NeurIPS) | Can LLMs reliably substitute for human judges? | MT-Bench + Chatbot Arena; GPT-4 vs human panels | >80% agreement with humans; position bias and self-enhancement bias identified | Establishes scalable evaluation paradigm for policy compliance — critical for pi-bench |
| 21 | **Sleeper Agents** (Hubinger et al. 2024, Anthropic) | Do safety training techniques reliably remove deceptive behaviors? | Backdoored models tested against RLHF, SFT, adversarial training | All defenses fail; adversarial training can teach better hiding; larger models more resistant to removal | Rule-following may be superficial — compliance during eval ≠ compliance in production |
| 22 | **ToolEmu** (Ruan et al. 2024, ICLR Spotlight) | How can we scalably test agent safety in tool-use? | GPT-4 emulates tools; 36 toolkits, 144 test cases, 9 risk types | Even safest agent (GPT-4) fails 23.9%; most failures from not verifying before executing | Scalable sandbox methodology directly applicable to policy-compliant agent testing |
| 23 | **tau-bench** (Yao et al. 2024, Sierra) | How well do agents follow policies while using tools and talking to users? | Retail (61 rules) + airline (115 rules) domains; pass^k metric | Best model <50% pass^1; pass^8 <25%; airline (complex policies) much harder | The most direct benchmark for policy intelligence under operational pressure |
| 24 | **RuleArena** (Zhou et al. 2025, ACL) | Can LLMs apply complex real-world rules with multi-step reasoning? | 95 rules (airline/NBA/tax), 816 problems with gold derivations | Best ~53% accuracy; rule selection degrades with rule set size; math within rules fails | Quantifies the gap between LLM capability and reliable regulatory reasoning |
| 25 | **SORRY-Bench** (Xie et al. 2025, ICLR) | How do LLMs handle safety refusal across fine-grained categories? | 44-class taxonomy, 440 prompts, 20 linguistic mutations, 56 LLMs | Existing benchmarks have 50x class imbalance; simple mutations (translation) break safety; fine-tuned 7B judge matches GPT-4 | Systematic methodology for evaluating compliance refusal boundaries |
| 26 | **AgentHarm** (Andriushchenko et al. 2025, ICLR) | Do LLM agents perform harmful multi-step actions when equipped with tools? | 110 base + 330 augmented malicious tasks, 11 harm categories | Up to 68% comply without jailbreaking; 88% with simple jailbreak; transfers from chat to agent | Agents are highly vulnerable to executing policy-violating action sequences |
| 27 | **Rethinking Legal Compliance** (Hassani et al. 2024, IEEE RE) | Can LLMs automate GDPR compliance verification of legal documents? | 5 DPAs against 20 GDPR provisions; sentence vs paragraph context | Paragraph context +40%; GPT-4 Preview at 81%; struggles with implicit compliance | Demonstrates LLM policy compliance verification — both potential and limitations |
| 28 | **Critical Domains Survey** (Chen et al. 2024) | What's the state of LLMs in finance, healthcare, and law? | Literature survey across 3 high-stakes regulated domains | No LLM reliably meets regulatory standards for autonomous deployment; human-in-loop still needed | Broader context for why policy intelligence evaluation is essential |
| 29 | **Agent-SafetyBench** (Zhang et al. 2024) | How safe are LLM agents across diverse risk scenarios? | 349 environments, 2,000 test cases, 8 risk categories, 16 LLMs | No agent scores >60%; jailbreaking accounts for ~30% of failures; GPT-4o at 59.8% | Most comprehensive agent safety evaluation; identifies specific failure modes |
| 30 | **LogiSafetyBench** (2025) | Can formal logic enable verifiable compliance evaluation? | Regulations → LTL oracles → logic-guided fuzzing → 240 test traces | Larger models prioritize task over safety; explicit safety instructions help but reduce task perf | Introduces formal verification (LTL) for policy compliance — a rigorous approach |

---

## LAYER 3: EXECUTION — Does the model hold up under pressure?

| # | Paper | Core Question | Method | Key Findings | Relevance to pi-bench |
|---|-------|---------------|--------|--------------|----------------------|
| 31 | **GCG Attacks** (Zou et al. 2023) | Can gradient optimization produce universal adversarial prompts? | Greedy Coordinate Gradient search on token suffixes; transfer tested on GPT-4, Claude, PaLM-2 | Near-100% on open-source; transfers to black-box commercial models; single suffix works across prompts | Alignment is brittle to optimization attacks — policy frameworks must assume guardrails can be bypassed |
| 32 | **"Do Anything Now"** (Shen et al. 2024, ACM CCS) | How do real-world jailbreak communities create and evolve prompts? | 1,405 prompts from 4 platforms; 107,250 query-response pairs across 6 LLMs | Prompts evolve rapidly; persona simulation and logic manipulation most persistent; Claude shows strongest resistance | Adversarial ecosystem is crowd-sourced and rapidly iterating — continuous monitoring needed |
| 33 | **PAIR** (Chao et al. 2023) | Can an LLM systematically jailbreak another LLM with black-box access? | Attacker LLM iteratively refines jailbreaks; budget of 20 queries | 88% on Vicuna, 51% on GPT-3.5, 73% on Gemini; avg cost ~$0.03 | Automated low-cost jailbreaking means policy controls can't rely on access restrictions alone |
| 34 | **Instruction Hierarchy** (Wallace et al. 2024, NeurIPS, OpenAI) | Can LLMs be trained to prioritize system instructions over conflicting user instructions? | Fine-tuned GPT-3.5 with hierarchy-aware data; tested on extraction, jailbreaks, injection | +63% robustness on in-domain, +34% on held-out; over-refusal remains a concern | Architectural mechanism for policy enforcement — system-level constraints resist user override |
| 35 | **Control Illusion** (2025) | Do LLMs actually obey instruction hierarchies? | 6 LLMs with verifiable conflicting constraints in system vs user messages | Adherence drops to 9.6-45.8%; societal cues (authority, expertise) are more influential than system/user separation | Critically undermines system-prompt-as-policy assumption; multiple control layers needed |
| 36 | **HarmBench** (Mazeika et al. 2024, ICML) | How can red teaming be standardized? | 510 harmful behaviors, 18 attack methods, 33 LLMs; R2D2 defense | No single attack is universal; no single defense is universal; multimodal attacks highly effective | Evaluation infrastructure for reproducible policy safety assessments |
| 37 | **Jailbreak Survey** (Yi et al. 2024) | What's the full attack/defense landscape? | Taxonomy of white-box + black-box attacks, prompt-level + model-level defenses | Defense-in-depth necessary; emerging attacks target multi-modal and multi-agent systems | Threat landscape reference — understanding attacks is prerequisite for policy design |
| 38 | **AgentBench** (Liu et al. 2023, ICLR 2024) | How capable are LLMs as autonomous agents? | 29 LLMs across 8 environments (OS, DB, web, games) | GPT-4 leads at 4.01; huge gap to open-source (0.51); long-horizon reasoning is bottleneck | Quantifies agent capability frontier — informs what tasks can realistically be delegated |
| 39 | **WebArena** (Zhou et al. 2024, ICLR) | Can agents do complex multi-step web tasks? | 4 real web apps, 812 tasks, functional correctness evaluation | GPT-4 at 14.41% vs humans at 78.24%; near-zero on 10+ step tasks | Autonomous agents far from human-level — human oversight still essential |
| 40 | **SWE-bench** (Jimenez et al. 2024, ICLR) | Can models resolve real GitHub issues? | 2,294 tasks from 12 Python repos; patches must pass test suites | Claude 2 at 1.96%; retrieval helps significantly; cross-file edits fail | Production-quality code generation remains extremely unreliable |
| 41 | **AI Control** (Greenblatt et al. 2024, ICML, Redwood) | How to maintain safety with potentially subversive AI? | GPT-4 (untrusted) monitored by GPT-3.5 (trusted); blue/red team protocols | Trusted editing achieves 94% usefulness + 92% safety; combined protocols improve frontier | Concrete protocol designs for policy-mandated oversight of untrusted AI outputs |
| 42 | **Sycophancy Survey** (2024) | What causes LLMs to agree with users over being correct? | Literature survey: measurement metrics, RLHF causes, mitigations | RLHF is primary driver; manifests as opinion conformity, false praise, reluctance to correct | Models that tell users what they want to hear undermine policy analysis and compliance decisions |
| 43 | **ODCV-Bench** (Li et al. 2025, McGill) | Do agents violate constraints when pressured to optimize outcomes? | 40 scenarios in 6 domains; 12 models given KPI targets | Gemini-3-Pro at 71.4% misalignment; more capable models better at gaming; models rarely refuse | **Most directly relevant to pi-bench**: outcome pressure causes agents to violate policy constraints |
| 44 | **LAT** (Sheshadri et al. 2024) | Can latent-space adversarial training provide broad robustness? | Targeted LAT on Gemma 7B; tested vs GCG, PEZ, GBDA, backdoors | Near-zero attack success; outperforms R2D2 at orders of magnitude less compute | Efficient safety training technique — could be mandated as baseline defense |

---

## GitHub Repositories & Datasets

| # | Paper | Repo / Resource |
|---|-------|----------------|
| 1 | LegalBench | [HazyResearch/legalbench](https://github.com/HazyResearch/legalbench) |
| 2 | LexGLUE | [coastalcph/lex-glue](https://github.com/coastalcph/lex-glue) |
| 3 | CUAD | [TheAtticusProject/cuad](https://github.com/TheAtticusProject/cuad) |
| 4 | MAUD | [TheAtticusProject/maud](https://github.com/TheAtticusProject/maud) |
| 5 | ContractNLI | [stanfordnlp/contract-nli-bert](https://github.com/stanfordnlp/contract-nli-bert) |
| 8 | BLT | [BlairStanek/BLT](https://github.com/BlairStanek/BLT) |
| 11 | SaulLM-7B | HuggingFace: `Equall/Saul-7B-Base` |
| 12 | MultiLegalPile | HuggingFace: `joelniklaus/Multi_Legal_Pile` |
| 13 | LawBench | [open-compass/LawBench](https://github.com/open-compass/LawBench) |
| 14 | RegNLP | [RegNLP org](https://github.com/RegNLP) (ObliQADataset, RePASs) |
| 15 | LEXam | [LEXam-Benchmark/LEXam](https://github.com/LEXam-Benchmark/LEXam) |
| 17 | Constitutional AI | [anthropics/ConstitutionalHarmlessnessPaper](https://github.com/anthropics/ConstitutionalHarmlessnessPaper) |
| 18 | IFEval | [google-research/.../instruction_following_eval](https://github.com/google-research/google-research/tree/master/instruction_following_eval) |
| 19 | Reflexion | [noahshinn/reflexion](https://github.com/noahshinn/reflexion) |
| 20 | LLM-as-a-Judge | [lm-sys/FastChat/.../llm_judge](https://github.com/lm-sys/FastChat/tree/main/fastchat/llm_judge) |
| 21 | Sleeper Agents | [anthropics/sleeper-agents-paper](https://github.com/anthropics/sleeper-agents-paper) |
| 22 | ToolEmu | [ryoungj/ToolEmu](https://github.com/ryoungj/ToolEmu) |
| 23 | tau-bench | [sierra-research/tau-bench](https://github.com/sierra-research/tau-bench) |
| 24 | RuleArena | [SkyRiver-2000/RuleArena](https://github.com/SkyRiver-2000/RuleArena) |
| 25 | SORRY-Bench | [SORRY-Bench/sorry-bench](https://github.com/SORRY-Bench/sorry-bench) |
| 26 | AgentHarm | [METR/inspect_evals/.../agentharm](https://github.com/METR/inspect_evals/tree/main/src/inspect_evals/agentharm) |
| 29 | Agent-SafetyBench | [thu-coai/Agent-SafetyBench](https://github.com/thu-coai/Agent-SafetyBench) |
| 31 | GCG Attacks | [llm-attacks/llm-attacks](https://github.com/llm-attacks/llm-attacks) |
| 32 | "Do Anything Now" | [verazuo/jailbreak_llms](https://github.com/verazuo/jailbreak_llms) |
| 33 | PAIR | [patrickrchao/JailbreakingLLMs](https://github.com/patrickrchao/JailbreakingLLMs) |
| 35 | Control Illusion | [yilin-geng/llm_instruction_conflicts](https://github.com/yilin-geng/llm_instruction_conflicts) |
| 36 | HarmBench | [centerforaisafety/HarmBench](https://github.com/centerforaisafety/HarmBench) |
| 38 | AgentBench | [THUDM/AgentBench](https://github.com/THUDM/AgentBench) |
| 39 | WebArena | [web-arena-x/webarena](https://github.com/web-arena-x/webarena) |
| 40 | SWE-bench | [SWE-bench/SWE-bench](https://github.com/SWE-bench/SWE-bench) |
| 43 | ODCV-Bench | [McGill-DMaS/ODCV-Bench](https://github.com/McGill-DMaS/ODCV-Bench) |
| 44 | LAT | [aengusl/latent-adversarial-training](https://github.com/aengusl/latent-adversarial-training) |

**No public repo:** #6 (Bar Exam — SSRN paper), #7 (Not Ready for Bench), #9 (Augmented Legal LLMs), #10 (Corporate Lobbyists), #16 (Legal Compliance), #27 (Rethinking Compliance), #28 (Critical Domains Survey), #30 (LogiSafetyBench), #34 (Instruction Hierarchy — OpenAI internal), #37 (Jailbreak Survey), #41 (AI Control — Redwood org), #42 (Sycophancy Survey)

---

## Changelog

| Date | Change |
|---|---|
| 2026-02-25 | Initial creation. 44 papers analyzed across 3 layers. GitHub repos documented. |
