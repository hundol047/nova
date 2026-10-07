"""`python -m evaluation.validation_benchmark_round_n` -- Round N frozen validation set (see its module docstring)."""
from evaluation.benchmark import print_case_table, print_summary, run_all
from evaluation.validation_cases_round_n import VALIDATION_CASES_ROUND_N

if __name__ == "__main__":
    results = run_all(VALIDATION_CASES_ROUND_N)
    print("=== Round N frozen validation set (synthetic, single author, mock LLM; not an official score) ===")
    print_case_table(results)
    print_summary("Round N validation summary", results)
