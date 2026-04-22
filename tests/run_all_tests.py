"""Run pytest: fast (default) or integration suite."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_AGENT_ROOT = Path(__file__).resolve().parent.parent


def run_tests(run_integration: bool = False) -> int:
    cmd = [sys.executable, "-m", "pytest", str(_AGENT_ROOT / "tests"), "-v", "--tb=short"]
    env = os.environ.copy()
    if run_integration:
        env.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
        env.setdefault("OMP_NUM_THREADS", "1")
        env.setdefault("AGENT_TEST_MINIMAL_LOGS", "1")
        env.setdefault("AGENT_SCENARIO_LIVE_LOGS", "0")
        cmd.extend(["-m", "integration"])
    print("Running:", " ".join(cmd), f"(cwd={_AGENT_ROOT})")
    proc = subprocess.run(cmd, cwd=str(_AGENT_ROOT), env=env if run_integration else None)
    return int(proc.returncode)


if __name__ == "__main__":
    integration = "--integration" in sys.argv
    if integration:
        print("Mode: integration tests only (-m integration)")
    else:
        print("Mode: default (unit/mocked; excludes -m integration)")
    code = run_tests(run_integration=integration)
    raise SystemExit(code)
