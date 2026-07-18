# README.md

# Main Pipeline

## Giới thiệu

Main Pipeline mô tả toàn bộ quy trình xử lý của tác tử **Agentic AI**, từ khi tiếp nhận dữ liệu đến khi sinh báo cáo quản trị theo đúng biểu mẫu của UBND phường.

Hệ thống được xây dựng theo hướng **AI-native**, sử dụng **LLM + RAG + Rule Engine**, không Fine-tuning mô hình.

---

# Stage 1. Data Ingestion & Security Hook

## Mục tiêu

Tiếp nhận tệp biểu mẫu cùng tài liệu đầu vào, và tiến hành bảo mật hóa dữ liệu trước khi xử lý.

## Input

- **Mẫu báo cáo trống** do cán bộ tải lên (`template.docx`).
- Các file báo cáo thô của các phòng ban gửi về (`inputs/` dưới dạng Word, Excel, PDF).

## Xử lý (Agentic Mechanism)

- Tác tử tiếp nhận cả tệp biểu mẫu trống và các báo cáo thô.
- Tự động chạy **Anonymization Hook** trên các tệp báo cáo thô:
  - Dùng Regex/NER phát hiện và che giấu/mã hóa (masking) thông tin cá nhân (PII) như Họ tên công dân, Số điện thoại, CCCD,... theo đúng Nghị định 13/2023/NĐ-CP.
  - Lọc và phát hiện thông tin thuộc danh mục mật bằng **Redaction Hook**.

## Output

- Mẫu báo cáo trống (`template.docx`)
- Anonymized Raw Documents (Báo cáo thô đã được bảo mật hóa)

---

# Stage 2. Template Parsing & Data Extraction (Parser Tools)

## Mục tiêu

Phân tích biểu mẫu để xác định các trường cần điền, sau đó trích xuất đích danh các số liệu từ tài liệu thô.

## Input

- Mẫu báo cáo trống (`template.docx`)
- Anonymized Raw Documents

## Xử lý (Agentic Mechanism)

1. **Phân tích Biểu mẫu (Template Parsing):** Tác tử quét qua cấu trúc tệp `template.docx` để tìm tất cả các thẻ tag đặt sẵn (dạng `{{tong_dan_so}}`, `{{ty_le_dung_han}}`) hoặc các ô trống trong bảng biểu. Tác tử tự động biên dịch chúng thành một **Dynamic Schema (Danh sách các trường số liệu cần tìm)**.
2. **Trích xuất có định hướng (Targeted Extraction):** Tác tử sử dụng Dynamic Schema vừa tạo để làm mục tiêu trích xuất. Tác tử gọi các công cụ tương ứng (**Excel Parser**, **Word/PDF Parser**, hoặc **OCR Tool**) để chỉ quét và lấy đúng các con số/thông tin cần thiết từ báo cáo thô, bỏ qua thông tin thừa để tiết kiệm token và tránh nhiễu.

## Output

- Dynamic Schema (Danh sách trường cần điền)
- Raw JSON Dataset (Chứa đúng các biến trong Schema)
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

## Xử lý (Agentic Mechanism - Pipeline 2)

Đây là quy trình khi Tác tử kích hoạt **RAG Search Tool** để tra cứu tri thức giải trình báo cáo:

```text
Người dùng đưa yêu cầu (hoặc Agent tự nhận thức)
                     │
                     ▼
            Agent phân tích nhiệm vụ
                     │
                     ▼
       Agent xác định có cần RAG không
                     │
                     ▼
          Tạo câu truy vấn cho RAG
                     │
                     ▼
             Lọc theo Metadata
                     │
                     ▼
               Hybrid Search
                     │
                     ▼
           Lấy các chunk phù hợp
                     │
                     ▼
                 Reranking
                     │
                     ▼
           Chọn các đoạn tốt nhất
                     │
                     ▼
               Ghép thành Context
                     │
                     ▼
              Đưa Context cho LLM
                     │
                     ▼
        LLM viết câu trả lời / báo cáo
                     │
                     ▼
         Kiểm tra nguồn và trích dẫn
                     │
                     ▼
            Trả kết quả cho Agent
```

Chi tiết luồng thực thi:
1. **Lập luận gọi RAG:** Tác tử phân tích chỉ số KPI nhận được. Nếu phát hiện chỉ số bất thường hoặc theo yêu cầu viết báo cáo chuyên đề của cán bộ, Tác tử quyết định kích hoạt công cụ `RAG Search Tool`.
2. **Xây dựng Query & Lọc:** Tác tử tự dịch nhu cầu phân tích thành câu truy vấn nghiệp vụ tối ưu và áp dụng bộ lọc Metadata (ví dụ: chỉ tìm trong `Luật Khiếu nại` đối với lỗi liên quan đến Đơn thư).
3. **Tìm kiếm & Rerank:** Tìm kiếm kết hợp (Hybrid Search: Vector Search + Keyword Search). Sau đó sử dụng mô hình Reranker (`bge-reranker-v2-m3`) để xếp hạng lại, lấy ra top các đoạn văn bản luật chất lượng nhất.
4. **Đổ ngữ cảnh cho LLM:** Gắn thông tin luật và các nguồn trích dẫn tương ứng vào Context để LLM tham chiếu viết phần nhận xét, đảm bảo tính pháp lý tuyệt đối cho văn bản hành chính công.

## Output

- Legal Context (Ngữ cảnh pháp lý được trích dẫn chính xác nguồn)

---

# Stage 6. Report Generation (Memory & Template Injection)

## Mục tiêu

Sinh dự thảo báo cáo hành chính hoàn chỉnh trực tiếp trên tệp biểu mẫu đã tải lên.

## Input

- Unified KPI Dataset
- Legal Context
- Mẫu báo cáo trống (`template.docx` từ Stage 1)

## Xử lý (Agentic Mechanism)

- Tác tử nạp **Short-term Memory** (ngữ cảnh cuộc đối thoại) và **Long-term Memory** (thói quen, phong cách viết báo cáo của cán bộ phường trong quá khứ).
- Tác tử viết các đoạn văn bản nhận xét/đánh giá dựa trên RAG luật pháp và đưa vào bộ nhớ.
- Tác tử gọi công cụ **Docx Template Engine (`docxtpl`)** để điền trực tiếp dữ liệu số từ `Unified KPI Dataset` và các đoạn văn nhận xét vào đúng các tag placeholder trên tệp **`template.docx` gốc**, đảm bảo giữ nguyên 100% định dạng lề, bảng biểu và font chữ của UBND phường.

## Output

- Draft Word Report (.docx) (Bản Word đầy đủ nội dung)

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
    [Mẫu báo cáo trống template.docx + Báo cáo thô]
                           │
                           ▼
     Stage 1. Ingestion & Security Hook (PII Masking)
                           │
                           ▼
     Stage 2. Template Parsing (Dynamic Schema) & Extraction
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
     Stage 6. Report Generation (Memory + docxtpl Injection)
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