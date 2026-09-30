"""Produce a sanitized Metrics → Logs → Traces incident note for CP3.

The official challenge file remains local and ignored. This script only reads it,
the application log, and observations from the student's configured Langfuse
project; it never prints API credentials or raw model input/output.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.challenge import load_challenge
from app.tracing import get_langfuse_client


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_slow_logs(
    log_path: Path, *, feature: str, threshold_ms: int, start: datetime, end: datetime
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        timestamp = record.get("ts")
        if not isinstance(timestamp, str):
            continue
        try:
            occurred_at = parse_timestamp(timestamp)
        except ValueError:
            continue
        if not (
            start <= occurred_at <= end
            and record.get("event") == "response_sent"
            and record.get("feature") == feature
            and isinstance(record.get("latency_ms"), (int, float))
            and record["latency_ms"] > threshold_ms
        ):
            continue
        matches.append(record)
    return matches


def observation_rows(start: datetime, end: datetime) -> list[Any]:
    response = get_langfuse_client().api.observations.get_many(
        from_start_time=start,
        to_start_time=end,
        fields="core,basic,usage,metadata",
        limit=100,
    )
    return list(response.data)


def render(
    *, challenge_id: str, incident: str, threshold_ms: int, start: datetime, end: datetime,
    slow_logs: list[dict[str, Any]], observations: list[Any]
) -> str:
    correlation_ids = {record["correlation_id"] for record in slow_logs}
    grouped: dict[str, list[Any]] = {correlation_id: [] for correlation_id in correlation_ids}
    for observation in observations:
        metadata = getattr(observation, "metadata", None) or {}
        correlation_id = metadata.get("correlation_id") if isinstance(metadata, dict) else None
        if correlation_id in grouped:
            grouped[correlation_id].append(observation)

    lines = [
        "# CP3 incident investigation",
        "",
        f"- Challenge ID: `{challenge_id}`",
        f"- Incident: `{incident}`",
        f"- Investigation window (UTC): `{start.isoformat()}` to `{end.isoformat()}`",
        f"- Symptom threshold: `latency_ms > {threshold_ms}`",
        "",
        "## Metrics and logs",
        "",
        "| Timestamp (UTC) | Correlation ID | API latency (ms) | Retrieval success |",
        "|---|---|---:|---|",
    ]
    for record in slow_logs:
        lines.append(
            f"| {record['ts']} | `{record['correlation_id']}` | "
            f"{record['latency_ms']} | {record.get('tool_success')} |"
        )

    lines.extend(["", "## Matching Langfuse observations", ""])
    for correlation_id, rows in grouped.items():
        lines.append(f"### `{correlation_id}`")
        if not rows:
            lines.append("No observation returned in this time window.")
            continue
        lines.extend(["", "| Trace ID | Observation | Type | Latency (s) | Parent observation |", "|---|---|---|---:|---|"])
        for observation in sorted(rows, key=lambda item: str(getattr(item, "start_time", ""))):
            lines.append(
                f"| `{getattr(observation, 'trace_id', '')}` | "
                f"{getattr(observation, 'name', '')} | {getattr(observation, 'type', '')} | "
                f"{float(getattr(observation, 'latency', 0) or 0):.3f} | "
                f"`{getattr(observation, 'parent_observation_id', '') or '-'}` |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create sanitized CP3 incident evidence")
    parser.add_argument("--from", dest="from_time", required=True, help="UTC ISO-8601 start")
    parser.add_argument("--to", dest="to_time", required=True, help="UTC ISO-8601 end")
    parser.add_argument("--logs", type=Path, default=Path("data/logs.jsonl"))
    parser.add_argument(
        "--output", type=Path, default=Path("submission/evidence/incident-investigation.md")
    )
    args = parser.parse_args()
    load_dotenv(REPO_ROOT / ".env")
    start, end = parse_timestamp(args.from_time), parse_timestamp(args.to_time)
    if end <= start:
        raise SystemExit("--to must be after --from")

    challenge = load_challenge()
    slow_logs = read_slow_logs(
        args.logs,
        feature=challenge.affected_feature,
        threshold_ms=challenge.latency_threshold_ms,
        start=start,
        end=end,
    )
    if not slow_logs:
        raise SystemExit("No slow challenge response logs found in the supplied window")
    report = render(
        challenge_id=challenge.challenge_id,
        incident=challenge.incident,
        threshold_ms=challenge.latency_threshold_ms,
        start=start,
        end=end,
        slow_logs=slow_logs,
        observations=observation_rows(start, end),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Incident evidence written to {args.output}")


if __name__ == "__main__":
    main()
