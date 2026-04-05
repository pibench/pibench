# LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in Large Language Models

**Paper:** Guha et al., arXiv:2308.11462, August 2023 (NeurIPS 2023)
**PDF:** `papers/legalbench_2308.11462.pdf`

---

## What Is It About?

LegalBench is an open-source, collaboratively constructed benchmark for evaluating whether LLMs can perform **legal reasoning**. It was built by an interdisciplinary team of 40+ contributors from law schools, CS departments, and legal-tech companies. The key motivation: existing legal benchmarks either (a) focus on finetuned models rather than few-shot LLM capabilities, or (b) treat "legal reasoning" as a monolithic skill instead of decomposing it into distinct reasoning types lawyers actually recognize.

The benchmark contains **162 tasks** drawn from **36 distinct data sources**, each measuring a specific type of legal reasoning. Tasks have an average of 563 samples and at least 50 samples each.

---

## The Typology: Six Types of Legal Reasoning

LegalBench organizes tasks using the **IRAC framework** (Issue, Rule, Application, Conclusion) plus two additional categories:

| Category | # Tasks | What It Measures |
|---|---|---|
| **Issue-spotting** | 17 | Can the LLM identify which legal issues a set of facts raises? |
| **Rule-recall** | 5 | Can the LLM state the correct legal rule for an issue? (Measures hallucination.) |
| **Rule-application** | 16 | Can the LLM explain *how* a rule applies to facts? (Evaluated for correctness + analysis quality.) |
| **Rule-conclusion** | 16 | Can the LLM predict the correct legal outcome under a given rule? |
| **Interpretation** | 118 | Can the LLM parse and understand legal text (contracts, policies, statutes)? |
| **Rhetorical-understanding** | 10 | Can the LLM reason about legal argumentation structure? |

The heavy skew toward Interpretation (118/162) reflects that contract/document analysis is the most practically demanded legal-AI use case.

---

## What Did They Experiment?

### Models Evaluated (20 total)
- **Commercial (3):** GPT-4, GPT-3.5 (text-davinci-003), Claude-1 (v1.3)
- **Open-source (17):** Models at 3B, 7B, and 13B parameter scales from families including Flan-T5, LLaMA-2, OPT, Vicuna, Falcon, MPT, BLOOM, Incite, WizardLM

### Evaluation Method
- Few-shot prompting (0-8 in-context examples per task)
- Classification tasks: balanced accuracy (exact match)
- Rule-application: manual evaluation by a law-trained individual for correctness and analysis quality
- Temperature = 0 for all generations

### Three-Part Study
1. **Sweeping performance comparison** across all 20 models and 5 reasoning categories
2. **Deep-dive comparison** of GPT-4 vs GPT-3.5 vs Claude-1 with fine-grained "slice" analysis
3. **Prompt engineering experiments**: latent knowledge vs explicit rules, plain vs technical language, sensitivity to in-context demonstrations

---

## Key Findings

### 1. Overall Performance Hierarchy
GPT-4 dominates across nearly all categories. Average scores by category (top models):

| Model | Issue | Rule-Recall | Conclusion | Interpretation | Rhetorical |
|---|---|---|---|---|---|
| GPT-4 | 82.9 | 59.2 | 89.9 | 75.2 | 79.4 |
| GPT-3.5 | 60.9 | 46.3 | 78.0 | 72.6 | 66.7 |
| Claude-1 | 58.1 | 57.7 | 79.5 | 67.4 | 68.9 |

### 2. Bigger Models Generally Win (But Not Always)
- Within families, larger models outperform smaller ones
- But architecture/training choices matter: Flan-T5-XXL (11B) beats Claude-1 on issue-spotting and rhetorical-understanding despite being far smaller
- WizardLM-13B is worst on issue-spotting but best among peers on rule-recall

### 3. Rule-Application Quality (GPT-4 >> others)
| Model | Correctness | Analysis |
|---|---|---|
| GPT-4 | 82.2 | 79.7 |
| GPT-3.5 | 58.5 | 44.2 |
| Claude-1 | 61.4 | 59.0 |

Common errors: arithmetic mistakes, citing wrong portion of a rule, generating conclusions without reasoning.

### 4. Claude-1 Surprisingly Strong on Rule-Recall
Claude-1 nearly matches GPT-4 on rule-recall tasks (57.7 vs 59.2) and outperforms on 3 of 5 tasks. This is the only category where Claude-1 is competitive with GPT-4.

### 5. Open-Source vs Commercial Gap
- Gap is **largest** for rule-conclusion tasks (multi-step reasoning)
- Gap is **smallest** for issue-spotting and rhetorical-understanding
- Open-source models can match or beat GPT-3.5/Claude-1 on some categories (Flan-T5-XXL)

### 6. Performance Degrades on Harder Sub-Tasks
Slice analysis reveals where models fail:
- **Hearsay:** Both GPT-3.5 and GPT-4 handle standard hearsay and non-assertive conduct perfectly, but struggle with "not introduced to prove truth" (25-45%) and non-verbal hearsay (33-75%)
- **Abercrombie trademark:** Models excel on generic/fanciful marks but struggle with suggestive/arbitrary ones
- **Interpretation:** Performance drops sharply on longer texts (Supply Chain Disclosure: 74-75%) and multi-class tasks (MAUD: GPT-4 drops to 47.8%)

### 7. Prompt Engineering Insights
- **Explicit rule descriptions help** on some tasks (abercrombie, diversity jurisdiction) but not others — LLMs can't always rely on latent legal knowledge
- **Plain language prompts outperform technical legal language** on 4 of 5 tested tasks (by up to 21 points)
- **In-context demonstration choice matters significantly** — on some tasks, best vs worst prompt differs by 20+ points (balanced accuracy)

---

## Limitations (Acknowledged by Authors)

- English-only, skewed toward American law
- Tasks have objectively correct answers — doesn't handle "reasonable minds may differ" scenarios
- Doesn't test long-document reasoning (context window constraints at time of writing)
- Evaluates IRAC steps independently, not as a multi-hop chain
- Only general-domain LLMs tested (no law-specific fine-tuned models)
- Some tasks may have leaked into pretraining data

---

## Why This Matters for Policy Benchmarking

1. **Collaborative construction model**: Domain experts (lawyers) designed and hand-crafted tasks, not just CS researchers. This ensures tasks are legally meaningful, not just technically interesting.
2. **Typology bridges disciplines**: The IRAC-based framework gives lawyers and ML developers a shared vocabulary for discussing LLM capabilities.
3. **Granular evaluation over aggregate scores**: Slice-level analysis reveals *where* models fail, not just *how much* they fail.
4. **Benchmark as a platform**: Open-source, extensible, designed for contributions from the legal community.
5. **Practical relevance**: Tasks were chosen because they either measure practically useful capabilities or reasoning skills lawyers find interesting.
