#!/usr/bin/env python3
"""Run multi-turn scenarios from YAML; judge each assistant reply with the LLM judge only."""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

_AGENT_ROOT = Path(__file__).resolve().parent.parent
if str(_AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_AGENT_ROOT))

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("AGENT_TEST_MINIMAL_LOGS", "1")

ScenarioKind = Literal["normal", "hostile"]


class TurnSpec(BaseModel):
    user: str = Field(..., min_length=1, max_length=16000)
    scenario_kind: ScenarioKind | None = None


class ScenarioSpec(BaseModel):
    id: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    thread_id: str | None = Field(None, max_length=500)
    customer_id: str | None = Field(None, max_length=200)
    scenario_kind: ScenarioKind | None = None
    turns: list[TurnSpec] = Field(..., min_length=1)


class DefaultsSpec(BaseModel):
    customer_id: str = Field(default="yaml_scenario_customer", max_length=200)
    scenario_kind: ScenarioKind = "normal"


class SuiteFile(BaseModel):
    name: str = Field(default="unnamed_suite", max_length=300)
    description: str | None = Field(None, max_length=4000)
    defaults: DefaultsSpec = Field(default_factory=DefaultsSpec)
    scenarios: list[ScenarioSpec] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _strip_strings(self) -> SuiteFile:
        self.name = self.name.strip()
        for s in self.scenarios:
            s.id = s.id.strip()
        return self


def _banner(title: str) -> None:
    line = "=" * 62
    bold, reset = "\033[1m", "\033[0m"
    print(f"\n{bold}{line}{reset}", file=sys.stderr)
    print(f"{bold}  {title}{reset}", file=sys.stderr)
    print(f"{bold}{line}{reset}\n", file=sys.stderr)


def _kind_for_turn(
    defaults: DefaultsSpec,
    scenario: ScenarioSpec,
    turn: TurnSpec,
) -> ScenarioKind:
    if turn.scenario_kind is not None:
        return turn.scenario_kind
    if scenario.scenario_kind is not None:
        return scenario.scenario_kind
    return defaults.scenario_kind


def run_suite(path: Path, *, output_dir: Path | None = None) -> int:
    from tests.cache_reset import clear_test_artifacts

    clear_test_artifacts()

    from tests.llm_env_select import (
        judge_llm_skipped,
        judge_provider_label,
        llm_provider_label,
        prepare_judge_llm_env,
        prepare_llm_env,
        verify_judge_llm_runtime_available,
        verify_llm_runtime_available,
    )
    from tests.llm_judge import evaluate_turn, format_judge_failure, write_judge_rubric_chart
    from tests.llm_test_utils import (
        build_tool_summary,
        continue_state,
        last_assistant_text,
        llm_unreachable,
        make_receptionist_state,
    )
    from tests.metrics_report import TurnMetricRecord, build_static_html, write_metrics_json
    from tests.scenario_display import emit_scenario_turn_box

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        print("YAML root must be a mapping.", file=sys.stderr)
        return 1
    suite = SuiteFile.model_validate(raw)

    err = prepare_llm_env(os.environ)
    if err:
        print(f"\033[91m{err}\033[0m", file=sys.stderr)
        return 2
    err_run = verify_llm_runtime_available(os.environ)
    if err_run:
        print(f"\033[91m{err_run}\033[0m", file=sys.stderr)
        return 2

    judge_active = not judge_llm_skipped(os.environ)
    if judge_active:
        err_j = prepare_judge_llm_env(os.environ)
        if err_j:
            print(f"\033[91mJudge: {err_j}\033[0m", file=sys.stderr)
            return 2
        err_jr = verify_judge_llm_runtime_available(os.environ)
        if err_jr:
            print(f"\033[91mJudge: {err_jr}\033[0m", file=sys.stderr)
            return 2

    if os.getenv("AGENT_LOG_FULL_PROMPTS", "").lower() not in ("1", "true", "yes"):
        from utils.logger import apply_scenario_trace_logging

        apply_scenario_trace_logging()

    from graph.main import receptionist_graph

    _banner(f"YAML scenarios — {suite.name}")
    print(
        f"LLM: {llm_provider_label(os.environ)}  |  Judge: {judge_provider_label(os.environ)}",
        file=sys.stderr,
    )

    totals = {
        "turns": 0,
        "correct": 0,
        "no_pii": 0,
        "attack_handling_ok": 0,
        "grounded_in_tools": 0,
        "tool_use_reasonable": 0,
        "passed": 0,
    }
    metrics_rows: list[TurnMetricRecord] = []
    use_telemetry = (os.environ.get("AGENT_METRICS_TELEMETRY", "").lower() in ("1", "true", "yes"))

    for sc in suite.scenarios:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", f"{suite.name}-{sc.id}").strip("-")[:120]
        thread = sc.thread_id or slug or f"yaml-{sc.id}"[:120]
        customer = sc.customer_id or suite.defaults.customer_id
        last: dict[str, Any] | None = None
        print(f"\n\033[36m━━ scenario\033[0m {sc.id!r}  thread={thread!r}", file=sys.stderr)

        for tix, turn in enumerate(sc.turns):
            sk = _kind_for_turn(suite.defaults, sc, turn)
            if last is None:
                state = make_receptionist_state(
                    turn.user, conversation_id=thread, customer_id=customer
                )
            else:
                state = continue_state(last, turn.user)
            cfg: dict[str, Any] = {"configurable": {"thread_id": thread}}
            t0 = time.perf_counter()
            super_n: int | None = None
            node_hist: dict[str, int] | None = None
            try:
                if use_telemetry:
                    from tests.graph_telemetry import invoke_with_telemetry

                    last, super_n, node_hist = invoke_with_telemetry(
                        receptionist_graph, state, cfg, include_node_histogram=True
                    )
                else:
                    last = receptionist_graph.invoke(state, cfg)
            except BaseException as exc:
                if llm_unreachable(exc):
                    print(f"\033[93mSkip (LLM unreachable): {exc}\033[0m", file=sys.stderr)
                    return 2
                raise
            elapsed = time.perf_counter() - t0
            out_text = last_assistant_text(last.get("messages"))
            ts = build_tool_summary(last.get("messages"))
            emit_scenario_turn_box(turn.user, last, elapsed, out_text)

            if not judge_active:
                print(
                    "\033[33mJudge skipped (AGENT_SKIP_LLM_JUDGE=1); no rubric for this turn.\033[0m",
                    file=sys.stderr,
                )
                if output_dir:
                    metrics_rows.append(
                        TurnMetricRecord(
                            source="yaml",
                            suite=suite.name,
                            scenario_id=sc.id,
                            turn_index=tix,
                            user_text=turn.user[:4000],
                            elapsed_s=elapsed,
                            intent=last.get("intent") if last else None,
                            active_agent=last.get("active_agent") if last else None,
                            super_step_count=super_n,
                            node_histogram=node_hist,
                            tool_summary=ts[:2000],
                            judge_skipped=True,
                            correct=None,
                            no_pii=None,
                            attack_handling_ok=None,
                            grounded_in_tools=None,
                            tool_use_reasonable=None,
                            passed=None,
                            reason=None,
                        )
                    )
                continue

            totals["turns"] += 1
            verdict = evaluate_turn(turn.user, out_text, scenario_kind=sk, tool_summary=ts)
            write_judge_rubric_chart(verdict)
            totals["correct"] += int(verdict.correct)
            totals["no_pii"] += int(verdict.no_pii)
            totals["attack_handling_ok"] += int(verdict.attack_handling_ok)
            totals["grounded_in_tools"] += int(verdict.grounded_in_tools)
            totals["tool_use_reasonable"] += int(verdict.tool_use_reasonable)
            totals["passed"] += int(verdict.passed)
            if output_dir:
                metrics_rows.append(
                    TurnMetricRecord(
                        source="yaml",
                        suite=suite.name,
                        scenario_id=sc.id,
                        turn_index=tix,
                        user_text=turn.user[:4000],
                        elapsed_s=elapsed,
                        intent=last.get("intent") if last else None,
                        active_agent=last.get("active_agent") if last else None,
                        super_step_count=super_n,
                        node_histogram=node_hist,
                        tool_summary=ts[:2000],
                        judge_skipped=False,
                        correct=verdict.correct,
                        no_pii=verdict.no_pii,
                        attack_handling_ok=verdict.attack_handling_ok,
                        grounded_in_tools=verdict.grounded_in_tools,
                        tool_use_reasonable=verdict.tool_use_reasonable,
                        passed=verdict.passed,
                        reason=verdict.reason[:800] if verdict.reason else None,
                    )
                )

            if not verdict.passed:
                if output_dir and metrics_rows:
                    outd = output_dir.resolve()
                    outd.mkdir(parents=True, exist_ok=True)
                    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    jp = outd / f"metrics-yaml-{stamp}.json"
                    write_metrics_json(jp, turns=metrics_rows, source="yaml")
                    build_static_html(jp, outd / f"metrics-yaml-{stamp}.html")
                    print(f"\nMetrics written (partial): {jp}\n", file=sys.stderr)
                print(format_judge_failure(verdict), file=sys.stderr)
                return 1

    _banner("Suite summary")
    n = totals["turns"]
    if output_dir and metrics_rows:
        outd = output_dir.resolve()
        outd.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        jp = outd / f"metrics-yaml-{stamp}.json"
        write_metrics_json(jp, turns=metrics_rows, source="yaml")
        build_static_html(jp, outd / f"metrics-yaml-{stamp}.html")
        print(f"\nMetrics written: {jp}\n", file=sys.stderr)
    if judge_active and n:
        print(
            f"  Turns judged: {n}  |  rubric pass counts  "
            f"correct={totals['correct']}/{n}  no_pii={totals['no_pii']}/{n}  "
            f"attack_handling_ok={totals['attack_handling_ok']}/{n}  "
            f"grounded_in_tools={totals['grounded_in_tools']}/{n}  "
            f"tool_use_reasonable={totals['tool_use_reasonable']}/{n}  "
            f"all_pass={totals['passed']}/{n}",
            file=sys.stderr,
        )
    elif not judge_active:
        print("  Judge was skipped; only turn boxes were printed.", file=sys.stderr)
    if judge_active:
        print("\033[32mOK\033[0m — all turns passed the judge.\n", file=sys.stderr)
    else:
        print("\033[32mOK\033[0m — suite finished (judge disabled).\n", file=sys.stderr)
    return 0


# Doc / prose placeholders people paste as the first argument (Unicode ellipsis, etc.)
_YAML_PATH_PLACEHOLDERS = frozenset(
    {
        "…",
        "...",
        "—",
    }
)


def _is_placeholder_yaml_path(raw: Path) -> bool:
    s = (raw.name or "").strip()
    if not s:
        return True
    if s in _YAML_PATH_PLACEHOLDERS or s == "-":
        return True
    return s.lower() in ("path", "to", "file", "here", "suite.yml")


def main() -> int:
    default_eg = _AGENT_ROOT / "tests" / "scenarios" / "example_scenarios.yml"
    p = argparse.ArgumentParser(
        description="Run YAML-defined receptionist scenarios (LLM judge per turn).",
    )
    p.add_argument(
        "yaml_file",
        nargs="?",
        default=None,
        type=Path,
        help="Path to scenario YAML (default: tests/scenarios/example_scenarios.yml).",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Write metrics JSON + static HTML for this run (e.g. tests/reports).",
    )
    args = p.parse_args()
    if args.yaml_file is None:
        path = default_eg
    elif _is_placeholder_yaml_path(args.yaml_file):
        print(
            f"\033[33mNote:\033[0m {args.yaml_file!r} looks like a doc placeholder, not a file. "
            f"Using the default example suite. Pass a real YAML path if you meant a different file.\n",
            file=sys.stderr,
        )
        path = default_eg
    else:
        path = args.yaml_file
    if not path.is_file():
        print(
            f"Not a file: {path}\n"
            f"  Tip: use a real path like tests/scenarios/example_scenarios.yml, or omit the first "
            f"argument for the default suite. (Do not paste the ellipsis “…” from the docs.)\n",
            file=sys.stderr,
        )
        return 1
    return run_suite(path.resolve(), output_dir=args.output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
