# AI Collaboration Log (Antigravity)

Tài liệu này ghi nhận quá trình tương tác và lập trình đồng hành (Pair Programming) giữa đội ngũ phát triển và Trợ lý lập trình AI **Antigravity** trong khuôn khổ cuộc thi **Vietnam AI Innovation Challenge**.

## 1. Thông tin phiên làm việc (Session Info)
* **AI Tool:** Antigravity AI Coding Assistant
* **Session ID:** `db3e35ac-a11d-46a5-8c0a-a33cb5450688`
* **Raw Log File:** [transcript.jsonl](file:///e:/Project/VAIC_Project/.gemini/sessions/transcript.jsonl) (File nhật ký thô).
* **Protobuf Session File:** [db3e35ac-a11d-46a5-8c0a-a33cb5450688.pb](file:///e:/Project/VAIC_Project/.gemini/sessions/db3e35ac-a11d-46a5-8c0a-a33cb5450688.pb) (Tệp lưu trữ phiên làm việc thực tế dưới dạng Protocol Buffers được ghi nhận trực tiếp từ IDE).

---

## 2. Các công việc và cột mốc đã hoàn thành trong Session

### Mốc 1: Phân tích dữ liệu gốc & Xác định cấu trúc
* Đọc và phân tích file Excel dữ liệu hành chính GSO để kiểm tra cấu trúc dữ liệu cấp tỉnh và cấp xã.
* Cài đặt thành công các thư viện bổ trợ (`xlrd`) để phục vụ kiểm tra tệp Excel phiên bản cũ.

### Mốc 2: Tinh chỉnh phạm vi dự án (Scope Down)
* Rút gọn phạm vi dự án từ 5 lĩnh vực xuống **3 lĩnh vực cốt lõi** phù hợp với thực tế dữ liệu cấp phường:
  1. **Dân cư** (Biến động dân số, khai sinh, khai tử, tạm trú, tạm vắng).
  2. **Khiếu nại - Tố cáo** (Tiếp dân, phân loại đơn thư, trạng thái giải quyết).
  3. **Chỉ tiêu thực hiện nhiệm vụ** (Hồ sơ thủ tục hành chính một cửa, KPI, tỷ lệ đúng hạn).
* Cập nhật toàn bộ tài liệu kiến trúc tại [README.md](file:///e:/Project/VAIC_Project/README.md) và [data/README.md](file:///e:/Project/VAIC_Project/data/README.md) khớp với phạm vi mới.

### Mốc 3: Thiết lập Schema chuẩn hóa và Quy tắc nghiệp vụ (Master Data & Rules)
* Tạo danh mục phòng ban chuẩn hóa tại [data/chuan_hoa_hop_nhat/dm_phong_ban/phong_ban.csv](file:///e:/Project/VAIC_Project/data/chuan_hoa_hop_nhat/dm_phong_ban/phong_ban.csv).
* Xây dựng đặc tả cấu trúc chỉ tiêu chi tiết tại [data/chuan_hoa_hop_nhat/report_schema.json](file:///e:/Project/VAIC_Project/data/chuan_hoa_hop_nhat/report_schema.json) (gồm mô tả và các từ khóa đồng nghĩa để so khớp tự động).
* Thiết lập bộ quy tắc kiểm tra chéo toán học và logic số liệu tại [data/chuan_hoa_hop_nhat/validation_rules.json](file:///e:/Project/VAIC_Project/data/chuan_hoa_hop_nhat/validation_rules.json).

### Mốc 4: Tư vấn kiến trúc Data Pipeline & RAG
* Thống nhất mô hình trích xuất mềm dẻo bằng LLM (LLM-based Extraction) kết hợp Pydantic Schema.
* Tư vấn giải pháp sinh biểu mẫu kết hợp (Hybrid Template Engine) bằng `docxtpl` để giữ nguyên font/khung bảng biểu chuẩn hành chính nhà nước của UBND (Nghị định 30/2020/NĐ-CP).

---

Hệ thống ghi nhận phiên làm việc dưới dạng tệp tin nhị phân Protocol Buffers [db3e35ac-a11d-46a5-8c0a-a33cb5450688.pb](file:///e:/Project/VAIC_Project/.gemini/sessions/db3e35ac-a11d-46a5-8c0a-a33cb5450688.pb). Nếu có tệp nhật ký thô [transcript.jsonl](file:///e:/Project/VAIC_Project/.gemini/sessions/transcript.jsonl), nó ghi nhận dưới định dạng JSON Lines với cấu trúc mỗi dòng bao gồm:
* `source`: Người dùng (`USER_EXPLICIT`) hoặc AI (`MODEL`).
* `tool_calls`: Các cuộc gọi công cụ (đọc file, chạy terminal lệnh).
* `content`: Nội dung hội thoại trao đổi.
