"""Aggregated test-run metrics: JSON for CI and optional static HTML summary."""
from __future__ import annotations

import json
import os
import statistics
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any, Literal

SourceKind = Literal["pytest", "yaml", "unknown"]


def _try_git_sha() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path(__file__).resolve().parent.parent,
        )
        if out.returncode == 0 and (out.stdout or "").strip():
            return (out.stdout or "").strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return None


@dataclass
class TurnMetricRecord:
    source: str
    suite: str
    scenario_id: str
    turn_index: int
    user_text: str
    elapsed_s: float
    intent: str | None
    active_agent: str | None
    super_step_count: int | None
    node_histogram: dict[str, int] | None
    tool_summary: str
    judge_skipped: bool
    correct: bool | None
    no_pii: bool | None
    attack_handling_ok: bool | None
    grounded_in_tools: bool | None
    tool_use_reasonable: bool | None
    passed: bool | None
    reason: str | None = None


# In-memory buffer for pytest session (single-process; avoid xdist workers mixing).
_TURNS: list[TurnMetricRecord] = []


def clear_metrics_buffer() -> None:
    _TURNS.clear()


def append_turn(record: TurnMetricRecord) -> None:
    _TURNS.append(record)


def buffer_snapshot() -> list[TurnMetricRecord]:
    return list(_TURNS)


@dataclass
class MetricsRunFile:
    generated_at: str
    source: str
    git_sha: str | None
    llm_provider: str
    judge_provider: str
    environment: str
    turns: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def build_summary(turns: list[dict[str, Any]], *, source: str) -> dict[str, Any]:
    n = len(turns)
    if not n:
        return {
            "source": source,
            "turns": 0,
            "judge_mode": "n/a",
            "pass_rate": None,
            "mean_elapsed_s": None,
            "median_elapsed_s": None,
        }
    judged = [t for t in turns if not t.get("judge_skipped")]
    jn = len(judged)
    passed = [t for t in judged if t.get("passed") is True]
    elapsed = [float(t["elapsed_s"]) for t in turns if t.get("elapsed_s") is not None]
    rub = {
        "correct": sum(1 for t in judged if t.get("correct") is True),
        "no_pii": sum(1 for t in judged if t.get("no_pii") is True),
        "attack_handling_ok": sum(1 for t in judged if t.get("attack_handling_ok") is True),
        "grounded_in_tools": sum(1 for t in judged if t.get("grounded_in_tools") is True),
        "tool_use_reasonable": sum(1 for t in judged if t.get("tool_use_reasonable") is True),
    }
    return {
        "source": source,
        "turns": n,
        "judged_turns": jn,
        "judge_mode": "full" if jn else "skipped",
        "pass_rate": (len(passed) / jn) if jn else None,
        "rubric_pass_counts": {k: f"{v}/{jn}" for k, v in rub.items()} if jn else {},
        "mean_elapsed_s": (sum(elapsed) / len(elapsed)) if elapsed else None,
        "median_elapsed_s": (statistics.median(elapsed) if len(elapsed) > 1 else (elapsed[0] if elapsed else None)),
    }


def write_metrics_json(
    path: str | Path,
    *,
    turns: list[TurnMetricRecord] | list[dict[str, Any]],
    source: SourceKind = "unknown",
) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tdicts: list[dict[str, Any]]
    if not turns:
        tdicts = []
    elif isinstance(turns[0], TurnMetricRecord):
        tdicts = [asdict(x) for x in turns]  # type: ignore[assignment]
    else:
        tdicts = [dict(x) for x in turns]  # type: ignore[arg-type]
    env_label = (os.environ.get("LLM_PROVIDER") or "ollama").lower().strip()
    from tests.llm_env_select import judge_provider_label, llm_provider_label  # local import

    m = MetricsRunFile(
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        source=source,
        git_sha=_try_git_sha(),
        llm_provider=llm_provider_label(os.environ),
        judge_provider=judge_provider_label(os.environ),
        environment=env_label,
        turns=tdicts,
        summary=build_summary(tdicts, source=source),
    )
    p.write_text(json.dumps(m.to_jsonable(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def write_metrics_from_buffer(path: str | Path, *, source: str) -> Path:
    return write_metrics_json(path, turns=buffer_snapshot(), source=source)  # type: ignore[arg-type]


def _html_pass_rate(summary: dict[str, Any]) -> str:
    pr = summary.get("pass_rate")
    if pr is None:
        return "—"
    return f"{100.0 * float(pr):.1f}%"


def _html_num(x: Any, fmt: str) -> str:
    if x is None:
        return "—"
    return format(float(x), fmt)


def build_static_html(
    json_path: str | Path,
    out_html: str | Path | None = None,
) -> str:
    """Build HTML string from a metrics JSON file; if out_html, write to disk."""
    p = Path(json_path)
    data = json.loads(p.read_text(encoding="utf-8"))
    turns: list[dict[str, Any]] = data.get("turns") or []
    summary: dict[str, Any] = data.get("summary") or {}
    meta = f"{escape(data.get('source', ''))} · {escape(data.get('generated_at', ''))} · {escape(data.get('llm_provider', ''))}"

    def pass_cell(t: dict[str, Any]) -> str:
        if t.get("judge_skipped"):
            return "—"
        v = t.get("passed")
        if v is True:
            return '<span class="ok">PASS</span>'
        if v is False:
            return '<span class="bad">FAIL</span>'
        return "—"

    rows: list[str] = []
    for t in turns:
        rows.append(
            "<tr>"
            f"<td>{escape(t.get('suite', ''))}</td>"
            f"<td>{escape(t.get('scenario_id', ''))}</td>"
            f"<td class=\"n\">{t.get('turn_index', 0)}</td>"
            f"<td class=\"t\">{escape((t.get('user_text') or '')[:200])}</td>"
            f"<td class=\"n\">{t.get('elapsed_s', 0) if t.get('elapsed_s') is not None else '—'}</td>"
            f"<td class=\"n\">{escape(str(t.get('super_step_count'))) if t.get('super_step_count') is not None else '—'}</td>"
            f"<td>{pass_cell(t)}</td>"
            "</tr>"
        )

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Agent metrics — {escape(data.get("source", "run"))}</title>
  <style>
    :root {{ font-family: system-ui, sans-serif; color: #0f172a; background: #f1f5f9; }}
    body {{ max-width: 1200px; margin: 1.5rem auto; padding: 0 1rem; }}
    h1 {{ font-size: 1.25rem; color: #0c4a6e; }}
    .meta {{ color: #64748b; font-size: 0.9rem; margin-bottom: 1rem; }}
    .cards {{ display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 1rem 0; }}
    .card {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 0.75rem 1rem; min-width: 8rem; }}
    .card strong {{ display: block; color: #64748b; font-size: 0.75rem; text-transform: uppercase; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; font-size: 0.9rem; }}
    th, td {{ text-align: left; padding: 0.5rem 0.65rem; border-bottom: 1px solid #e2e8f0; }}
    th {{ background: #f8fafc; color: #334155; font-weight: 600; }}
    .n {{ font-variant-numeric: tabular-nums; white-space: nowrap; }}
    .t {{ max-width: 24rem; overflow: hidden; text-overflow: ellipsis; }}
    .ok {{ color: #059669; font-weight: 600; }}
    .bad {{ color: #dc2626; font-weight: 600; }}
    h2 {{ font-size: 1rem; color: #334155; margin-top: 1.5rem; }}
  </style>
</head>
<body>
  <h1>Receptionist agent test metrics</h1>
  <p class="meta">{meta}</p>
    <div class="cards">
    <div class="card"><strong>Turns</strong> {summary.get("turns", 0)}</div>
    <div class="card"><strong>Pass rate (judged)</strong> {_html_pass_rate(summary)}</div>
    <div class="card"><strong>Mean turn latency (s)</strong> {_html_num(summary.get("mean_elapsed_s"), ".2f")}</div>
    <div class="card"><strong>Median (s)</strong> {_html_num(summary.get("median_elapsed_s"), ".2f")}</div>
  </div>
  <h2>Per turn</h2>
  <table>
    <thead>
      <tr>
        <th>Suite</th>
        <th>Scenario</th>
        <th>#</th>
        <th>User (trimmed)</th>
        <th>s</th>
        <th>Steps</th>
        <th>Judge</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows) if rows else '<tr><td colspan="7">No turns</td></tr>'}
    </tbody>
  </table>
  <h2>Summary (JSON)</h2>
  <pre style="background:#0f172a;color:#e2e8f0;padding:1rem;border-radius:8px;overflow:auto;font-size:0.8rem;">{escape(json.dumps(summary, indent=2))}</pre>
</body>
</html>"""

    if out_html:
        out_p = Path(out_html)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(body, encoding="utf-8")
    return body

