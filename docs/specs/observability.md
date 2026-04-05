# Observability Spec

Date: 2026-03-21
Status: Planned

## Goal

Start a benchmark run, open a local Grafana dashboard, and watch it live.
See every scenario as it completes — tool calls, decisions, check results,
failures. After the run finishes, the dashboard shows the full report:
leaderboard scores, failure modes by dimension, per-scenario details.

## Stack

All local. No Prometheus. No external services.

```
pi-bench runner
    ↓ structured events (JSON)
Loki (logs: scenario events, tool calls, check results)
Tempo (traces: per-scenario trajectories with tool call spans)
Mimir (metrics: pass rates, check counts, column scores)
    ↓
Grafana (dashboards: live progress, leaderboard, failure analysis)
```

Bring up with `docker compose up` or OrbStack. Single command.

## What gets emitted

### During the run (live)

Each scenario emits structured events as it progresses:

```json
{"event": "scenario_start", "scenario_id": "SCEN_010", "column": "Policy Activation", "label": "DENY", "timestamp": "..."}
{"event": "tool_call", "scenario_id": "SCEN_010", "tool": "verify_customer_identity", "step": 1, "timestamp": "..."}
{"event": "tool_call", "scenario_id": "SCEN_010", "tool": "query_account_status", "step": 3, "timestamp": "..."}
{"event": "tool_result", "scenario_id": "SCEN_010", "tool": "query_account_status", "result_keys": ["balance", "status"], "step": 4}
{"event": "scenario_end", "scenario_id": "SCEN_010", "passed": false, "termination": "agent_stop", "steps": 12, "duration_ms": 8500}
```

### After evaluation (per-scenario)

```json
{
  "event": "evaluation",
  "scenario_id": "SCEN_010",
  "passed": false,
  "dimensions": {
    "decision": {"passed": false, "total": 1, "failed": 1},
    "permissibility": {"passed": false, "total": 1, "failed": 1},
    "outcomes": {"passed": true, "total": 3, "failed": 0},
    "ordering": {"passed": true, "total": 2, "failed": 0},
    "state": {"passed": false, "total": 1, "failed": 1}
  },
  "failed_checks": ["E06_DECISION", "E04_NO_PROCESS_WIRE", "E07_STATE"]
}
```

### After the run (aggregate)

```json
{
  "event": "episode_complete",
  "model": "gpt-4o",
  "total": 37,
  "passed": 12,
  "compliance": 0.324,
  "by_column": {"Policy Activation": 0.33, "Policy Interpretation": 0.50, ...},
  "by_group": {"Policy Understanding": 0.42, "Policy Execution": 0.30, "Policy Boundaries": 0.25}
}
```

## Grafana dashboards

### 1. Live Progress

- Episode completion gauge (X / 37 scenarios)
- Per-scenario status tiles (green/red as they complete)
- Running tool call feed (live log stream from Loki)
- Current scenario trajectory (Tempo trace view)

### 2. Leaderboard

- 9-column bar chart (one bar per column, color = pass rate)
- 3-group summary (Policy Understanding / Execution / Boundaries)
- Overall compliance rate (big number)
- Model comparison table (when multiple models run)

### 3. Failure Analysis

- Dimension heatmap (5 dimensions × 9 columns, color = failure rate)
- Most-failed scenarios (sorted by check failure count)
- Failure mode pie chart (which dimensions fail most)
- Per-scenario drill-down (click → see full check results)

### 4. Trajectory Explorer

- Tempo trace view: select a scenario, see the full tool call sequence
- Each span = one tool call with arguments and result
- Decision span highlighted
- Failed checks annotated on the timeline

## Implementation

### Emitter (bolt-on, not in core)

```python
# pi_bench/observability/emitter.py
class ObservabilityEmitter:
    """Emits structured events to Loki/Tempo/Mimir."""

    def on_scenario_start(self, scenario_id, column, label): ...
    def on_tool_call(self, scenario_id, tool_name, step): ...
    def on_scenario_end(self, scenario_id, passed, report): ...
    def on_episode_complete(self, metrics, reports): ...
```

### Hook point

In `runner/core.py`, after each `_run_one()`:
```python
if emitter:
    emitter.on_scenario_end(sim["task_id"], reward["all_passed"], report)
```

The emitter is optional. If not configured, nothing is emitted.
The core benchmark code has zero dependency on observability.

### Docker Compose

```yaml
services:
  loki:
    image: grafana/loki:latest
    ports: ["3100:3100"]
  tempo:
    image: grafana/tempo:latest
    ports: ["3200:3200"]
  mimir:
    image: grafana/mimir:latest
    ports: ["9009:9009"]
  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    volumes:
      - ./dashboards:/var/lib/grafana/dashboards
```

### CLI integration

```bash
# Start observability stack
docker compose -f observability/docker-compose.yml up -d

# Run benchmark with observability
pi run-domain finra --agent-llm gpt-4o --observe

# Open dashboard
open http://localhost:3000
```

The `--observe` flag enables the emitter. Without it, benchmark runs
produce terminal output only (current behavior).
