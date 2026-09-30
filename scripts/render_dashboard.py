"""Render the six-panel dashboard contract from structured JSONL logs.

The generated HTML is deliberately dependency-free so it can be opened locally
or served by any static HTTP server for a screenshot during the lab demo.
"""

from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


def percentile(values: list[float], p: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((p / 100) * len(ordered) + 0.5) - 1))
    return ordered[index]


def read_records(log_path: Path) -> list[dict[str, Any]]:
    records = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def panel(title: str, unit: str, threshold: str, body: str) -> str:
    return f"""
    <section class=\"panel\">
      <h2>{html.escape(title)}</h2>
      <p class=\"meta\">Unit: {html.escape(unit)} · Threshold/SLO: {html.escape(threshold)}</p>
      <div class=\"values\">{body}</div>
    </section>"""


def metric(label: str, value: str) -> str:
    return f"<div><strong>{html.escape(value)}</strong><span>{html.escape(label)}</span></div>"


def render(records: list[dict[str, Any]]) -> str:
    received = [record for record in records if record.get("event") == "request_received"]
    sent = [record for record in records if record.get("event") == "response_sent"]
    failed = [record for record in records if record.get("event") == "request_failed"]
    latencies = [float(record["latency_ms"]) for record in sent if isinstance(record.get("latency_ms"), (int, float))]
    ttfts = [float(record["ttft_ms"]) for record in sent if isinstance(record.get("ttft_ms"), (int, float))]
    costs = [float(record["cost_usd"]) for record in sent if isinstance(record.get("cost_usd"), (int, float))]
    tokens_in = sum(int(record.get("tokens_in", 0)) for record in sent)
    tokens_out = sum(int(record.get("tokens_out", 0)) for record in sent)
    quality = [float(record["quality_score"]) for record in sent if isinstance(record.get("quality_score"), (int, float))]
    tool_results = [record["tool_success"] for record in sent if isinstance(record.get("tool_success"), bool)]
    retrieval_rate = 100 * sum(tool_results) / len(tool_results) if tool_results else 0.0
    error_rate = 100 * len(failed) / len(received) if received else 0.0
    error_types = Counter(str(record.get("error_type", "unknown")) for record in failed)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    panels = "".join(
        [
            panel(
                "Latency percentiles and TTFT",
                "ms",
                "P95 latency ≤ 3000 ms",
                metric("P50 latency", f"{percentile(latencies, 50):.0f}")
                + metric("P95 latency", f"{percentile(latencies, 95):.0f}")
                + metric("P99 latency", f"{percentile(latencies, 99):.0f}")
                + metric("P95 TTFT", f"{percentile(ttfts, 95):.0f}"),
            ),
            panel(
                "Request traffic",
                "requests/minute",
                "≥ 1 request/minute while demoing",
                metric("Requests", str(len(received)))
                + metric("Responses", str(len(sent)))
                + metric("Window", "60 min"),
            ),
            panel(
                "Error rate and retrieval success",
                "percent",
                "Error rate ≤ 2%; retrieval success ≥ 90%",
                metric("Error rate", f"{error_rate:.1f}%")
                + metric("Retrieval success", f"{retrieval_rate:.1f}%")
                + metric("Error types", ", ".join(error_types) or "none"),
            ),
            panel(
                "Cost over time",
                "USD",
                "Total ≤ $2.50 / 60 min",
                metric("Total cost", f"${sum(costs):.4f}")
                + metric("Average request cost", f"${mean(costs) if costs else 0:.4f}"),
            ),
            panel(
                "Input and output tokens",
                "tokens",
                "Total ≤ 50,000 tokens / 60 min",
                metric("Input tokens", f"{tokens_in:,}")
                + metric("Output tokens", f"{tokens_out:,}")
                + metric("Total tokens", f"{tokens_in + tokens_out:,}"),
            ),
            panel(
                "Quality proxy",
                "score (0–1)",
                "Mean quality ≥ 0.75",
                metric("Average quality", f"{mean(quality) if quality else 0:.2f}")
                + metric("Scored responses", str(len(quality))),
            ),
        ]
    )
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<title>Day 13 Monitoring Dashboard</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 0; background: #f5f7fb; color: #14213d; }}
main {{ max-width: 1100px; margin: auto; padding: 32px; }}
h1 {{ margin-bottom: 4px; }} .subtitle,.meta {{ color: #52627c; }}
.grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
.panel {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 10px #14213d14; }}
.panel h2 {{ margin: 0; font-size: 1.1rem; }} .values {{ display: flex; flex-wrap: wrap; gap: 20px; margin-top: 20px; }}
.values div {{ min-width: 115px; }} strong {{ display:block; font-size: 1.55rem; color: #005f73; }} span {{ font-size: .85rem; color:#52627c; }}
footer {{ margin-top: 22px; color:#52627c; font-size:.85rem; }} @media(max-width:700px){{.grid{{grid-template-columns:1fr}} main{{padding:16px}}}}
</style></head><body><main>
<h1>Day 13 Monitoring &amp; LLMOps</h1>
<p class=\"subtitle\">Structured-log dashboard · time range: last 60 minutes · refresh target: 30 seconds</p>
<div class=\"grid\">{panels}</div>
<footer>Source: <code>data/logs.jsonl</code> · generated {generated_at} · {len(records)} valid log records</footer>
</main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the Day 13 local dashboard")
    parser.add_argument("--logs", type=Path, default=Path("data/logs.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("submission/evidence/11-dashboard-overview.html"))
    args = parser.parse_args()
    if not args.logs.exists():
        raise SystemExit(f"Log file not found: {args.logs}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(read_records(args.logs)), encoding="utf-8")
    print(f"Dashboard written to {args.output}")


if __name__ == "__main__":
    main()
