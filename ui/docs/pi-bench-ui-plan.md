# PI Bench UI Plan

This document defines the planned website structure and design process for the
static PI Bench UI prototype. All pages use synthetic data. No backend
integration, evaluation pipeline, submission flow, or live run controls are in
scope.

## Scope

Build inside `ui/` only:

- Static frontend prototype.
- Synthetic leaderboard data.
- Synthetic scenario data.
- Synthetic model detail data.
- Static methodology content.
- No imports from the Python benchmark codebase.
- No reads from real `scenarios/`, `domains/`, or `src/`.
- No run/evaluate/submit/upload controls.

## Final Page Map

```text
/
  Homepage

/leaderboard
  Full mock leaderboard, charts, filters, capability heatmap

/models
  Model comparison index

/models/:modelId
  Mock model profile and breakdown

/scenarios
  Synthetic scenario explorer

/scenarios/:scenarioId
  Synthetic scenario detail

/methodology
  Benchmark design, scoring, taxonomy, reliability, limitations
```

Not in scope:

```text
/submit
/runs
/api
/dashboard
/evaluate
```

## Design Direction

PI Bench should feel like a research-grade policy compliance instrument.

Visual traits:

- Dark technical interface.
- Near-black background.
- Off-white primary text.
- Muted gray secondary text.
- Thin borders and grid lines.
- Monospaced metric/table typography.
- Low-radius buttons and inputs.
- Semantic accent colors:
  - Green: compliant/pass.
  - Red: violation/fail.
  - Yellow: warning/provisional.
  - Blue/cyan: neutral metric.
  - Magenta: selected/highlighted.

Avoid:

- Generic SaaS hero sections.
- Decorative gradient orbs.
- Purple/blue gradient-heavy themes.
- Oversized marketing cards.
- UI that suggests live backend execution.

## Homepage Components

### 1. Global Header

Purpose:

- Establish identity and navigation.

Elements:

- PI Bench wordmark.
- Nav links: Home, Leaderboard, Models, Scenarios, Methodology.
- Status pill: `static prototype` or `mock data`.

Interactions:

- Sticky header.
- Subtle active nav indicator.
- Mobile menu.

### 2. Benchmark Intro

Purpose:

- Explain what the benchmark is in one glance.

Elements:

- `PI Bench`
- `Policy interpretation benchmark for AI agents`
- Short supporting sentence about policies, tools, pressure, and compliance.
- Small metadata row:
  - `v0.1 prototype`
  - `3 domains`
  - `9 capability columns`
  - `synthetic data`

No "Run Eval" or "Submit" CTA.

### 3. Headline Metrics Strip

Purpose:

- Give immediate benchmark shape.

Mock metrics:

- PI Score.
- Compliance.
- ViolationEver.
- PassAll@k.
- Scenarios.
- Domains.

Threshold behavior:

- PI Score >= 85: strong.
- PI Score 70-84: moderate.
- PI Score 50-69: warning.
- PI Score < 50: weak.
- ViolationEver >= 25: high risk.
- PassAll@k < 50: reliability warning.

### 4. Primary Risk Chart

Purpose:

- Make PI Bench's risk framing visually distinct.

Default chart:

- X-axis: ViolationEver.
- Y-axis: Compliance.
- Each point: synthetic model.
- Color: provider.
- Stroke/dash: result status.

Chart modes:

- Compliance vs ViolationEver.
- PI Score vs Cost.
- PassAll@k vs Cost.

Interactions:

- Hover tooltip.
- Chart mode toggle.
- Provider legend.
- Highlight selected model.

### 5. Leaderboard Preview

Purpose:

- Show the top models without requiring navigation.

Columns:

- Rank.
- Model.
- Provider.
- PI Score.
- Compliance.
- ViolationEver.
- PassAll@k.
- Status.

Interaction:

- Row hover.
- Link to full leaderboard/model detail.

### 6. 9-Column Capability Heatmap

Purpose:

- Make PI Bench's taxonomy the signature visual.

Columns:

- Policy Activation.
- Policy Interpretation.
- Evidence Grounding.
- Procedural Compliance.
- Authorization & Access Control.
- Temporal / State Reasoning.
- Safety Boundary Enforcement.
- Privacy & Information Flow.
- Escalation / Abstention.

Rows:

- Top synthetic models.

Cell behavior:

- Color intensity = score.
- Red marker = high failure concentration.
- Tooltip = exact score, failed checks, most common failure dimension.

### 7. Domain Snapshot

Purpose:

- Show benchmark coverage and domain-specific model behavior.

Cards/panels:

- FINRA.
- Retail.
- Helpdesk.

Each panel:

- Domain score.
- Compliance.
- Most common failure mode.
- Scenario count.

### 8. Failure Mode Snapshot

Purpose:

- Show how agents fail, not just whether they fail.

Dimensions:

- Decision Correctness.
- Action Permissibility.
- Required Outcomes.
- Temporal Constraints.
- State Correctness.
- Semantic Quality.

Visualization:

- Horizontal bars or compact matrix.

### 9. Methodology Teaser

Purpose:

- Surface trust and scoring philosophy.

Cards:

- Deterministic checks.
- Canonical decision.
- Reliability metrics.
- Scenario taxonomy.

Link:

- Methodology page.

## Leaderboard Page Components

### 1. Leaderboard Header

Elements:

- Page title.
- Mock-data status.
- Last updated synthetic date.
- Benchmark set toggle:
  - Overall.
  - Public.
  - Verified.
  - Generated.

### 2. Chart Panel

Components:

- Large scatter plot.
- Chart mode segmented control.
- Provider/status legend.
- Hover tooltip.

### 3. Filters

Controls:

- Search model.
- Provider.
- Status.
- Domain.
- Capability column.
- Label.
- Risk threshold.
- Cost range.

Filter patterns:

- Compact dropdowns.
- Active filter chips.
- Clear all control.

### 4. Full Leaderboard Table

Columns:

- Rank.
- Model / Agent.
- Provider.
- Type.
- PI Score.
- Compliance.
- ViolationEver.
- PassAll@k.
- FINRA.
- Retail.
- Helpdesk.
- Cost / Scenario.
- Status.
- Details.

Table behavior:

- Sortable columns.
- Sticky header.
- Expandable rows.
- Compact density.
- Mobile horizontal scroll.

Expanded row:

- Mini 9-column capability bars.
- Domain breakdown.
- Decision behavior.
- Top synthetic failure modes.
- Mock metadata.

## Models Page Components

### Model Index

Purpose:

- Browse model profiles without relying only on the leaderboard.

Components:

- Search.
- Provider filter.
- Model-type filter.
- Compact model cards or table.
- Sort by PI Score, risk, cost, reliability.

### Model Detail

Sections:

- Model header.
- Score summary.
- Capability profile.
- Domain breakdown.
- Decision behavior.
- Failure mode breakdown.
- Synthetic example failures.

Decision behavior metrics:

- ALLOW pass rate.
- DENY pass rate.
- ESCALATE pass rate.
- Over-refusal.
- Under-refusal.
- Escalation accuracy.

## Scenarios Page Components

### Scenario Explorer

Purpose:

- Make benchmark coverage visible and understandable.

Columns:

- Scenario ID.
- Domain.
- Expected label.
- Primary capability.
- Stressors.
- Deterministic checks.
- Semantic checks.
- Difficulty/risk tag.

Filters:

- Domain.
- Label.
- Capability.
- Stressor.
- Check type.

### Scenario Detail

Sections:

- Summary.
- Policy clauses.
- Available tools.
- User pressure script.
- Expected behavior.
- Evaluation checks.
- Common failure pattern.

All content is synthetic.

## Methodology Page Components

Sections:

- What PI Bench measures.
- Domains.
- 9-column taxonomy.
- Decision labels.
- Deterministic checks.
- State checks.
- Semantic checks.
- Reliability metrics.
- Verified/preview status definitions for display only.
- Limitations and mock-data note.

## Design Component Inventory

Core components:

- Header.
- Footer.
- Metric card.
- Status badge.
- Segmented control.
- Search input.
- Filter dropdown.
- Filter chip.
- Data table.
- Expandable row.
- Tooltip.
- Drawer/detail panel.
- Tabs.
- Heatmap.
- Scatter chart.
- Bar chart.
- Domain card.
- Methodology card.

Motion components:

- Tab indicator slide.
- Row expansion.
- Tooltip fade.
- Chart point hover.
- Heatmap cell highlight.
- Filter chip enter/exit.

Use motion sparingly. The product should feel precise, not flashy.

## Mock Data Requirements

Create synthetic records that cover all UI states:

- High score and low risk.
- High score but high ViolationEver.
- Low cost but unreliable.
- Expensive and strong.
- Domain specialist.
- Good at ALLOW, weak at DENY.
- Good at ESCALATE, over-refuses ALLOW.
- Preview/incomplete status.
- Community/mock status.
- Missing domain values.

Synthetic data should include:

- Models.
- Providers.
- Scores.
- Domain breakdowns.
- Capability breakdowns.
- Decision behavior.
- Failure modes.
- Scenario metadata.

## Step-by-Step Design Process

### Step 1: Benchmark Framing

Define the product promise in UI terms:

- PI Bench measures policy compliance under operational pressure.
- The UI must prioritize risk, reliability, and evidence.

Output:

- Final site map.
- Metric glossary.
- Primary chart decision.

### Step 2: Visual Language

Define:

- Color tokens.
- Typography scale.
- Border/radius system.
- Table density.
- Chart style.
- Badge/status colors.

Output:

- CSS token file.
- Global layout rules.

### Step 3: Mock Data Modeling

Create mock data to stress:

- thresholds.
- sorting.
- missing values.
- warnings.
- expanded rows.
- domain specialists.

Output:

- `mockModels`.
- `mockScenarios`.
- `mockMetrics`.

### Step 4: Homepage Prototype

Build first because it defines the design system.

Output:

- Header.
- Metric strip.
- Risk chart.
- Leaderboard preview.
- Capability heatmap.
- Domain snapshot.

### Step 5: Leaderboard Prototype

Build the dense data surface.

Output:

- Filters.
- Chart modes.
- Sortable table.
- Expandable model rows.

### Step 6: Model And Scenario Details

Build drill-down pages.

Output:

- Model detail page.
- Scenario explorer.
- Scenario detail page.

### Step 7: Methodology Page

Build trust and explanation.

Output:

- Taxonomy sections.
- Scoring explanation.
- Reliability explanation.
- Limitations.

### Step 8: Responsive Pass

Check:

- 1440px desktop.
- 1024px tablet.
- 390px mobile.
- Tables scroll rather than breaking.
- Chart labels do not overlap excessively.
- Text remains readable.

### Step 9: Polish Pass

Tune:

- hover states.
- focus states.
- micro-interactions.
- table density.
- chart colors.
- empty/missing/provisional states.

### Step 10: Static Prototype Review

Confirm:

- No backend calls.
- No eval controls.
- No submission controls.
- Everything is inside `ui/`.
- Mock-data status is clear.

## Out-of-Scope Guardrails

Do not add:

- Run evaluation button.
- Submit result page.
- Upload result control.
- API client.
- CLI wrapper.
- Imports from benchmark backend.
- Real scenario ingestion.
- Real model invocation.

