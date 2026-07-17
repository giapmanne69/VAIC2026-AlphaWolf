# README.md

# Main Pipeline

## Giới thiệu

Main Pipeline mô tả toàn bộ quy trình xử lý của tác tử **Agentic AI**, từ khi tiếp nhận dữ liệu đến khi sinh báo cáo quản trị theo đúng biểu mẫu của UBND phường.

Hệ thống được xây dựng theo hướng **AI-native**, sử dụng **LLM + RAG + Rule Engine**, không Fine-tuning mô hình.

---

# Stage 1. Data Ingestion & Security Hook

## Mục tiêu

Tiếp nhận và bảo mật hóa toàn bộ tài liệu đầu vào trước khi xử lý.

## Input

- Báo cáo của các bộ phận chuyên môn gửi lên (Tư pháp, Công an, Một cửa...) dưới dạng Word, Excel, PDF.

## Xử lý (Agentic Mechanism)

- Tác tử tiếp nhận tài liệu và tự động chạy **Anonymization Hook**:
  - Dùng Regex/NER phát hiện và che giấu/mã hóa (masking) thông tin cá nhân (PII) như Họ tên công dân, Số điện thoại, CCCD,... theo đúng Nghị định 13/2023/NĐ-CP.
  - Lọc và phát hiện thông tin thuộc danh mục mật bằng **Redaction Hook**.

## Output

- Anonymized Raw Documents (Tài liệu thô đã được bảo mật hóa)

---

# Stage 2. Data Extraction (Parser Tools)

## Mục tiêu

Chuyển đổi dữ liệu phi cấu trúc từ các tệp thô thành dữ liệu có cấu trúc.

## Input

- Anonymized Raw Documents

## Xử lý (Agentic Mechanism)

- Tác tử phân tích định dạng tệp và tự động gọi các công cụ trích xuất tương ứng:
  - Gọi **Excel Parser Tool** để đọc bảng biểu.
  - Gọi **Word/PDF Parser Tool** để trích xuất văn bản thô.
  - Gọi **OCR Tool** đối với các báo cáo dạng quét (PDF Scan).
- Tác tử gọi LLM trích xuất số liệu thô thông qua Pydantic schema của [report_schema.json](file:///e:/Project/VAIC_Project/data/chuan_hoa_hop_nhat/report_schema.json).

## Output

- Raw JSON Dataset
- Document Metadata

---

# Stage 3. Data Standardization (Standardization Tools)

## Mục tiêu

Chuẩn hóa các thực thể, địa bàn, và chỉ tiêu về dạng nhất quán.

## Input

- Raw JSON Dataset

## Xử lý (Agentic Mechanism)

- Tác tử gọi **Standardization Tools** để:
  - So khớp fuzzy và chuẩn hóa tên địa bàn dựa trên cơ sở dữ liệu quốc gia (`wards.csv` và `admin_units_full.json`).
  - Chuẩn hóa tên đơn vị/phòng ban gửi báo cáo bằng `phong_ban.csv`.
  - Áp dụng các từ khóa đồng nghĩa (aliases) trong `report_schema.json` để quy đổi tất cả các biến về key chuẩn.

## Output

- Standardized JSON Dataset

---

# Stage 4. KPI Generation & Self-Correction (Rule Engine)

## Mục tiêu

Tính toán các chỉ số thống kê và tự động kiểm tra chéo tính hợp lệ của số liệu.

## Input

- Standardized JSON Dataset

## Xử lý (Agentic Mechanism)

- Tác tử gọi **Rule Engine Tool** để:
  - Tính toán các chỉ tiêu phái sinh và chỉ số KPI hành chính (ví dụ: tỷ lệ đúng hạn).
  - Tự động thực thi các biểu thức kiểm tra chéo trong `validation_rules.json`.
- **Cơ chế tự sửa sai (Self-Correction Loop):** Nếu phát hiện lỗi logic số liệu (Rule Fail), tác tử tự động phản hồi (self-reflect), điều chỉnh tham số trích xuất và thực hiện lại Stage 2-3 cho đến khi số liệu hoàn toàn nhất quán (tối đa N lần).

## Output

- Unified KPI Dataset (Bộ số liệu hợp nhất hoàn toàn sạch)

---

# Stage 5. Knowledge Retrieval (RAG Search Tool)

## Mục tiêu

Truy xuất thông tin pháp lý và biểu mẫu chuẩn làm căn cứ viết báo cáo.

## Input

- Unified KPI Dataset

## Xử lý (Agentic Mechanism)

- Tác tử chủ động lập luận dựa trên kết quả số liệu:
  - Nếu số liệu bình thường: Tác tử bỏ qua hoặc hạn chế gọi RAG pháp luật để tối ưu tốc độ.
  - Nếu số liệu có biến động bất thường hoặc giảm sút KPI: Tác tử tự tạo câu truy vấn và gọi **RAG Search Tool** để tìm các điều luật, quy định xử lý từ Vector DB làm căn cứ giải trình.
  - Tác tử truy xuất mẫu cấu trúc báo cáo cần điền.

## Output

- Legal Context & Report Layout

---

# Stage 6. Report Generation (Memory & Templates)

## Mục tiêu

Sinh dự thảo báo cáo hành chính đúng mẫu của UBND.

## Input

- Unified KPI Dataset
- Legal Context & Report Layout

## Xử lý (Agentic Mechanism)

- Tác tử nạp **Short-term Memory** (ngữ cảnh cuộc đối thoại hiện tại) và **Long-term Memory** (thói quen, phong cách viết báo cáo của cán bộ phường trong quá khứ).
- Tác tử viết các đoạn văn bản nhận xét/đánh giá kết hợp căn cứ luật pháp từ RAG.
- Tác tử gọi công cụ **Docx Template Engine (`docxtpl`)** để đổ tự động các trường số liệu từ `Unified KPI Dataset` vào đúng vị trí biểu mẫu Word chuẩn, đồng thời chèn các đoạn văn nhận xét do LLM viết vào.

## Output

- Draft Word Report (.docx)

---

# Stage 7. AI Validation & Refinement

## Mục tiêu

Kiểm tra toàn diện báo cáo trước khi trình cán bộ duyệt.

## Input

- Draft Word Report (.docx)

## Xử lý (Agentic Mechanism)

- Tác tử tự đóng vai trò là "Kiểm soát viên" chạy một lượt đánh giá độc lập (Self-Validation):
  - Kiểm tra xem định dạng văn bản có tuân thủ Nghị định 30/2020/NĐ-CP (font chữ, bố cục bảng).
  - Kiểm tra xem các văn cảnh luật pháp được trích dẫn có chính xác không (tránh ảo giác trích dẫn luật).
- Nếu phát hiện lỗi, tự động chỉnh sửa và cập nhật lại file báo cáo.

## Output

- Validated Word Report (.docx)

---

# Stage 8. Human Review & Memory Update

## Mục tiêu

Trình duyệt và học hỏi từ các chỉnh sửa của con người.

## Input

- Validated Word Report (.docx)

## Xử lý (Agentic Mechanism)

- Cán bộ tổng hợp kiểm duyệt báo cáo trên giao diện web (Streamlit).
- **Cơ chế học hỏi (Learning Loop):**
  - Hệ thống ghi nhận các điểm cán bộ sửa đổi thủ công trên file nháp (Human Edit Rate - HER).
  - Các sửa đổi này được đưa vào **Long-term Memory** của Tác tử để cải thiện chất lượng viết báo cáo cho các kỳ sau.
- Xuất báo cáo chính thức (Word/PDF) và ký số.

## Output

- Official Report (.docx, .pdf)
- Long-term Memory Updated

---

# Tổng quan Pipeline Tác tử (Agentic Flow)

```text
       [Dữ liệu thô của các phòng ban]
                     │
                     ▼
  Stage 1. Ingestion & Security Hook (PII Masking)
                     │
                     ▼
  Stage 2. Data Extraction (Calling Parser Tools)
                     │
                     ▼
  Stage 3. Data Standardization (Fuzzy Match GSO)
                     │
                     ▼
  Stage 4. KPI Generation & Self-Correction (Rule Engine)  ◄──┐
                     │                                         │ (Vòng tự sửa số liệu)
                     ├── Vi phạm logic số liệu ────────────────┘
                     │
                     ▼ (Số liệu đã nhất quán)
  Stage 5. Dynamic Knowledge Retrieval (RAG Search Tool)
                     │
                     ▼
  Stage 6. Report Generation (Memory + docxtpl Engine)
                     │
                     ▼
  Stage 7. AI Self-Validation & Refinement
                     │
                     ▼
  Stage 8. Human Review & Memory Update (HER Tracking)
                     │
                     ▼
       [Báo cáo chính thức xuất bản]
```


# Đầu ra của hệ thống

Tác tử **Agentic AI** tự động:

- Tổng hợp dữ liệu từ nhiều nguồn.
- Chuẩn hóa và hợp nhất số liệu.
- Tính toán KPI và thống kê.
- Tra cứu quy định và biểu mẫu bằng RAG.
- Sinh báo cáo đúng mẫu của UBND.
- Kiểm tra chất lượng báo cáo trước khi xuất.
- Xuất báo cáo Word/PDF và Dashboard phục vụ lãnh đạo ra quyết định.