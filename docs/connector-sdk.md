# Connector SDK

Tài liệu này mô tả chuẩn để đóng góp connector mới cho Antigravity.

## 1) Connector contract

Mọi connector **phải** kế thừa `BaseConnector` và cung cấp:

- `name: str` — tên định danh duy nhất (ví dụ: `github`, `filesystem`).
- `capabilities: tuple[str, ...]` — danh sách capability để discovery trong registry.
- `invoke(input, context)` — hàm thực thi chính, trả về `Mapping[str, Any]`.

`context` dùng kiểu `ConnectorContext` gồm:

- `request_id` (bắt buộc) để trace toàn luồng.
- `actor` để audit người gọi.
- `metadata` để truyền thông tin runtime bổ sung.

### Quy ước input/output

- `input` là dict phẳng hoặc nested JSON-serializable.
- Connector **không** trả object tùy biến khó serialize.
- Output nên có các trường ổn định: `status`, `data`/`body`, metadata cần thiết.

## 2) Error model

Sử dụng `ConnectorError(code, message, details)` thay vì throw lỗi thô từ thư viện nền.

Mã lỗi gợi ý:

- `INVALID_INPUT` — thiếu/sai tham số đầu vào.
- `NOT_FOUND` — tài nguyên không tồn tại.
- `ACCESS_DENIED` — vi phạm quyền truy cập.
- `READ_ONLY` — thao tác ghi bị chặn bởi chế độ readonly.
- `HTTP_ERROR` — upstream trả lỗi HTTP.
- `NETWORK_ERROR` — lỗi kết nối/tên miền/timeout.

Nguyên tắc:

1. `message` dễ hiểu cho người vận hành.
2. `details` chứa dữ liệu có thể debug (status code, url, path, ...).
3. Không để lộ secrets trong `details`.

## 3) Registry integration

Đăng ký connector trong `ConnectorRegistry` với version rõ ràng:

```python
registry.register(MyConnector(), version="v1")
```

Khi breaking change:

- Tạo version mới (`v2`) thay vì ghi đè version cũ.
- Duy trì song song để workflow cũ không gãy.

## 4) Test contract checklist

Mỗi connector nên có test tối thiểu theo checklist sau:

- [ ] Có thể khởi tạo connector với cấu hình tối thiểu.
- [ ] `invoke` thành công với input hợp lệ (happy path).
- [ ] Trả `ConnectorError(INVALID_INPUT, ...)` khi thiếu trường bắt buộc.
- [ ] Mapping lỗi external sang `ConnectorError` đúng code.
- [ ] Không vi phạm boundary bảo mật (ví dụ path traversal).
- [ ] Đăng ký/lookup được qua `ConnectorRegistry`.
- [ ] Discovery theo capability trả đúng connector + version.

## 5) Contribution flow

1. Tạo file `connectors/<your_connector>.py`.
2. Triển khai interface + validation + error mapping.
3. Cập nhật ví dụ workflow nếu connector dùng cho use case mới.
4. Bổ sung test theo checklist ở trên.
5. Mở PR kèm mô tả capability, hạn chế và cấu hình cần thiết.
