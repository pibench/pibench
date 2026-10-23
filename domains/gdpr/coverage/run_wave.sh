#!/usr/bin/env bash
# Run one GDPR wave in both conditions on this laptop and record it.
#   domains/gdpr/coverage/run_wave.sh <wave> [pushbacks] [concurrency]
# Neutral first, then stress, one condition at a time (laptop-safe: 8 GB RAM).
# Re-running resumes: episodes already completed in the save file are kept.
# Each run saves to results/wave<wave>_<condition>.json, then is added to the
# run registry (RUNS.md / runs.json) and summarised in wave<wave>_report.txt.
set -u
WAVE="$1"; PUSHBACKS="${2:-3}"; CONC="${3:-2}"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"
R=domains/gdpr/coverage/results
IDS=$(python3 -c "import json,glob; print(','.join(sorted(json.load(open(f))['meta']['scenario_id'] for f in glob.glob('scenarios/gdpr/GDPR_W${WAVE}_*.json'))))")
read -r AGENT_MODEL USER_MODEL JUDGE_MODEL <<<"$(python3 -c "import sys; sys.path[:0]=['src']; from pi_bench.omnigent import DEFAULT_AGENT_MODEL as a, DEFAULT_USER_MODEL as u; from pi_bench.evaluator.llm_judge import get_judge_model as j; print(a, u, j().split(':')[-1])")"
PV=$(python3 -c "import json,glob; fs=glob.glob('scenarios/gdpr/GDPR_W${WAVE}_*.json'); print(2 if any(isinstance(json.load(open(f))['user_simulation'].get('pressure'), dict) for f in fs) else 1)")
for COND in neutral stress; do
  OUT="$R/wave${WAVE}_${COND}.json"
  START=$(date +%Y-%m-%dT%H:%M)
  # Resume: run only episodes not yet completed in $OUT (into a part file), then merge.
  [ -f "$OUT.part" ] && python3 domains/gdpr/coverage/resume.py merge "$OUT" "$OUT.part"  # an interrupted part
  TODO=$(python3 domains/gdpr/coverage/resume.py todo "$OUT" "$IDS")
  if [ -n "$TODO" ]; then
    pi run-domain gdpr --agent omnigent --user omnigent --user-condition "$COND" --pushbacks "$PUSHBACKS" \
       --concurrency "$CONC" --retry-failed 1 --task-ids "$TODO" --save-to "$OUT.part" >> "$R/wave${WAVE}_${COND}.log" 2>&1
    echo "wave $WAVE $COND exit=$?"
    python3 domains/gdpr/coverage/resume.py merge "$OUT" "$OUT.part"
  fi
  END=$(date +%Y-%m-%dT%H:%M)
  # A run where many episodes errored (e.g. the model backend was unreachable) is not a result.
  if ! python3 -c "import json,sys; s=json.load(open('$OUT'))['simulations']; e=sum(x.get('termination_reason')=='agent_error' for x in s); print(f'{e}/{len(s)} agent_error'); sys.exit(1 if not s or e > 0.2*len(s) else 0)"; then
    echo "wave $WAVE $COND not recorded: too many errored episodes"; exit 1
  fi
  python3 domains/gdpr/coverage/registry.py add --wave "$WAVE" --condition "$COND" --results "$OUT" \
     --agent-model "$AGENT_MODEL" --user-model "$USER_MODEL" --judge-model "$JUDGE_MODEL" --pressure-version "$PV" \
     --pushbacks "$PUSHBACKS" --concurrency "$CONC" --started "$START" --finished "$END" --notes "${NOTES:-}"
done
python3 domains/gdpr/coverage/report_run.py "wave${WAVE}" > "$R/wave${WAVE}_report.txt" 2>&1
# Compressed copies are what git keeps (raw save files are 50-85 MB).
for F in "$R"/wave${WAVE}_*.json; do gzip -9 -k -f "$F"; done
python3 domains/gdpr/coverage/failures.py
python3 domains/gdpr/coverage/ledger.py
echo "wave $WAVE done"
