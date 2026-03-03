# Incident triage example

Workflow mẫu này dùng **2 connectors**:

1. `filesystem` đọc dữ liệu incident từ local file.
2. `github` đọc metadata issue liên kết để enrich triage summary.

## Run

```bash
python examples/incident_triage/workflow.py
```

Kết quả:

- In summary JSON ra stdout.
- Ghi `triage_summary.json` trong cùng thư mục example.

> Ghi chú: workflow gọi GitHub API public ở chế độ read-only mặc định.
