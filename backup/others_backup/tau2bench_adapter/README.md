# tau2bench adapter

Thin adapter that maps the pi_bench interface (used by our BDD tests)
to tau2-bench's actual implementation. This lets us run our behavioral
contracts against tau2's working code to see which pass and which fail.

NOT part of pi_bench. This is a test harness only.

## Usage

```bash
cd workspace
PYTHONPATH=tau2bench_adapter pytest tests/step_defs/test_environment.py -v
```
