# AI Governance Report Assistant

## 1. Bối cảnh

Mỗi tuần và mỗi tháng, UBND phường phải tiếp nhận một lượng lớn báo cáo từ các phòng, ban và đơn vị trực thuộc. Các báo cáo này được gửi dưới nhiều định dạng khác nhau (Word, Excel, PDF, Email hoặc từ các hệ thống chuyên ngành), khiến việc tổng hợp và lập báo cáo quản trị tiêu tốn nhiều thời gian.

Quy trình hiện nay chủ yếu được thực hiện thủ công, dẫn đến nhiều hạn chế:

- Mất nhiều thời gian tổng hợp số liệu.
- Dễ xảy ra sai sót khi nhập liệu và hợp nhất dữ liệu.
- Khó đảm bảo tính nhất quán giữa các báo cáo.
- Khó khai thác dữ liệu phục vụ điều hành và ra quyết định.
- Phụ thuộc nhiều vào kinh nghiệm của cán bộ tổng hợp.

Trong bối cảnh chuyển đổi số của cơ quan nhà nước, cần một hệ thống AI có khả năng tự động hóa quy trình tổng hợp báo cáo, chuẩn hóa số liệu và hỗ trợ lãnh đạo khai thác thông tin hiệu quả hơn.

---

# 2. Bài toán

Xây dựng một tác tử **Agentic AI** có khả năng:

- Tiếp nhận dữ liệu từ nhiều nguồn khác nhau.
- Chuẩn hóa và hợp nhất dữ liệu.
- Tổng hợp các chỉ tiêu của 03 lĩnh vực:
  - Dân cư
  - Khiếu nại - tố cáo
  - Chỉ tiêu thực hiện nhiệm vụ
- Tra cứu các quy định và biểu mẫu bằng RAG.
- Tự động sinh báo cáo quản trị theo đúng biểu mẫu của cơ quan nhà nước.
- Hỗ trợ lãnh đạo theo dõi các chỉ tiêu và đưa ra quyết định.

Hệ thống được xây dựng theo hướng **AI-native**, sử dụng **LLM + RAG + Rule Engine**, không Fine-tuning mô hình.

---

# 3. Đối tượng sử dụng

### Cán bộ tổng hợp

- Thu thập dữ liệu.
- Kiểm tra báo cáo do AI sinh.
- Phê duyệt trước khi trình lãnh đạo.

### Lãnh đạo UBND

- Xem báo cáo tổng hợp.
- Theo dõi KPI.
- Theo dõi tình hình thực hiện nhiệm vụ.
- Hỗ trợ ra quyết định.

### Quản trị hệ thống

- Quản lý Knowledge Base.
- Theo dõi chất lượng AI.
- Theo dõi các chỉ số vận hành.

---

# 4. Input & Output

## Input

### Dữ liệu nghiệp vụ

- Báo cáo dân cư.
- Báo cáo khiếu nại - tố cáo.
- Báo cáo chỉ tiêu thực hiện nhiệm vụ.

### Định dạng

- Word (.docx)
- Excel (.xlsx)
- PDF
- PDF Scan
- Email công vụ
- CSDL chuyên ngành

### Dữ liệu chuẩn hóa

- Master Data
- Schema báo cáo
- Business Rules

### Knowledge Base

- Luật
- Nghị định
- Thông tư
- Quy trình nghiệp vụ
- Biểu mẫu báo cáo
- Hướng dẫn lập báo cáo

---

## Output

### Dữ liệu chuẩn hóa

- Unified Dataset

### Dữ liệu thống kê

- KPI Dataset
- Statistical Summary

### Báo cáo quản trị

- Báo cáo Word (.docx)
- Báo cáo PDF
- Dashboard tổng hợp

---

# 5. Kiến trúc Pipeline

## 5.1 Luồng Xử lý của Tác tử (Agentic Flow)

```text
[Mẫu báo cáo template.docx + Báo cáo thô của các phòng ban]
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

---

## 5.2 Evaluation Pipeline

```text
Ground Truth
+
AI Generated Report
+
Test Dataset
      │
      ▼
Evaluation
      │
      ├── Data Accuracy
      ├── Hallucination Rate
      ├── Consistency Score
      ├── Latency
      └── Human Edit Rate
      │
      ▼
Evaluation Dashboard
      │
      ▼
Improve:
- Data Pipeline
- Knowledge Base (RAG)
- Prompt
- Rule Engine
```

---

# 6. Thành phần Agentic AI (Memory, Tools, Hooks & Rules)

Để chuyển đổi từ một AI Pipeline thông thường sang **Agentic AI** (Hệ tác tử AI tự trị), hệ thống bổ sung các thành phần sau:

## 6.1. Memory (Bộ nhớ tác tử)
Giúp tác tử lưu giữ ngữ cảnh để phản hồi tự nhiên và nhất quán:
- **Short-term Memory (Bộ nhớ ngắn hạn):** Lưu trữ toàn bộ hội thoại của phiên làm việc (session history) và các tài liệu, bảng biểu vừa được tải lên trong luồng xử lý hiện tại.
- **Long-term Memory (Bộ nhớ dài hạn):** Lưu giữ các thông tin cấu hình đặc thù của phường, thói quen viết báo cáo của cán bộ tổng hợp, và các phản hồi/chỉnh sửa của lãnh đạo từ các kỳ báo cáo trước để tự động điều chỉnh hành vi sinh văn bản trong tương lai.

## 6.2. Tools (Hộp công cụ hành động)
Cung cấp cho tác tử khả năng chủ động tương tác với hệ thống và dữ liệu thông qua các công cụ chuyên biệt:
- **Parser Tools:** Trích xuất nội dung từ các định dạng Word, Excel, PDF và OCR tài liệu quét.
- **Standardization Tools:** So khớp fuzzy tên địa bàn (với Master GSO) và phòng ban hành chính.
- **Rule Engine Tool:** Thực thi các phép tính toán logic và kiểm tra chéo số liệu dựa trên `validation_rules.json`.
- **RAG Search Tool:** Tìm kiếm ngữ cảnh luật pháp và biểu mẫu báo cáo liên quan.

## 6.3. Hooks (Bộ lọc bảo mật & Kiểm soát thông tin mật)
Cơ chế bảo mật dữ liệu nhạy cảm và thông tin mật trước khi xử lý hoặc gửi tới mô hình ngôn ngữ lớn (nhất là khi sử dụng LLM Cloud API):
- **Anonymization Hook (Mã hóa thông tin cá nhân):** Tự động phát hiện và che giấu (masking/anonymize) các thông tin định danh cá nhân (PII) như: Họ tên công dân, Số CCCD, Số điện thoại, Địa chỉ nhà chi tiết,... nhằm tuân thủ **Nghị định số 13/2023/NĐ-CP** về bảo vệ dữ liệu cá nhân.
- **Redaction Hook (Kiểm soát thông tin mật):** Bộ lọc kiểm tra các từ khóa thuộc danh mục tài liệu mật (bí mật nhà nước, kế hoạch quốc phòng địa phương, ngân sách mật) để ngăn chặn rò rỉ dữ liệu ra ngoài phạm vi máy chủ nội bộ (On-premise).

## 6.4. Rules (Quy tắc tác tử)
Các quy chế và ranh giới hoạt động quy định hành vi của tác tử:
- Quy tắc kiểm tra tính hợp lệ số liệu bắt buộc (Error) và cảnh báo (Warning).
- Quy trình phê duyệt có sự tham gia của con người (Human-in-the-loop) để kiểm duyệt báo cáo trước khi ký số.

---

# 7. Công nghệ đề xuất

- **LLM:** Qwen2.5-7B-Instruct (hoặc tương đương)
- **RAG:** Vector Database + Embedding Model
- **Document Processing:** OCR + Parser (Word, Excel, PDF)
- **Rule Engine:** Chuẩn hóa dữ liệu và kiểm tra nghiệp vụ
- **Backend:** FastAPI
- **Frontend:** Streamlit hoặc React
- **Database:** PostgreSQL
- **Vector Database:** ChromaDB hoặc FAISS

---

# 8. Mục tiêu

Xây dựng một tác tử **Agentic AI** có khả năng tự động:

- Thu thập dữ liệu từ nhiều nguồn.
- Chuẩn hóa và hợp nhất số liệu.
- Tính toán các chỉ tiêu quản trị.
- Tra cứu quy định hiện hành bằng RAG.
- Sinh báo cáo đúng mẫu của UBND.
- Hỗ trợ lãnh đạo theo dõi tình hình và ra quyết định.

Con người chủ yếu thực hiện kiểm duyệt và phê duyệt báo cáo cuối cùng.