# Agentic semantics

Tài liệu này mô tả semantics cốt lõi của tầng runtime cho hệ thống multi-agent trong Antigravity.

## 1) Vai trò agent và registry

`runtime/agent_registry.py` định nghĩa các role chuẩn:

- `planner`: phân rã mục tiêu thành kế hoạch/steps.
- `researcher`: thu thập tri thức, bằng chứng, và ngữ cảnh bổ sung.
- `executor`: thực thi step bằng tool hoặc hành động hệ thống.
- `reviewer`: kiểm định chất lượng, chính sách, và tính đúng đắn trước khi hoàn tất.

Semantics chính:

- Registry quản lý **factory** theo role, không giữ singleton mặc định.
- Mỗi lần `create(role, name)` trả về một instance mới từ factory.
- Lỗi lookup trả về danh sách agents khả dụng để dễ debug và fallback.

## 2) Handoff semantics giữa agents

`runtime/handoff.py` cung cấp `HandoffManager` để chuyển ngữ cảnh giữa các role theo task state.

Semantics:

1. Agent hiện tại gọi `handoff(...)` với `from_agent`, `to_agent`, `reason` và `task_state`.
2. Runtime lọc state theo `include_keys` hoặc default keys (`task_id`, `goal`, `artifacts`).
3. Runtime gắn metadata handoff hiện tại và `handoff_history`.
4. Mỗi lần handoff sinh `HandoffRecord` có timestamp UTC để audit.

Nhờ đó, mỗi agent chỉ nhận phần context cần thiết nhưng vẫn giữ được chuỗi chuyển giao đầy đủ.

## 3) Policy semantics

`runtime/policy.py` là rule engine cơ bản với 3 loại ràng buộc:

1. **Allow/Deny tool**
   - `deny_tools` luôn ưu tiên cao nhất.
   - Nếu có `allow_tools`, tool ngoài allow-list bị chặn.
2. **Budget token/time**
   - `Budget` theo dõi `used_tokens` và `used_seconds`.
   - Mọi hành động nên kiểm tra `check_budget(...)` trước khi chạy.
   - Khi chạy xong, runtime consume budget theo usage thật.
3. **Sensitive action approval**
   - Action nhạy cảm (`delete`, `transfer_funds`, `exfiltrate_data`, ...) cần approval explicit.
   - `require_approval(action, approved_actions=...)` trả về quyết định allow/deny.

`PolicyDecision` thống nhất shape quyết định: `allowed` + `reason`.

## 4) Retry semantics

`runtime/retry.py` chuẩn hoá retry/backoff theo loại lỗi:

- `tool_timeout`: retry ít hơn transient nhưng backoff lớn hơn validation.
- `validation_fail`: retry rất hạn chế (thường cần sửa input/prompt thay vì lặp vô hạn).
- `transient`: cho phép số lần retry cao hơn với exponential backoff.

Semantics thực thi:

1. Classify lỗi vào `ErrorType`.
2. Kiểm tra `should_retry(error_type, attempt)`.
3. Tính delay bằng `next_backoff(...)` (có jitter để tránh thundering herd).
4. Dùng `with_retry(...)` để bọc callback chung.

## 5) Checkpoint semantics

`runtime/checkpoint.py` cung cấp `CheckpointStore` dạng file-based để resume workflow:

- `save_step(workflow_id, step_id, state)` ghi snapshot JSON mỗi step.
- `load_step(...)` đọc lại checkpoint cụ thể.
- `latest_step(workflow_id)` lấy checkpoint mới nhất để resume tự động.

Mỗi checkpoint lưu:

- `workflow_id`
- `step_id`
- `saved_at` (UTC ISO-8601)
- `state` (payload của workflow tại thời điểm đó)

## 6) Runtime flow gợi ý

Một flow phối hợp đầy đủ:

1. Planner được lấy từ registry và tạo plan.
2. Handoff sang Researcher để bổ sung context.
3. Mỗi tool call qua PolicyEngine (tool + budget + approval).
4. Nếu lỗi, áp dụng Retry policy theo loại lỗi.
5. Sau mỗi step quan trọng, ghi CheckpointStore.
6. Reviewer xác nhận output cuối cùng trước khi complete.

## 7) Nguyên tắc mở rộng

- Giữ API runtime nhỏ, deterministic, và dễ test.
- Mọi quyết định quan trọng (policy/handoff/retry) nên có metadata để audit.
- Checkpoint nên được xem như nguồn sự thật để phục hồi sau crash/redeploy.
- Khi hệ thống lớn hơn, có thể thay file checkpoint bằng object store/DB mà vẫn giữ cùng semantics API.
