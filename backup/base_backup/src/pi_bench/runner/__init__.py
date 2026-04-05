"""Runner — multi-trial execution with ThreadPoolExecutor."""

from pi_bench.runner.core import run_domain
from pi_bench.runner.seeds import derive_trial_seeds

__all__ = ["run_domain", "derive_trial_seeds"]
