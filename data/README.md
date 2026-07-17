# README.md

# Dữ liệu sử dụng trong dự án

## Giới thiệu

Dự án xây dựng **AI Assistant hỗ trợ UBND phường tự động tổng hợp và sinh báo cáo quản trị** theo đúng biểu mẫu của cơ quan nhà nước.

Phạm vi dữ liệu của dự án tập trung vào **05 nhóm lĩnh vực chính**:

- Dân cư
- Kinh tế - tài chính
- An sinh xã hội
- Khiếu nại - tố cáo
- Chỉ tiêu thực hiện nhiệm vụ

AI sẽ tự động thu thập dữ liệu từ nhiều nguồn, chuẩn hóa, hợp nhất, đối chiếu với quy định hiện hành và sinh báo cáo đúng mẫu.

---

# 1. Dữ liệu Ingestion (Đầu vào)

## Dữ liệu sử dụng

### 1.1. Dân cư

- Báo cáo dân số
- Tạm trú, tạm vắng
- Khai sinh
- Khai tử
- Biến động dân cư

### 1.2. Kinh tế - tài chính

- Thu ngân sách
- Chi ngân sách
- Thuế, phí
- Báo cáo tài chính định kỳ

### 1.3. An sinh xã hội

- Hộ nghèo
- Hộ cận nghèo
- Đối tượng bảo trợ xã hội
- Danh sách trợ cấp

### 1.4. Khiếu nại - tố cáo

- Hồ sơ tiếp nhận
- Hồ sơ đã giải quyết
- Hồ sơ tồn đọng
- Kết quả xử lý

### 1.5. Chỉ tiêu thực hiện nhiệm vụ

- Hồ sơ hành chính
- Tỷ lệ giải quyết đúng hạn
- KPI của các phòng ban
- Tiến độ các chương trình

### Định dạng dữ liệu

- Word (.docx)
- Excel (.xlsx)
- PDF
- PDF Scan
- Email công vụ
- CSDL chuyên ngành

### Nguồn dữ liệu

- Hệ thống quản lý văn bản
- Hệ thống Một cửa
- Các cơ sở dữ liệu chuyên ngành
- Báo cáo từ các phòng, ban
- Email công vụ

### Cách thu thập

- API
- ETL
- Parser Word/Excel/PDF
- OCR cho tài liệu scan
- Đồng bộ định kỳ

---

# 2. Dữ liệu Chuẩn hóa & Hợp nhất

## Mục đích

Chuẩn hóa toàn bộ dữ liệu trước khi AI tổng hợp báo cáo.

## Dữ liệu sử dụng

### Master Data

- Danh mục đơn vị
- Mã địa bàn hành chính
- Danh mục phòng ban
- Danh mục lĩnh vực

### Schema

- Cấu trúc báo cáo chuẩn
- Tên trường dữ liệu
- Metadata

### Business Rules

- Quy tắc tính toán
- Quy tắc kiểm tra dữ liệu
- Quy tắc hợp nhất số liệu

## Nguồn dữ liệu

- UBND phường
- Phòng Nội vụ
- Bộ Nội vụ
- Tổng cục Thống kê
- Biểu mẫu chính thức của cơ quan cấp trên

## Cách lấy dữ liệu

- Trích xuất từ hệ thống quản lý
- Chuyển đổi biểu mẫu thành Schema
- Xây dựng Master Data
- Thiết lập Business Rules

---

# 3. Dữ liệu RAG (Knowledge Base)

## Dữ liệu sử dụng

- Luật
- Nghị định
- Thông tư
- Quy chế báo cáo
- Hướng dẫn lập báo cáo
- Biểu mẫu báo cáo
- Quy trình nghiệp vụ

## Nguồn dữ liệu

- Cổng thông tin Chính phủ
- Bộ Nội vụ
- Bộ Tài chính
- Thanh tra Chính phủ
- UBND cấp huyện/quận
- UBND cấp tỉnh

## Cách lấy dữ liệu

- Thu thập văn bản điện tử
- Chuyển sang văn bản có cấu trúc
- Chunking
- Embedding
- Lưu trong Vector Database

---

# 4. Dữ liệu Đánh giá (Evaluation)

## Dữ liệu sử dụng

- Báo cáo đã được lãnh đạo phê duyệt (Ground Truth)
- Bộ test nghiệp vụ
- Báo cáo do AI sinh
- Kết quả đánh giá của cán bộ

## Nguồn dữ liệu

- Kho lưu trữ báo cáo
- Bộ test do đơn vị nghiệp vụ xây dựng
- Log của hệ thống
- Phản hồi của người sử dụng

## Cách lấy dữ liệu

- Thu thập báo cáo đã phê duyệt
- Xây dựng bộ test theo từng lĩnh vực
- Lưu toàn bộ kết quả AI
- Thu thập phản hồi sau khi sử dụng

---

# 5. Dữ liệu Giám sát Vận hành

## Dữ liệu sử dụng

- Log hệ thống
- Thời gian sinh báo cáo
- Tỷ lệ lỗi
- Tỷ lệ chỉnh sửa sau AI
- Phản hồi của lãnh đạo
- Lịch sử các lần sinh báo cáo

## Nguồn dữ liệu

- Application Log
- Monitoring System
- Workflow phê duyệt
- Hệ thống phản hồi nội bộ

## Cách lấy dữ liệu

- Ghi log tự động
- Thu thập metrics
- Theo dõi quá trình chỉnh sửa
- Tổng hợp phản hồi định kỳ

---

# Luồng dữ liệu

```text
Các phòng, ban và CSDL chuyên ngành
                │
                ▼
        Ingestion (API/ETL/OCR)
                │
                ▼
      Chuẩn hóa & Hợp nhất dữ liệu
      (Master Data + Business Rules)
                │
                ▼
        Data Warehouse / Data Lake
                │
        ┌───────┴────────┐
        ▼                ▼
 Knowledge Base      Dữ liệu nghiệp vụ
      (RAG)                │
        └────────┬─────────┘
                 ▼
      AI Assistant (LLM + RAG + Rule Engine)
                 │
                 ▼
Tổng hợp và chuẩn hóa số liệu thuộc 5 lĩnh vực:
- Dân cư
- Kinh tế - tài chính
- An sinh xã hội
- Khiếu nại - tố cáo
- Chỉ tiêu thực hiện nhiệm vụ
                 │
                 ▼
      Sinh báo cáo đúng mẫu UBND
                 │
        ┌────────┴────────┐
        ▼                 ▼
   Evaluation        Monitoring
```

## Ghi chú

- Dự án **không Fine-tuning mô hình LLM**.
- AI sử dụng **LLM + RAG + Rule Engine** để tổng hợp dữ liệu, chuẩn hóa số liệu và sinh báo cáo.
- AI đóng vai trò trung tâm trong toàn bộ quy trình; cán bộ chủ yếu thực hiện kiểm duyệt và phê duyệt báo cáo cuối cùng.

