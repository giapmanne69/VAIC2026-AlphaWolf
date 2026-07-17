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

Xây dựng một **AI Assistant** có khả năng:

- Tiếp nhận dữ liệu từ nhiều nguồn khác nhau.
- Chuẩn hóa và hợp nhất dữ liệu.
- Tổng hợp các chỉ tiêu của 05 lĩnh vực:
  - Dân cư
  - Kinh tế - tài chính
  - An sinh xã hội
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
- Báo cáo kinh tế - tài chính.
- Báo cáo an sinh xã hội.
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

## 5.1 Data Pipeline

```text
Data Sources
      │
      ▼
Ingestion
(API / ETL / OCR)
      │
      ▼
Data Extraction
      │
      ▼
Data Standardization
      │
      ▼
Data Integration
      │
      ▼
Unified Dataset
```

---

## 5.2 Main Pipeline

```text
Unified Dataset
      │
      ▼
KPI & Statistics Generation
      │
      ▼
Knowledge Retrieval (RAG)
      │
      ▼
Report Generation (LLM)
      │
      ▼
AI Validation
      │
      ▼
Export Report
      │
      ▼
Word / PDF / Dashboard
```

---

## 5.3 Evaluation Pipeline

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

# Công nghệ đề xuất

- **LLM:** Qwen2.5-7B-Instruct (hoặc tương đương)
- **RAG:** Vector Database + Embedding Model
- **Document Processing:** OCR + Parser (Word, Excel, PDF)
- **Rule Engine:** Chuẩn hóa dữ liệu và kiểm tra nghiệp vụ
- **Backend:** FastAPI
- **Frontend:** Streamlit hoặc React
- **Database:** PostgreSQL
- **Vector Database:** ChromaDB hoặc FAISS

---

# Mục tiêu

Xây dựng một AI Assistant có khả năng tự động:

- Thu thập dữ liệu từ nhiều nguồn.
- Chuẩn hóa và hợp nhất số liệu.
- Tính toán các chỉ tiêu quản trị.
- Tra cứu quy định hiện hành.
- Sinh báo cáo đúng mẫu của UBND.
- Hỗ trợ lãnh đạo theo dõi tình hình và ra quyết định.

Con người chủ yếu thực hiện kiểm duyệt và phê duyệt báo cáo cuối cùng.