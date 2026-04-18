# Benchmark UI Research Notes

This document captures UI and interaction patterns from modern benchmark
websites and component libraries, then translates them into usable patterns for
PI Bench. It is design research only. It does not specify backend integration,
submission workflows, or evaluation pipelines.

## Research Sources

Primary benchmark references:

- ARC Prize leaderboard: https://arcprize.org/leaderboard
- SWE-bench: https://www.swebench.com/
- LMArena leaderboard: https://lmarena.ai/leaderboard
- Epoch AI benchmarks: https://epoch.ai/benchmarks
- Aider leaderboards: https://aider.chat/docs/leaderboards/
- HELM / Stanford CRFM: https://crfm.stanford.edu/helm/
- MTEB / Hugging Face: https://huggingface.co/mteb

Modern UI/component references:

- shadcn/ui: https://ui.shadcn.com/
- Radix UI primitives: https://www.radix-ui.com/primitives
- Magic UI: https://magicui.design/
- Aceternity UI: https://ui.aceternity.com/

## What ARC Prize Gets Right

ARC Prize is the strongest direct reference for PI Bench because it makes a
benchmark feel like a serious measurement instrument.

Observed patterns:

- Chart-first page structure. The leaderboard starts with the data, not a
  marketing hero.
- Dark technical visual language: near-black background, off-white text, thin
  gray chart lines, and neon accents.
- Compact navigation with benchmark sections: leaderboards, benchmark versions,
  tasks, research, policy.
- Version toggle near the chart: ARC-AGI-1, ARC-AGI-2, ARC-AGI-3.
- Filter controls directly under the primary chart: author, model type, model.
- Scatter plot as primary visual: score vs cost per task.
- Download/export action for the chart.
- "Understanding the Leaderboard" explanation immediately after the chart.
- Verification policy and caveats are visible on the leaderboard page.
- Dense breakdown table with score columns, cost columns, and paper/code links.
- Small type, monospaced labels, and low visual ornamentation.

Adaptation for PI Bench:

- Use a chart-first homepage/leaderboard.
- Replace ARC's score-vs-cost core with PI-specific risk charts:
  Compliance vs ViolationEver, PI Score vs Cost, PassAll@k vs Cost.
- Keep visible testing-policy and scoring notes.
- Use a benchmark-set toggle for mock data slices such as Overall, Public,
  Verified, and Generated.
- Make "how to read this benchmark" a first-class content block.

Do not copy:

- ARC task/game visual identity.
- ARC-specific AGI framing.
- Prize competition/submission language.

## SWE-bench Patterns

SWE-bench is less visually distinctive than ARC but very strong for analysis.

Observed patterns:

- Multiple leaderboard variants.
- Search and filter controls.
- Compare selected models.
- Charts for resolved percentage, cost, release date, instance matrix, and
  category-level breakdowns.
- Export buttons for data and chart assets.
- Dense model rows and practical metadata.

Adaptation for PI Bench:

- Add model comparison views.
- Provide model x capability and model x scenario matrices.
- Add chart toggles instead of a single fixed chart.
- Use filtered URLs and export later, but for this prototype these remain
  static UI patterns only.

## LMArena Patterns

LMArena is useful for public-facing rank clarity.

Observed patterns:

- Tabbed categories.
- Top-ranked models get visual emphasis.
- Search and compact views.
- Rank, score, confidence/range, organization, and license columns.
- Category-specific leaderboards for broad user tasks.

Adaptation for PI Bench:

- Use category tabs for Overall, FINRA, Retail, Helpdesk, Deny, Escalate, and
  High Pressure.
- Use confidence-like visual language for reliability metrics:
  PassAll@k, PassAny@k, ViolationEver.
- Keep model/provider metadata visible.

## HELM Patterns

HELM is useful for scientific trust and multi-metric framing.

Observed patterns:

- Taxonomy-first evaluation.
- Clear distinction between scenarios, models, metrics, and raw runs.
- Multi-dimensional metrics instead of one score only.
- Strong methodology and limitations pages.

Adaptation for PI Bench:

- Make the 9-column policy capability taxonomy central.
- Explain deterministic checks, state checks, semantic checks, and canonical
  decision resolution.
- Separate aggregate score from risk metrics.
- Give methodology the same weight as leaderboard polish.

## MTEB / Hugging Face Patterns

MTEB and Hugging Face leaderboards are useful for filtering and ecosystem
metadata.

Observed patterns:

- Task-family filters.
- Modality/language/dataset filtering.
- Model details, links, and external artifacts.
- Community-friendly metadata tables.

Adaptation for PI Bench:

- Filter by domain, capability column, label, stressor, result status, provider,
  model type, and risk threshold.
- Give each scenario a compact metadata profile.

## Epoch / FrontierMath Patterns

Epoch's benchmark pages feel more like research-institute publications.

Observed patterns:

- Clean benchmark overview pages.
- Benchmark cards.
- Methodology-first writing.
- Capability framing and benchmark update history.
- Calm editorial style rather than flashy product UI.

Adaptation for PI Bench:

- Keep a polished methodology page.
- Use concise benchmark cards for domains and capability groups.
- Include clear limitations and status language.

## Aider Patterns

Aider is useful for reproducibility and run metadata.

Observed patterns:

- Dense leaderboards.
- Cost, tokens, commands, edit format, errors, and versions.
- Practical row-level details.

Adaptation for PI Bench:

- Expand model rows with mock run metadata: scenario set, trials, observer mode,
  cost, failure dimensions, and report links.
- Do not include any executable run controls in this prototype.

## Modern UI Component Trends

### Component Architecture

Current high-quality React UIs usually combine:

- shadcn/ui style copy-owned components for tables, dialogs, tabs, popovers,
  tooltips, badges, inputs, and dropdown menus.
- Radix primitives under the hood for accessible keyboard/focus behavior.
- Tailwind-style design tokens and utility classes.
- Framer Motion or CSS transitions for purposeful micro-interactions.
- Data visualization with SVG/canvas libraries or custom SVG for full control.

For PI Bench:

- Use Radix/shadcn-like primitives for filters, tabs, popovers, tooltips,
  drawer panels, and table menus.
- Keep components locally owned in `ui/` rather than depending on the benchmark
  Python code.

### Motion Trends

Useful motion patterns:

- Subtle table-row expansion.
- Filter chips appearing/disappearing with short fades.
- Heatmap cell hover that reveals exact metric and failed-check count.
- Chart point hover with a compact tooltip.
- Smooth tab indicator movement.
- Skeleton loading states for future data integration, but only mocked for now.

Avoid:

- Large decorative animations that compete with data.
- Heavy hero animations.
- Infinite background motion.
- Animated gradient blobs/orbs.

### Buttons And Controls

For a benchmark UI, buttons should feel precise and low-noise.

Recommended control types:

- Pill toggles for benchmark set/category.
- Compact outline buttons for chart mode and export-style actions.
- Square-ish select triggers with 4-8px radius.
- Search input with keyboard focus state.
- Filter chips with clear/remove affordance.
- Status badges for Verified, Preview, Community, Incomplete.

Avoid:

- Oversized marketing buttons.
- Glossy CTA buttons.
- Buttons that imply live backend actions, such as "Run Eval" or "Submit".

### Tables

Modern benchmark tables need:

- Sticky header.
- Sortable columns.
- Compact density.
- Expandable rows.
- Status badges.
- Inline sparklines or mini-bars.
- Horizontal scrolling on mobile.
- Tooltips for ambiguous metric names.

For PI Bench:

- The leaderboard table is a primary product surface, not a secondary detail.
- Use tabular numerals and monospaced metric columns.
- Expand rows to show synthetic evidence, not run controls.

### Charts

Modern benchmark chart patterns:

- Scatter plot for score vs cost/risk.
- Heatmap for capability profile.
- Stacked bars for failure modes.
- Small multiples for domain-specific breakdown.
- Interactive legends and hover tooltips.

For PI Bench:

- Primary chart: Compliance vs ViolationEver.
- Secondary chart modes: PI Score vs Cost, PassAll@k vs Cost.
- Signature visual: 9-column capability heatmap.

## PI Bench Design Principles

1. Data before marketing.
2. Trust before persuasion.
3. Risk metrics are first-class, not footnotes.
4. Dense tables are acceptable if filters and hierarchy are strong.
5. The 9-column taxonomy should be visually memorable.
6. Every metric needs a tooltip or explanation path.
7. The UI must not imply a backend pipeline exists.
8. All prototype data is synthetic and clearly mock-only where needed.

