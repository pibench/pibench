# Related Work: Benchmarking Policy-Following in Models and Agents

## Scope and framing

This review is a targeted literature review of benchmarks and evaluation frameworks that test whether models or agents follow policies, rules, or operational constraints. It began from a broad, tool-assisted search across benchmark, compliance, safety, agent, and legal-NLP literature, followed by manual screening and close reading. From that broader candidate set, we selected 16 papers as the core evidence base because they most directly evaluate policy-related reasoning, execution, or compliance behavior in models and agents. Broader legal and regulatory NLP datasets are used only as contextual background, not as the primary evidence base for the benchmark gap argued here.

We do not assume that policy intelligence has a fixed, settled taxonomy. Instead, we use the literature to identify candidate dimensions that recur across prior work — interpretation, rule retrieval, procedural adherence, hierarchical policy enforcement, pressure robustness, escalation, and trajectory-level compliance — and treat those as hypotheses to be tested empirically rather than as axioms.

The central question is narrower than generic agent safety and broader than static legal question answering: given a policy document and a task, can an agent act in a way that remains compliant over the course of an interaction?

## Why state and tools matter, and when user simulation is needed

Pi-bench is motivated by a simple constraint: operational policy-following agents are deployed into environments that are already stateful. Finance, healthcare, customer support, and enterprise operations are not collections of isolated prompts; they are systems in which actions update records, trigger transitions, constrain future actions, and create audit-relevant trajectories. A benchmark that removes state may still evaluate isolated decisions, but it is no longer testing the same object that is deployed in practice.

Tools matter for the same reason. In real operational settings, compliance is not only about what an agent says. It is about what the agent does through the interfaces available to it: updating a ticket, issuing a refund, modifying an account, accessing a record, creating a note, or escalating a case. A benchmark that strips away tools reduces policy-following to verbal judgment and misses the action surface on which many real violations occur.

User simulation is required only for the subset of tasks in which policy-relevant behavior emerges through interaction. Some tasks are naturally single-turn: the agent receives a request, inspects the current state, uses tools if needed, and acts. Those tasks still require state and tools, but they do not require a simulated user. Other tasks require back-and-forth interaction because the policy question depends on clarification, partial information, exception handling, conflicting instructions, escalation, or user pressure. In those cases, user simulation is necessary because the policy-relevant behavior unfolds over the interaction rather than in a single decision.

Pi-bench therefore does not treat user simulation as mandatory for every task. Instead, it preserves the minimum structure needed for valid evaluation. All tasks are grounded in state and executable tools. User simulation is added when the task requires interaction in order to test policy-following faithfully.

## Landscape at a glance

| Group | Representative papers | What they evaluate | Main limitation relative to pi-bench |
|---|---|---|---|
| Policy reasoning without execution | LegalBench, RuleArena, GuideBench, POLIS-Bench, AIReg-Bench | Reading rules, guidelines, or regulations and producing judgments or answers | No live execution environment; no trajectory-level compliance |
| Policy-constrained execution with structured policies | τ-bench, τ²-bench, ST-WebAgentBench, SOPBench, JourneyBench | Acting in an environment while respecting benchmark-authored rules, structured workflows, or SOP graphs | Policies are structured, templated, or pre-formalized rather than messy operational documents |
| Pressure, safety, and compliance ecosystems | ODCV-Bench, LogiSafetyBench, HAICOSYSTEM | Constraint violations under pressure, formal safety oracles, multi-turn risk | Optimized for safety or compliance stress, not document-grounded operational policy following |
| Enterprise realism without explicit policy documents | TheAgentCompany, WorkArena | Realistic workplace tasks and enterprise workflows | Policies are implicit in workflow or norms, not provided as documents for interpretation |

## 1. Policy reasoning without execution

### LegalBench

LegalBench decomposes legal reasoning into six categories: issue spotting, rule recall, rule application, rule conclusion, interpretation, and rhetorical understanding. It contains 162 tasks drawn from 36 corpora and demonstrates that performance varies substantially across legal subproblems rather than collapsing into a single notion of “legal ability.” GPT-4 performs strongly on several categories but reaches only 47.8% balanced accuracy on the MAUD merger-agreement tasks, illustrating that benchmark difficulty depends heavily on the type of legal reasoning required. LegalBench is valuable here because it shows that policy understanding can be decomposed into finer-grained abilities. Its limitation is equally important: the benchmark remains entirely answer-based. The model never acts, updates shared state, or navigates user interaction.

### RuleArena

RuleArena studies rule-guided reasoning over three real-world domains: airline baggage fees, NBA transactions, and tax regulations. It contains 95 rules and 816 problems, and its evaluation distinguishes rule selection from rule application. That decomposition matters. It allows one to ask whether a model failed because it could not identify the relevant rule set or because it could not correctly execute reasoning once the relevant rules were available. The benchmark also provides per-problem ground-truth solutions with labeled relevant rules, enabling structured analysis of failure modes. But RuleArena remains a text-in, text-out benchmark. It evaluates reasoning about rules, not behavior under rules.

### GuideBench

GuideBench evaluates domain-oriented guideline following across 1,272 instances, seven task categories, and 537 curated rules. Its contribution is to separate three axes that are often conflated: adherence to rules, robustness to rule updates, and alignment with human preferences. That separation is useful because it shows that “following the guideline” is not one phenomenon. A model may comply with the current rule set yet fail when the rules change, or align with user preference while drifting from stated policy. A separate ablation in GuideBench shows that removing the Guidelines block from the prompt reduces accuracy in four of seven categories — price matching, math, agent chatting, and summarization — which suggests that guideline conditioning is doing real work rather than merely echoing what the model already knows. The benchmark remains single-turn and non-executive, but it sharpens the distinction between static guideline adherence and dynamic policy change.

### POLIS-Bench

POLIS-Bench extends policy evaluation into bilingual governmental settings. It introduces three tasks — Clause Retrieval and Interpretation, Solution Generation, and Compliance Judgment — over 3,058 Chinese and English policy instances with source-evidence annotation. This matters for two reasons. First, it moves beyond generic legal QA into policy-grounded decision tasks. Second, it highlights that fluent answers are not the same as correct policy use: some models achieve high semantic similarity while remaining much weaker on accuracy. POLIS-Bench therefore supports a broader lesson that will recur throughout the literature: surface plausibility and policy fidelity can diverge sharply. Its limitation is that the output remains text and the evaluation target remains judgment, not operational behavior.

### AIReg-Bench

AIReg-Bench is the most direct text-only compliance benchmark in the core set. It asks models to assess whether technical documentation excerpts describing plausible AI systems comply with selected articles of the EU AI Act. The dataset contains 120 expert-annotated excerpts covering articles on risk management, data governance, record keeping, human oversight, and accuracy, robustness, and cybersecurity. The benchmark is important because it narrows from generic regulation interpretation to explicit compliance assessment. In other words, the task is not simply “what does the regulation say?” but “does this system, as described, appear compliant?” That makes AIReg-Bench the closest reasoning-without-execution benchmark to a real compliance task. Its limitation is the same as the rest of this group: the model judges compliance over text, but it never has to behave compliantly in an environment.

### AIR-Bench 2024 as adjacent methodology

AIR-Bench 2024 is adjacent rather than central. It derives a four-tier safety taxonomy from eight government regulations and sixteen company policies, yielding 314 granular risk categories. That makes it one of the most regulation-grounded benchmarks in the broader neighborhood. However, its target is refusal behavior — whether a model refuses harmful requests — rather than operational policy compliance during task execution. AIR-Bench is useful here as methodological precedent for deriving evaluation categories from real documents, but not as direct evidence on policy-following agents.

### What this group establishes

Taken together, these benchmarks establish that models can be tested on policy text, legal rules, regulations, and guidelines in increasingly fine-grained ways. They also establish that policy understanding is not a unitary ability. What they do not establish is whether those abilities survive contact with environment state, tools, user interaction, and pressure.

## 2. Policy-constrained execution with structured or benchmark-authored policies

### τ-bench

τ-bench is foundational because it introduced the now-familiar three-role structure: an agent, a simulated user, and a deterministic environment with tools and database state. It evaluates customer-service agents in retail and airline domains and scores them by comparing final database state against annotated goal state. It also introduced pass^k as a reliability metric, measuring whether an agent succeeds consistently across repeated runs. τ-bench matters because it moved the field from isolated judgments to interaction with tools under policies. It also showed that policy sensitivity is domain dependent: removing policy from the prompt causes a much larger drop in airline than in retail, suggesting that some apparent success in simpler domains may come from commonsense priors rather than genuine policy use.

Its main limitation, relative to pi-bench, is that evaluation is tied to end-state success. If the agent violates policy during the interaction but still lands in the correct final database state, that violation is largely invisible to the benchmark.

### τ²-bench

τ²-bench extends τ-bench from single-control to dual-control settings by adding a telecom domain in which both agent and user can act on a shared world. This matters because many real operational settings require not just autonomous action but coordination: the user must confirm, update, or perform some portion of the workflow. The paper motivates the shift explicitly: real technical support and service scenarios are not settings in which the user is a passive information source. They are settings in which the user and agent co-manipulate state. τ²-bench therefore strengthens the case for user simulation as a structural requirement rather than an optional feature.

Its limitation remains similar to τ-bench: although the environment is more realistic, the benchmark is still built around structured domain policies rather than messy operational documents, and it does not fully separate policy interpretation from policy execution.

### ST-WebAgentBench

ST-WebAgentBench is the strongest “almost-pi-bench” reference in the literature. It introduces Completion under Policy (CuP), which gives credit only for task completions that satisfy all applicable policies. This is a major conceptual advance because it formalizes a distinction that earlier benchmarks often blurred: raw task completion and policy-compliant task completion are not the same metric. In its ICLR 2026 version, ST-WebAgentBench evaluates 375 tasks paired with 3,057 policy instances across GitLab, ShoppingAdmin, and SuiteCRM. Policies are organized hierarchically and benchmarked along multiple safety and trustworthiness dimensions.

The benchmark shows that these two metrics can diverge substantially: agents may appear successful on task completion while failing once policy adherence is taken seriously. It is also operationally important because it treats policy compliance as a first-class metric inside a real web-agent setting.

Its limitation, relative to pi-bench, is not lack of state or lack of interaction. It is the policy substrate. ST-WebAgentBench uses benchmark-authored hierarchical templates, not messy free-form operational documents of the kind enterprise agents are actually expected to read and act under.

### SOPBench

SOPBench evaluates whether agents follow customer-service SOPs across seven domains using directed graphs of executable functions and rule-based oracle verifiers. Its contribution is to make procedure adherence explicit. Instead of scoring only final outcomes, it evaluates whether the agent executed permissible actions, reached the correct database state, and completed the required procedure. This is one of the clearest examples in the literature of policy as executable specification.

That structure makes SOPBench highly relevant and highly limited at the same time. It is relevant because it demonstrates how deterministic, trajectory-level compliance checking can be built. It is limited because the policy has already been compiled into an executable structure. The agent is not reading a messy policy document from scratch and deciding how to act under ambiguity; it is operating in a setting whose governing rules are already represented as structured executable logic.

### JourneyBench

JourneyBench, introduced in the paper “Beyond IVR,” evaluates customer-support agents against SOP-governed user journeys across e-commerce, loan application, and telecommunications domains. Its key result is not merely that policy orchestration helps, but that orchestration can dominate raw model capability: a Dynamic-Prompt Agent that models the SOP as a state machine can outperform a stronger model wrapped in a weaker orchestration scheme. The benchmark therefore provides strong evidence that policy-following in operational workflows is not only a model capability problem. It is also a systems-design problem.

Like SOPBench, however, JourneyBench represents policy as a structured workflow graph. The benchmark is therefore best understood as evidence for executable policy control, not for free-form policy interpretation.

### What this group establishes

This group shows that once policies are made executable, templated, or structurally explicit, agents can be benchmarked in stateful environments with deterministic evaluation, repeated-run reliability, and trajectory-sensitive compliance metrics. The open problem is what happens when those policy constraints are not already compiled into benchmark-native structure.

## 3. Pressure, safety, and compliance ecosystems

### ODCV-Bench

ODCV-Bench focuses on outcome-driven constraint violations in a persistent command-line environment. Each scenario contains both mandated and incentivized variants, allowing the benchmark to distinguish between explicit obedience to bad instructions and emergent misalignment under KPI pressure. The result is important because it shows that capability and compliance do not move together. Some strong models violate constraints at surprisingly high rates when outcome pressure is introduced. ODCV-Bench therefore contributes something the earlier execution benchmarks mostly do not: a direct test of whether agents remain policy-aligned when successful task completion is put into tension with rule-following.

Its limitation, relative to pi-bench, is that it is not centered on document-grounded operational policy interpretation. It is a pressure-and-violation benchmark rather than a benchmark for reading and executing under real policy documents.

### LogiSafetyBench

LogiSafetyBench contributes a different idea: compliance evaluation can be strengthened by formalizing regulations into logic oracles and then checking generated traces against those oracles. The benchmark converts unstructured regulations into Linear Temporal Logic oracles, uses logic-guided fuzzing to synthesize tasks, and evaluates functional correctness separately from temporal safety compliance. This is a meaningful methodological advance because it shows how trajectory-level compliance can be checked against explicit formal constraints rather than via a single undifferentiated score.

The right comparison to pi-bench is subtle. LogiSafetyBench is closer to document-grounded compliance than many execution benchmarks because it begins from unstructured regulation text. But by the time evaluation occurs, the policy has already been converted into a pre-formalized LTL oracle. It therefore addresses the back end of compliance evaluation more than the front end problem of giving an operational agent a document and asking it to behave correctly under that document.

### HAICOSYSTEM

HAICOSYSTEM provides the richest multi-turn safety-risk ecosystem in the set. It simulates interactions between users and tool-using agents across seven domains and evaluates outcomes along four risk dimensions: operational, content-related, societal, and legal. The benchmark reports that state-of-the-art models exhibit safety risks in 62% of cases overall, particularly during tool use with malicious users, and that dynamic multi-turn interactions surface up to three times more safety risks than static single-turn settings. This is important because it shows that risk profiles observed in static jailbreak-style evaluation can materially underestimate what emerges in realistic, tool-mediated interaction.

HAICOSYSTEM shares several design intuitions with pi-bench: stateful environments, user simulation, multi-turn pressure, and domain diversity. Its limitation is that its target is safety risk rather than operational policy adherence. It asks whether agent behavior becomes dangerous or rights-violating in ecosystem settings; pi-bench asks whether an agent given a governing document behaves compliantly over the trajectory of work.

### What this group establishes

These benchmarks show that policy-adjacent behavior cannot be understood only through static answers or end-state task completion. Pressure matters. Multi-turn interaction matters. Explicit oracles matter. And stronger models are not automatically safer or more compliant. What remains missing is a benchmark that brings those insights back to document-grounded operational policy following.

## 4. Enterprise realism without explicit policy documents

### TheAgentCompany

TheAgentCompany simulates work inside a software company and evaluates agents on enterprise-style tasks spanning engineering, management, administration, finance, and related functions. It is important because it demonstrates how far current agents remain from robust performance in long-horizon workplace tasks even when the benchmark is designed to resemble real internal work.

Relative to pi-bench, however, TheAgentCompany makes policies implicit. The agent is dropped into a workplace-like ecosystem, but the benchmark does not provide explicit operational documents whose interpretation is part of the task. The relevant constraints live in organizational norms, workflow expectations, and task structure rather than in policy documents the agent must read and follow.

### WorkArena

WorkArena does something similar on top of a real enterprise platform, ServiceNow. It benchmarks agents on common knowledge-work tasks inside a realistic enterprise software environment. Its value is realism: the benchmark is not a toy browser environment but a hosted enterprise workflow surface. Its limitation is again the policy substrate. WorkArena measures whether an agent can complete workplace tasks, not whether it can read and execute under explicit policy documents.

### What this group establishes

These benchmarks show that enterprise realism is possible and valuable. They do not, however, solve the document-grounded policy-following problem. They show what enterprise environments look like, not how to evaluate policy-following inside them.

## 5. Broader legal and regulatory NLP context

A broader literature in legal and regulatory NLP provides important background on static document understanding. Datasets and benchmarks such as CUAD, ContractNLI, MAUD, LexGLUE, LawBench, RegNLP, LEXam, and BLT study clause extraction, legal entailment, merger-agreement understanding, legal NLU, law-exam reasoning, regulation-grounded QA, and related legal-text operations. These works matter because they show that models can be evaluated on long documents, clause-level reasoning, obligation-sensitive interpretation, and structured legal tasks.

However, this body of work remains largely non-agentic. The dominant object being tested is document understanding, not policy-constrained behavior in an environment. That distinction is why the legal-NLP literature is important context but not sufficient evidence for the benchmark gap at issue here.

## 6. What the literature now supports

Across the 16 core papers, four conclusions are robust.

First, policy understanding is not a single ability. The literature repeatedly decomposes it into rule retrieval, interpretation, application, procedural execution, hierarchical enforcement, and compliance judgment.

Second, stateful evaluation changes what is being measured. Once agents interact with tools and shared state, final-answer evaluation is no longer enough. End-state correctness, trajectory correctness, and policy-compliant completion separate from one another.

Third, pressure reveals failures that static evaluation hides. ODCV-Bench and HAICOSYSTEM show that interaction and incentives surface violations that do not appear clearly in answer-based or single-turn settings.

Fourth, stronger capabilities do not guarantee safer or more compliant behavior. Several recent benchmarks converge on the same qualitative finding: models that are more capable in general reasoning or task completion may still fail badly on compliance-sensitive behavior.

These are not separate stories. Together they imply that a benchmark for operational policy-following must care about document interpretation, stateful execution, interactive pressure, and trajectory-level auditing at the same time.

## 7. The remaining gap

No benchmark in the current literature closes the full conjunction of requirements needed for operational policy-following evaluation.

- The reasoning-only benchmarks use real policy or regulation text, but the model never acts.
- The execution benchmarks evaluate agents in environments, but the governing policies are usually benchmark-authored templates, structured workflows, or executable graphs.
- The pressure and safety ecosystems stress-test compliance-adjacent behavior, but they are not primarily framed around agents reading real operational documents and being scored on document-grounded policy adherence.
- The enterprise-realism benchmarks provide realistic environments, but policy is implicit in workflow rather than explicit in documents.

That conjunction — real policy documents, stateful execution, executable tools, and trajectory-level compliance evaluation, with user interaction when the task requires it — remains unfilled.

## 8. Where pi-bench fits

Pi-bench is designed around that missing conjunction. It evaluates policy-following agents in operational roles such as finance, healthcare, and customer support, where behavior is governed by rules, regulations, clinical guidance, and company SOPs. The benchmark gives the agent the kind of policy artifact it would plausibly encounter in deployment, places it in a stateful environment with tools, and evaluates compliance over the trajectory of behavior rather than only at the end state. For tasks in which policy-relevant behavior depends on clarification, pressure, exception handling, or other interaction effects, the benchmark also introduces a simulated user.

The benchmark is therefore not just another environment for testing general agent competence. Its target is narrower and more operational: can an agent read a governing document, act in an interactive stateful setting, and remain compliant as the situation evolves?

This also explains why pi-bench should not begin from a fixed ontology of “policy intelligence.” The literature points to several recurring slices of policy-following, but it does not provide a single shared taxonomy. Pi-bench therefore uses a working taxonomy to organize evaluation, rather than claiming that prior work has already settled the dimension structure of the field.

## 9. Pi-bench's working taxonomy of policy-following

Prior work suggests several recurring slices of policy-following — interpretation, procedural adherence, hierarchical enforcement, pressure robustness, and multi-turn ecosystem risk among them — but it does not converge on a single shared dimension taxonomy. Pi-bench therefore adopts a working taxonomy that is informed by prior work but proposed by the benchmark itself.

### Policy Understanding

1. **Policy Activation** — does the agent recognize that a policy is relevant in the current situation?
2. **Policy Interpretation** — does the agent correctly understand the meaning, conditions, exceptions, and obligations expressed by the policy?
3. **Hierarchical Policy Resolution** — when multiple instructions or policy layers apply, does the agent resolve them in the correct precedence order?

### Policy Execution

4. **Procedural Compliance** — does the agent follow the required sequence of steps when order and completeness matter?
5. **Constraint-Preserving Execution** — does the agent avoid impermissible actions while pursuing the task?
6. **Temporal / State Reasoning** — does the agent reason correctly over prior actions, case state, deadlines, approvals, and state transitions that affect policy compliance?

### Policy Robustness & Auditability

7. **Pressure Robustness** — does the agent remain compliant when facing urgency, incentives, user pressure, or adversarial prompting?
8. **Escalation / Abstention** — does the agent know when to defer, clarify, escalate, abstain, or refuse?
9. **Trajectory-Level Auditability** — can policy compliance be evaluated over the full interaction trajectory rather than only from the final outcome?

These dimensions should be read as pi-bench's organizing evaluation framework, not as a taxonomy already agreed upon by the literature. Their role in the benchmark is practical: they structure scenario design, failure analysis, and coverage of policy-following behavior.

## References

### Core evidence base

- Balaji, S., Mishra, P., Sachdeva, A., and Agrawal, S. (2026). *Beyond IVR: Benchmarking Customer Support LLM Agents for Business-Adherence* (JourneyBench). EACL 2026 Industry Track.
- Barres, T., et al. (2025). *τ²-bench*. arXiv preprint.
- Diao, Y., et al. (2025). *GuideBench*. ACL 2025.
- Drouin, A., et al. (2024). *WorkArena: How Capable Are Web Agents at Solving Common Knowledge Work Tasks?* arXiv preprint.
- Guha, N., et al. (2023). *LegalBench*. NeurIPS 2023.
- Levy, S., et al. (2026). *ST-WebAgentBench: A Benchmark for Evaluating Safety and Trustworthiness in Web Agents*. ICLR 2026.
- Li, M. Q., et al. (2025). *ODCV-Bench*. arXiv preprint.
- Li, Z., et al. (2025). *SOPBench*. arXiv preprint.
- Marino, G., et al. (2025). *AIReg-Bench*. arXiv preprint.
- Song, D., et al. (2026). *Evaluating Implicit Regulatory Compliance in LLM Tool Invocation via Logic-Guided Synthesis* (LogiSafetyBench). arXiv preprint.
- Xu, F. F., et al. (2024). *TheAgentCompany*. arXiv preprint.
- Yang, et al. (2025). *POLIS-Bench*. arXiv preprint.
- Yao, S., et al. (2024). *τ-bench*. arXiv preprint.
- Zeng, Y., et al. (2024). *AIR-Bench 2024*. NeurIPS 2024.
- Zhou, X., et al. (2025). *HAICOSYSTEM*. COLM 2025.
- Zhou, et al. (2025). *RuleArena*. ACL 2025.

### Broader legal and regulatory NLP context

- Blair-Stanek, A., et al. (2023). *BLT*.
- Chalkidis, I., et al. (2022). *LexGLUE*. ACL 2022.
- Fan, et al. (2025). *LEXam*.
- Fei, et al. (2024). *LawBench*.
- Gokhan, et al. (2024). *RegNLP*.
- Hendrycks, D., et al. (2021). *CUAD*.
- Koreeda, Y., and Manning, C. D. (2021). *ContractNLI*.
- Wang, et al. (2023). *MAUD*.

