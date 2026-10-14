# Hermes Codex Search

[English](README.md) | Tiếng Việt | [简体中文](README.zh-CN.md)

> Bản dịch này có thể chậm hơn bản tiếng Anh. Khi có khác biệt, [README.md](README.md) là bản chuẩn.

Một backend Hermes Agent chỉ dành cho tìm kiếm, dùng với một endpoint tìm kiếm web độc lập tương thích Codex.

## Đây là plugin backend cho `web_search`

Repository này **không** thêm tool `codex_web`. Nó đăng ký một provider tên
`codex` cho tool `web_search` sẵn có của Hermes:

```text
Hermes web_search -> provider: codex -> /v1/alpha/search
```

Dùng plugin này khi bạn muốn các lời gọi `web_search` thông thường của Hermes đi
qua endpoint tìm kiếm tương thích Codex mà vẫn giữ nguyên dạng tool tìm kiếm của
Hermes. Plugin không cung cấp `open`, `find`, `click`, chụp màn hình PDF hay trích
xuất nội dung trang.

Với các lệnh nâng cao kiểu Codex đó, hãy dùng
[Hermes Codex Web](https://github.com/duu261/hermes-codex-web). Đó là một plugin
tool độc lập riêng và đăng ký `codex_web`; nó không phải backend tìm kiếm.

## Plugin làm gì

Hermes giữ nguyên mô hình chính và gọi tool `web_search` như bình thường. Plugin này gửi truy vấn tới `/v1/alpha/search`, rồi trả kết quả tìm kiếm có cấu trúc về cho chính mô hình Hermes đó. Plugin không tự tạo câu trả lời và không trích xuất nội dung trang.

Endpoint yêu cầu trường `model`. Mặc định là `gpt-5.6-sol`; ghi đè bằng `CODEX_SEARCH_MODEL` khi gateway dùng một mô hình tương thích khác. Trường này định danh request tìm kiếm để định tuyến và tính phí. Nó không khởi chạy thêm một lượt sinh câu trả lời của mô hình.

## Cài đặt

Cài repository dưới dạng plugin Hermes, bật nó, rồi khởi động lại bề mặt Hermes sẽ dùng nó:

```bash
hermes plugins install <repository-url> --enable
```

Đặt endpoint và credential trong file môi trường riêng tư của Hermes:

```text
CODEX_SEARCH_BASE_URL=https://gateway.example/v1
CODEX_SEARCH_API_KEY=replace-me
# Optional:
CODEX_SEARCH_MODEL=gpt-5.6-sol
```

Base URL phải có `/v1`; plugin nối thêm `/alpha/search`. Không bao giờ commit credential.

Endpoint từ xa phải dùng HTTPS. HTTP không mã hóa chỉ được chấp nhận cho phát triển cục
bộ trên `localhost`, `127.0.0.1` hoặc `::1`. Adapter từ chối credential nhúng trong
URL, từ chối redirect, giới hạn kích thước body response, và bỏ các dòng kết quả
không có URL HTTP(S) hợp lệ.

## Chọn backend tìm kiếm mà không đổi backend trích xuất

Đặt backend theo từng khả năng:

```yaml
web:
  search_backend: codex
  extract_backend: firecrawl
```

Hoặc dùng phần cài đặt Web Search của Hermes và chọn **Use for Search** cho provider này. Chọn **Use for Extract** riêng cho một provider trích xuất.

## Phát triển

Các bài kiểm thử chỉ dùng thư viện chuẩn của Python và response HTTP giả lập:

```bash
python -m unittest discover -s tests -v
```

Plugin này dùng điểm mở rộng `WebSearchProvider` công khai của Hermes. Nó không vá lõi Hermes và không thay thế tool `web_search` có sẵn.
