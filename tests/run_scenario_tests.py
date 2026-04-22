#!/usr/bin/env python3
"""Run LLM scenario tests under tests/integration/ (see project README → Testing)."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_AGENT_ROOT = Path(__file__).resolve().parent.parent
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

from tests.llm_env_select import judge_provider_label, llm_provider_label, prepare_judge_llm_env, prepare_llm_env


def _banner(title: str) -> None:
    line = "=" * 62
    bold, reset = "\033[1m", "\033[0m"
    dim = "\033[2m"
    print(f"\n{bold}{line}{reset}")
    print(f"{bold}  {title}{reset}")
    print(f"{bold}{line}{reset}\n{dim}Agent LLM:{reset} {llm_provider_label(os.environ)}")
    print(f"{dim}Judge LLM:{reset} {judge_provider_label(os.environ)}\n")


def _mark_expression(suite: str) -> str:
    s = suite.lower().strip()
    if s in ("all", "scenarios"):
        return "integration and (conversation or ordering or payment or cancellation or security)"
    if s == "flows":
        return "integration and (conversation or ordering or payment or cancellation)"
    if s in ("conversation", "ordering", "payment", "cancellation", "security"):
        return f"integration and {s}"
    raise ValueError(f"unknown suite: {suite!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AI receptionist scenario tests.")
    _suites = (
        "all",
        "flows",
        "conversation",
        "ordering",
        "payment",
        "cancellation",
        "security",
        "list",
    )
    parser.add_argument(
        "suite",
        nargs="?",
        default="all",
        choices=_suites,
        help="Scenario group to run (see descriptions in module docstring).",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Less pytest output (-q)")
    parser.add_argument(
        "--live-logs",
        action="store_true",
        help="Stream WARNING+ logs to the terminal (noisy). Default: capture everything; failures show dumps.",
    )
    args = parser.parse_args()

    if args.suite.strip().lower() == "list":
        print("Suites: all, flows, conversation, ordering, payment, cancellation, security, list")
        return 0

    err = prepare_llm_env(os.environ)
    if err:
        print(f"\033[91m{err}\033[0m", file=sys.stderr)
        return 2
    err_j = prepare_judge_llm_env(os.environ)
    if err_j:
        print(f"\033[91m{err_j}\033[0m", file=sys.stderr)
        return 2

    suite = args.suite.strip().lower()
    mark = _mark_expression("all" if suite == "all" else suite)
    _banner(f"Scenario tests — {suite.upper()}")

    env = os.environ.copy()
    env["AGENT_SCENARIO_RUN"] = "1"
    env["AGENT_SCENARIO_LIVE_LOGS"] = "1" if args.live_logs else "0"
    env.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("AGENT_TEST_MINIMAL_LOGS", "1")
    pytest_cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(_AGENT_ROOT / "tests" / "integration"),
        "-m",
        mark,
        "--tb=line",
        "--color=yes",
    ]
    if args.live_logs:
        pytest_cmd.extend(
            [
                "--capture=tee-sys",
                "-o",
                "log_cli=true",
                "-o",
                "log_cli_level=WARNING",
                "-o",
                "log_cli_format=%(asctime)s %(levelname)s [%(name)s] %(message)s",
            ]
        )
    if args.quiet:
        pytest_cmd.append("-q")
    else:
        pytest_cmd.extend(["-v", "--no-header"])

    proc = subprocess.run(pytest_cmd, cwd=str(_AGENT_ROOT), env=env)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
