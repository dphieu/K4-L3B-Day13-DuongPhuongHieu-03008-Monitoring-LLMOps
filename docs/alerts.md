# Alert runbook

All alerts are symptom-based, notify Slack `#k4-l3b-alerts`, and are owned by
`student-03008`. Start with metrics to identify the time window, then use the
correlation ID in `data/logs.jsonl` to locate the corresponding Langfuse trace.

## HighLatencyP95

- Severity/duration: `warning`, sustained for `5m`.
- Trigger: P95 of `response_sent.latency_ms` exceeds `3000 ms`.
- User impact: answers arrive slowly, including requests that ultimately succeed.
- First checks: confirm P95/P99 and TTFT in the latency panel; select a slow
  `response_sent` log and its correlation ID; compare retrieval and generation
  durations in the matching trace.
- Mitigation: disable the active practice incident; if a prompt version is
  implicated, move `production` back to the previous verified version; reduce
  concurrent load while investigating.

## HighErrorRate

- Severity/duration: `critical`, sustained for `3m`.
- Trigger: `request_failed / request_received > 2%`.
- User impact: requests fail with HTTP 500 and no answer is returned.
- First checks: confirm the error-rate panel; group `request_failed` logs by
  `error_type` and retrieve a correlation ID; inspect the failing child span.
- Mitigation: disable the active practice incident; restore the last working
  dependency configuration; pause affected traffic if failures persist.

## LowRetrievalSuccess

- Severity/duration: `warning`, sustained for `5m`.
- Trigger: retrieval success among `response_sent.tool_success` is below `90%`.
- User impact: answers may be unsupported or requests can fail before generation.
- First checks: confirm retrieval success in the errors panel; inspect retrieval
  fields in the affected logs; compare retrieval outputs/status in the trace.
- Mitigation: disable the practice scenario, verify vector-store connectivity,
  and fall back to a safe general-answer path until retrieval is recovered.
