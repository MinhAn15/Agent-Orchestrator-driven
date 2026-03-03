# Benchmark KPIs and Reproducible Baseline

Tài liệu này định nghĩa KPI cho orchestrator và cung cấp baseline công khai để cộng đồng có thể reproduce.

## KPI definition

### 1) Task Completion Rate
- **Định nghĩa**: `successful_runs / total_runs`.
- **Ý nghĩa**: đo tỷ lệ hệ thống hoàn tất task đúng kỳ vọng end-to-end.
- **Mục tiêu khuyến nghị**: `>= 0.90` trong bộ scenario chuẩn.

### 2) Mean Recovery Time (MRT)
- **Định nghĩa**: thời gian trung bình (ms) để workflow phục hồi sau lần lỗi tool đầu tiên.
- **Cách đo**:
  1. Inject lỗi transient trong các scenario có retry/fallback.
  2. Ghi timestamp của lần lỗi đầu tiên và timestamp khi workflow quay lại trạng thái thành công.
  3. Tính trung bình trên tất cả run có recovery.
- **Mục tiêu khuyến nghị**: càng thấp càng tốt; theo baseline hiện tại mục tiêu `< 2000ms`.

### 3) Tool Failure Resilience
- **Định nghĩa**: tỷ lệ run có thể phục hồi thành công khi tool lỗi.
- **Công thức**: `recovered_runs / failure_injected_runs`.
- **Mục tiêu khuyến nghị**: `>= 0.80`.

## Standard benchmark scenarios
Bộ task chuẩn nằm ở `benchmarks/scenarios.json` gồm 7 workflow:
1. single tool success
2. multi-tool linear chain
3. conditional branch
4. retry after tool failure
5. degraded fallback
6. long-context summary
7. parallel subtasks

## Methodology (reproducible)

- Script: `benchmarks/run_benchmarks.py`
- Mặc định dùng pseudo-simulator deterministic với seed cố định (`2026`) để bất kỳ ai cũng có thể chạy lại.
- Mỗi scenario chạy nhiều lần (`--runs-per-scenario`, mặc định 20).
- Output gồm:
  - `summary` (KPI tổng hợp)
  - `results` (chi tiết từng run)

### Reproduce steps

```bash
python3 benchmarks/run_benchmarks.py --runs-per-scenario 20 --seed 2026 --output benchmarks/baseline_results.json
```

## Public baseline results

Baseline hiện tại được publish tại `benchmarks/baseline_results.json`.

Ví dụ summary (seed 2026, 20 runs/scenario):
- task_completion_rate: 0.9929
- mean_latency_ms: 1492.58
- mean_cost_usd: 0.00266
- mean_tokens: 1640.71
- tool_failure_resilience: 0.95

> Lưu ý: `determinism_signature` trong file là fingerprint để so sánh tính ổn định giữa các lần chạy cùng cấu hình.
