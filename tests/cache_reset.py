"""Reset in-memory and on-disk test artifacts so runs do not leak stale state."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def clear_in_memory_caches() -> None:
    """Prompt YAML cache, guard rules, judge LLM singleton, metrics buffer."""
    from services.prompt_loader import reload_prompts
    from services.input_guard_rules import reload_guard_rules

    reload_prompts()
    reload_guard_rules()
    try:
        from tests.llm_judge import clear_judge_model_cache

        clear_judge_model_cache()
    except Exception:
        pass
    try:
        from tests.metrics_report import clear_metrics_buffer

        clear_metrics_buffer()
    except Exception:
        pass


def clear_in_memory_caches_for_new_scenario() -> None:
    """
    Call before each isolated scenario / graph_thread.reset (not full session reset).

    Same as :func:`clear_in_memory_caches` but no-ops if:

    * ``AGENT_TEST_SKIP_CACHE_RESET=1`` — same as full pytest session clear skip.
    * ``AGENT_TEST_SKIP_PER_SCENARIO_CACHE_RESET=1`` — only this lighter hook (faster local debug).
    """
    if os.environ.get("AGENT_TEST_SKIP_CACHE_RESET", "").lower() in ("1", "true", "yes"):
        return
    if os.environ.get("AGENT_TEST_SKIP_PER_SCENARIO_CACHE_RESET", "").lower() in (
        "1",
        "true",
        "yes",
    ):
        return
    clear_in_memory_caches()


def clear_disk_caches_for_tests() -> None:
    """FAISS index dir, log files, pytest cache dir (same as scripts/clear_local_state, without --pycache)."""
    vs = _ROOT / "data" / "vectorstore"
    if vs.exists():
        shutil.rmtree(vs)
    logd = _ROOT / "logs"
    if logd.is_dir():
        for f in sorted(logd.glob("*.log")):
            f.write_bytes(b"")
    pc = _ROOT / ".pytest_cache"
    if pc.exists():
        shutil.rmtree(pc)


def clear_test_artifacts(*, disk: bool = True) -> None:
    """
    Full reset for test runs. Called automatically from pytest session start.

    * ``AGENT_TEST_SKIP_CACHE_RESET=1`` — skip everything (rare debugging).
    * ``AGENT_TEST_SKIP_DISK_CACHE_RESET=1`` — in-memory only (keep vectorstore/logs on disk).
    """
    if os.environ.get("AGENT_TEST_SKIP_CACHE_RESET", "").lower() in ("1", "true", "yes"):
        return
    clear_in_memory_caches()
    if (
        disk
        and os.environ.get("AGENT_TEST_SKIP_DISK_CACHE_RESET", "").lower()
        not in ("1", "true", "yes")
    ):
        clear_disk_caches_for_tests()


def _emit(msg: str) -> None:
    print(msg, file=sys.stderr)


def main_cli() -> int:
    """When run as ``python -m tests.cache_reset`` (optional)."""
    import argparse

    p = argparse.ArgumentParser(description="Clear test caches (see docs/testing.md).")
    p.add_argument("--disk-only", action="store_true")
    p.add_argument("--memory-only", action="store_true")
    args = p.parse_args()
    if args.memory_only:
        clear_in_memory_caches()
        _emit("Cleared in-memory caches.")
    elif args.disk_only:
        clear_disk_caches_for_tests()
        _emit("Cleared disk test artifacts.")
    else:
        clear_test_artifacts(disk=True)
        _emit("Cleared in-memory and disk test artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main_cli())
