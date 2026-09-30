# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Dương Phương Hiểu
- **MSSV:** 03008
- **Lớp:** K4-L3B
- **Repository URL:** <https://github.com/dphieu/K4-L3B-Day13-DuongPhuongHieu-03008-Monitoring-LLMOps>
- **Commit SHA cuối:** 7b18d52b2cda69743f3265f3d513ff1d5ff06dd5
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-03008`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10a-prompt-promoted.png`, `evidence/10-prompt-rollback.png` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.txt` |
| Incident log | `evidence/13-incident-log.txt` |
| Incident trace | `evidence/14-incident-trace.txt` |

## 3. Kết quả kỹ thuật

Baseline CP0 không có snapshot số liệu được lưu trong repository, vì vậy không suy đoán lại số cũ. Cột kết quả cuối là lần chạy lại tại máy này với 10 request workload bình thường, incident tắt.

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---:|---:|---|
| `validate_logs.py` | 30/100 | 100/100 | 0 PII leak; xem `evidence/02-log-validator.txt`. |
| `validate_dashboard.py` | 6/6 | 6/6 | Dashboard contract hợp lệ; xem `evidence/03-dashboard-validator.txt`. |
| `pytest` | 22 passed | 22 passed | Chạy `python -m pytest -q`; xem `evidence/01-pytest.txt`. |
| Số traces hợp lệ | 0 | 10/10 | Workload mới được gửi tới project Langfuse cá nhân; trace list/metadata ở evidence 06–08. |
| Số PII leak | 3 | 0 | Validator quét email, phone, CCCD và card; xem evidence 02, 04, 05. |
| Latency P95 / TTFT P95 | 2653 ms / 50 ms (challenge `rag_slow`) | 1293 ms / 50 ms | P95 cuối gồm một request cold-start 1293 ms; 9 request còn lại 150–152 ms. |
| Retrieval success rate | 100% (5/5 challenge) | 100% (10/10) | `response_sent.tool_success=true` cho toàn bộ request chạy lại. |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa context cũ ở đầu request, nhận `x-request-id` hợp lệ dạng `req-<8-hex>` hoặc sinh ID mới, bind ID vào context `structlog`, rồi trả lại qua `x-request-id` và `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** Mỗi event có `ts`, `level`, `service`, `event`, `correlation_id`, `env`, `model`, `feature`, `session_id` và `user_id_hash` (SHA-256 rút gọn); event response bổ sung latency, TTFT, token, cost, quality và trạng thái retrieval.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` duyệt đệ quy chuỗi trong event trước file writer/JSON renderer. Nó redaction email, số điện thoại Việt Nam, CCCD, thẻ thanh toán và passport; payload chỉ lưu preview đã scrub.
- **Cách kiểm chứng kết quả:** Chạy workload có dữ liệu PII giả và `python scripts/validate_logs.py`; validator báo 100/100 và 0 potential PII leak trong `evidence/02-log-validator.txt`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Evidence 06–10 được chụp trong project `day13-k4-l3b-03008`; trace chứa `correlation_id`, `feature`, `model`, `env` để đối chiếu JSON log và không hiển thị API key.
- **Cấu trúc root/retrieval/generation observations:** Trace root `day13-agent-request` có agent `lab-agent-run`, hai child observation `retrieval` (RETRIEVER) và `generation` (GENERATION). Generation ghi token/cost và preview đã scrub.
- **Cách nối trace với log:** Dùng cùng `correlation_id`; ví dụ `req-d693fe48` trong log evidence 13 khớp trace `a140043c742c240d867e1d9715f22039` ở evidence 14.
- **Prompt name:** `day13-chat`.
- **Version/label baseline:** v1, labels `baseline` và trạng thái cuối cùng `production`.
- **Version/label candidate:** v2, labels `candidate` và `latest`.
- **Trace ID của mỗi version:** baseline/v1: `b12735898ddcedc2893d38cdad2418ac` (`req-22010d04`); candidate/v2: `307c0d72bc085d06f773b5bc69823f3e` (`req-7c3f342f`).
- **Cách promote và rollback `production`:** Đã promote `production` sang v2 (evidence 10a), sau đó rollback về v1 (evidence 10). Do đó ảnh 09 thể hiện versions/labels, còn evidence 10 là trạng thái sau rollback cuối cùng.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `scripts/render_dashboard.py` dựng dashboard từ `data/logs.jsonl`; evidence 11 thể hiện latency/TTFT, traffic, errors/retrieval success, cost, tokens và quality trong range 60 phút.
- **SLO và lý do chọn:** `config/slo.yaml` đặt SLO `fast_successful_requests`: 99.5% `response_sent` có latency không quá 3000 ms trong 28 ngày. Ngưỡng này tách tail latency bất thường của challenge (trên 2000 ms) và phản ánh trải nghiệm request thành công.
- **Cách tính error budget:** Target 99.5% cho error budget 0.5%. Ví dụ 10,000 request trong 28 ngày cho phép tối đa 50 request không đạt SLO trước khi cạn budget.
- **Ba alert và runbook tương ứng:** `HighLatencyP95` (>3000 ms/5m, warning), `HighErrorRate` (>2%/3m, critical) và `LowRetrievalSuccess` (<90%/5m, warning). Mỗi rule tại `config/alert_rules.yaml` trỏ đến runbook tương ứng trong `docs/alerts.md`.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`.
- **Khoảng thời gian điều tra:** 2026-09-30 09:36:25Z–09:36:50Z.
- **Triệu chứng từ metrics:** Với feature `monitoring`, P95 tăng từ 153 ms lên 2653 ms, vượt ngưỡng challenge 2000 ms; TTFT P95 vẫn 50 ms. Chi tiết ở `evidence/12-incident-metric.txt`.
- **Log line và correlation ID liên quan:** Event `response_sent` lúc 2026-09-30T09:36:38.104860Z có `correlation_id=req-d693fe48`, `latency_ms=2652`, `tool_success=true`; đây là slow-success, không phải retrieval failure. Xem `evidence/13-incident-log.txt`.
- **Trace ID và span gây ảnh hưởng:** Trace `a140043c742c240d867e1d9715f22039` có agent 2.654 s, `retrieval` 2.503 s và `generation` 0.151 s. Evidence 14 có mapping đầy đủ cho 5 request challenge.
- **Root cause:** Scenario chính thức `rag_slow` tạo thêm khoảng 2.5 giây ở retrieval. Metrics, log và child span đều nhất quán rằng retriever là phần chiếm gần toàn bộ latency.
- **Fix action:** Tắt scenario `rag_slow`, kiểm tra latency vector-store/upstream retrieval và chỉ mở lại traffic sau khi P95 xuống dưới ngưỡng challenge.
- **Preventive measure:** Duy trì alert P95, theo dõi riêng latency retrieval/generation và chạy smoke/load test retrieval trước khi deploy thay đổi RAG.

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đặt redaction ở processor trước cả file writer lẫn JSON renderer để không có đường serialize nào ghi PII thô xuống đĩa.
- **Một lỗi/blocker đã gặp:** Langfuse Cloud legacy trace-list API trả `LEGACY_API_UNAVAILABLE`, dù SDK v4 vẫn ingest trace bình thường.
- **Cách tìm nguyên nhân và xử lý:** Đối chiếu UI project cá nhân với `correlation_id` trong log thay cho legacy API; sau đó chụp evidence trace list, waterfall và metadata trực tiếp từ UI.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics khoanh vùng triệu chứng/time range; logs chọn request cụ thể bằng correlation ID; trace cùng ID chia latency theo retrieval/generation để kết luận root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Version/label giúp thử candidate trên cùng loại workload, promote không cần sửa code và rollback nhanh khi latency, token/cost hoặc quality xấu đi. SLO/alerts biến tín hiệu này thành hành động vận hành.
- **Điều quan trọng nhất đã học:** Không kết luận nguyên nhân chỉ từ P95; cần nối metric → log → trace để xác nhận span bất thường.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Không có snapshot số liệu CP0 gốc trong repository nên bảng chỉ ghi số liệu chạy lại, không dựng lại baseline bằng giả định. Commit SHA cần được cập nhật sau commit cuối cùng trước khi nộp.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [x] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
