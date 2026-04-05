# Purple Reference Agent

Reference implementation of the purple (assessed) agent for pi-bench bootstrap protocol testing.

**NOT shipped with pi-bench.** This is a test harness only, following the same pattern as `tau2bench_adapter/`.

## What it does

- Implements the purple side of the A2A bootstrap handshake
- Advertises `urn:pi-bench:policy-bootstrap:v1` in its agent card
- Caches policy + tools on bootstrap, prepends them on subsequent turns
- Uses litellm for actual LLM calls

## Usage

```bash
cd workspace

# Run unit tests (bootstrap.py functions)
PYTHONPATH=src:. python -m pytest purple_reference/tests/test_bootstrap.py -v

# Run integration tests (green ↔ purple)
PYTHONPATH=src:. python -m pytest purple_reference/tests/test_a2a_smoke.py -v

# Run the server standalone (for manual testing)
PYTHONPATH=src:. python -m purple_reference.server
```

## Structure

```
purple_reference/
├── server.py              # Starlette A2A server
├── README.md
└── tests/
    ├── conftest.py        # Shared fixtures
    ├── test_bootstrap.py  # 24 unit tests for bootstrap.py
    └── test_a2a_smoke.py  # Integration tests (green↔purple)
```
