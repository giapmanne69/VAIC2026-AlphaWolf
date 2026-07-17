# README.md

# Main Pipeline

## Giới thiệu

Main Pipeline mô tả toàn bộ quy trình xử lý của AI Assistant, từ khi tiếp nhận dữ liệu đến khi sinh báo cáo quản trị theo đúng biểu mẫu của UBND phường.

Hệ thống được xây dựng theo hướng **AI-native**, sử dụng **LLM + RAG + Rule Engine**, không Fine-tuning mô hình.

---

# Stage 1. Data Ingestion

## Mục tiêu

Thu thập dữ liệu từ nhiều nguồn khác nhau.

## Input

- Báo cáo Word (.docx)
- Báo cáo Excel (.xlsx)
- Báo cáo PDF/PDF Scan
- Email công vụ
- Dữ liệu từ các CSDL chuyên ngành

## Xử lý

- API
- ETL
- Đồng bộ dữ liệu
- Thu thập tài liệu

## Output

- Raw Documents

---

# Stage 2. Data Extraction

## Mục tiêu

Chuyển tài liệu thành dữ liệu có cấu trúc.

## Input

- Raw Documents

## Xử lý

- OCR (PDF Scan)
- Word Parser
- Excel Parser
- PDF Parser
- Email Parser

## Output

- Structured Data
- Metadata

---

# Stage 3. Data Standardization & Integration

## Mục tiêu

Chuẩn hóa và hợp nhất dữ liệu trước khi phân tích.

## Input

- Structured Data
- Master Data
- Business Rules

## Xử lý

- Chuẩn hóa tên đơn vị
- Chuẩn hóa mã địa bàn
- Chuẩn hóa đơn vị tính
- Chuẩn hóa định dạng thời gian
- Loại bỏ dữ liệu trùng lặp
- Hợp nhất dữ liệu từ nhiều nguồn
- Kiểm tra tính hợp lệ

## Output

- Unified Dataset

---

# Stage 4. KPI & Statistics Generation

## Mục tiêu

Tổng hợp các chỉ tiêu và thống kê phục vụ sinh báo cáo.

## Input

- Unified Dataset

## Xử lý

- Tổng hợp chỉ tiêu theo từng lĩnh vực
- Tính toán KPI và các tỷ lệ
- So sánh với kỳ trước hoặc kế hoạch
- Phát hiện số liệu bất thường
- Sinh bảng thống kê tổng hợp

## Output

- KPI Dataset
- Statistical Summary

---

# Stage 5. Knowledge Retrieval (RAG)

## Mục tiêu

Truy xuất các tài liệu nghiệp vụ cần thiết để AI sinh báo cáo đúng quy định.

## Input

- KPI Dataset
- Statistical Summary
- Metadata báo cáo

## Xử lý

- Truy vấn Vector Database
- Truy xuất:
  - Luật
  - Nghị định
  - Thông tư
  - Quy trình nghiệp vụ
  - Biểu mẫu báo cáo
  - Hướng dẫn lập báo cáo

## Output

- Retrieved Context

---

# Stage 6. Report Generation

## Mục tiêu

Sinh báo cáo theo đúng biểu mẫu của cơ quan nhà nước.

## Input

- KPI Dataset
- Statistical Summary
- Retrieved Context
- Template báo cáo

## Xử lý

- LLM tổng hợp số liệu
- Viết phần nhận xét
- Viết phần đánh giá
- Điền nội dung vào đúng biểu mẫu

## Output

- Draft Report

---

# Stage 7. AI Validation

## Mục tiêu

Kiểm tra chất lượng báo cáo trước khi xuất.

## Input

- Draft Report
- Business Rules

## Xử lý

- Kiểm tra logic số liệu
- Kiểm tra tính nhất quán
- Kiểm tra dữ liệu thiếu
- Kiểm tra đúng biểu mẫu
- Kiểm tra tuân thủ quy định

## Output

- Validated Report

---

# Stage 8. Export

## Mục tiêu

Xuất báo cáo và kết quả phục vụ lãnh đạo.

## Input

- Validated Report

## Output

- Báo cáo Word (.docx)
- Báo cáo PDF
- Dashboard tổng hợp
- Bộ dữ liệu lưu trữ phục vụ tra cứu

---

# Tổng quan Pipeline

```text
Data Sources
      │
      ▼
Stage 1. Data Ingestion
      │
      ▼
Stage 2. Data Extraction
      │
      ▼
Stage 3. Data Standardization & Integration
      │
      ▼
Stage 4. KPI & Statistics Generation
      │
      ▼
Stage 5. Knowledge Retrieval (RAG)
      │
      ▼
Stage 6. Report Generation (LLM)
      │
      ▼
Stage 7. AI Validation
      │
      ▼
Stage 8. Export
```

# Đầu ra của hệ thống

AI Assistant tự động:

- Tổng hợp dữ liệu từ nhiều nguồn.
- Chuẩn hóa và hợp nhất số liệu.
- Tính toán KPI và thống kê.
- Tra cứu quy định và biểu mẫu bằng RAG.
- Sinh báo cáo đúng mẫu của UBND.
- Kiểm tra chất lượng báo cáo trước khi xuất.
- Xuất báo cáo Word/PDF và Dashboard phục vụ lãnh đạo ra quyết định.