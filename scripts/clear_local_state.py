#!/usr/bin/env python3
"""
Remove on-disk agent cache and log history for a clean local run.
Also clears in-memory prompt / guard / judge caches (same as pytest session start).

For ``--pycache`` only, this script walks ``__pycache__`` trees; the automatic
test reset (``tests/cache_reset.py``) does not remove ``__pycache__`` by default.

LangGraph conversation memory (MemorySaver) lives in the API process RAM only.
Restart api_server / any long-running process after this to clear in-memory thread state.
Ollama does not store your app chat; restarting Ollama is optional (frees model VRAM only).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _rm_tree(path: Path, *, dry: bool) -> list[str]:
    out: list[str] = []
    if not path.exists():
        return out
    if dry:
        return [f"[dry-run] would remove {path}"]
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    out.append(f"removed {path}")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done without deleting anything.",
    )
    p.add_argument(
        "--pycache",
        action="store_true",
        help="Also remove all __pycache__ directories under the agent repo (slower).",
    )
    args = p.parse_args()
    dry = args.dry_run
    lines: list[str] = []

    if not dry:
        from tests.cache_reset import clear_in_memory_caches, clear_disk_caches_for_tests

        clear_in_memory_caches()
        clear_disk_caches_for_tests()
        print(
            "Cleared in-memory caches, data/vectorstore, logs/*.log, .pytest_cache",
            file=sys.stderr,
        )
    else:
        lines.append(
            "[dry-run] would run clear_in_memory_caches() + clear_disk_caches_for_tests()"
        )

    if args.pycache:
        for d in sorted(_ROOT.rglob("__pycache__")):
            if d.is_dir():
                lines.extend(_rm_tree(d, dry=dry))

    for line in lines:
        print(line, file=sys.stderr)
    print(
        "\nIn-memory LangGraph state: restart your agent process (e.g. api_server) to clear thread history.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
