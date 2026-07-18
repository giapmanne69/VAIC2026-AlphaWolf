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
Các quy chế và ranh giới hoạt động quy định hành vi củ- Giao diện người dùng (Frontend & Backend): `React` + `Vite` + `TailwindCSS v4` (Giao diện thân thiện cán bộ trung niên) phối hợp cùng `FastAPI` Backend (Python API & Stream tư duy ReAct).

---

# 8. Hướng dẫn vận hành hệ thống (FastAPI + React)

Hệ thống được thiết kế theo mô hình tách biệt Frontend - Backend phục vụ linh hoạt cho cả môi trường phát triển (Development) và môi trường vận hành chính thức (Production).

## 8.1. Cài đặt môi trường Backend
Cài đặt các thư viện Python cần thiết:
```bash
pip install -r requirements.txt
```

Khởi chạy máy chủ Backend (FastAPI):
```bash
uvicorn src.server:app --host 0.0.0.0 --port 8000
```
*API Swagger Docs sẽ được tự động kích hoạt tại địa chỉ: [http://localhost:8000/docs](http://localhost:8000/docs)*

---

## 8.2. Vận hành Frontend (React + Vite)

### Chế độ phát triển (Development Mode)
Khi cần phát triển, sửa đổi mã nguồn React, chạy dev server với tính năng HMR (Hot Module Replacement):
```bash
cd frontend
npm install
npm run dev
```
*Giao diện Dev sẽ mở tại địa chỉ: [http://localhost:5173/](http://localhost:5173/). Mọi yêu cầu gọi `/api/*` sẽ được tự động proxy sang cổng `8000` của Backend.*

### Chế độ vận hành chính thức (Production Mode)
Để đóng gói gọn nhẹ và phân phối trực tiếp thông qua FastAPI mà không cần chạy máy chủ node độc lập:
1. Biên dịch dự án React:
   ```bash
   cd frontend
   npm run build
   ```
   *Kết quả biên dịch sẽ nằm trong thư mục `frontend/dist`.*
2. Đồng bộ tệp tĩnh vào Backend (FastAPI sẽ phục vụ thư mục này):
   * Sao chép tất cả nội dung trong thư mục `frontend/dist` vào `src/static`.
   * Truy cập giao diện trực tiếp tại: **[http://localhost:8000/](http://localhost:8000/)**

---

# 9. Dữ liệu & Kịch bản kiểm thử (Test Samples)

Để hỗ trợ kiểm duyệt nhanh chóng luồng làm việc tự trị của AI Agent, dự án cung cấp thư mục chứa dữ liệu mẫu tại:
📁 [data/test_samples/](file:///e:/Project/VAIC_Project/data/test_samples)

Bộ dữ liệu mẫu bao gồm:
1. **Biểu mẫu đầu ra trống**: [1_bieu_mau_chuan.docx](file:///e:/Project/VAIC_Project/data/test_samples/1_bieu_mau_chuan.docx) (chứa các thẻ Jinja của chỉ tiêu kinh tế, hộ tịch, an ninh và ô nhận xét AI).
2. **Số liệu tài chính**: [2_bao_cao_kinh_te.xlsx](file:///e:/Project/VAIC_Project/data/test_samples/2_bao_cao_kinh_te.xlsx) (Excel chứa tổng thu chi ngân sách).
3. **Số liệu hộ tịch**: [3_bao_cao_tu_phap.docx](file:///e:/Project/VAIC_Project/data/test_samples/3_bao_cao_tu_phap.docx) (báo cáo Word ghi nhận đăng ký khai sinh, khai tử, chứng thực).
4. **Số liệu an ninh**: [4_bao_cao_an_ninh.docx](file:///e:/Project/VAIC_Project/data/test_samples/4_bao_cao_an_ninh.docx) (báo cáo Word về tình hình an ninh trật tự, tạm trú).

### Kịch bản chạy thử:
* **Bước 1**: Truy cập `http://localhost:8000/`, nạp file biểu mẫu số 1 và 3 file báo cáo số 2, 3, 4.
* **Bước 2**: Nhấp **Khởi chạy Tác tử AI**, quan sát logs ReAct AI phân tích và kiểm lỗi chéo.
* **Bước 3**: Chỉnh sửa thử số liệu/nhận xét trên UI và nhấn **Tải báo cáo Word** để xuất bản chính thức.

---

# 10. Cấu trúc thư mục dự án

```text
VAIC_Project/
│
├── .gemini/                    # Lưu trữ phiên làm việc của trợ lý lập trình
│   ├── sessions/
│   │   ├── db3e35ac-a11d-46a5-8c0a-a33cb5450688.pb  # File session của trợ lý
│   │   └── transcript.jsonl
│   └── README.md
│
├── config/                     # Cấu hình hệ thống & Lời nhắc
│   ├── prompts/                # Prompt Registry (YAML/JSON)
│   │   ├── template_parser.yaml   # Prompt đọc biểu mẫu để sinh Schema động
│   │   ├── raw_extractor.yaml     # Prompt trích xuất dữ liệu có định hướng
│   │   └── report_commenter.yaml  # Prompt viết văn cảnh nhận định dựa trên RAG
│   └── settings.py             # Cấu hình API key, Model endpoint, Thư mục chứa
│
├── data/                       # Dữ liệu của hệ thống
│   ├── chuan_hoa_hop_nhat/     # Master Data cấu hình quy chế
│   │   ├── dm_don_vi/          # Danh mục hành chính GSO (.csv)
│   │   ├── dm_phong_ban/       # Danh mục ID phòng ban phường (.csv)
│   │   ├── report_schema.json  # Định nghĩa trường số liệu & từ đồng nghĩa
│   │   └── validation_rules.json  # Biểu thức kiểm tra chéo số liệu
│   ├── rag/                    # Cơ sở tri thức pháp luật phục vụ tra cứu
│   │   ├── legal_docs/         # Luật, Nghị định, Thông tư dạng PDF/Word thô
│   │   └── vector_db/          # Lưu trữ database vector (ChromaDB / FAISS)
│   ├── templates/              # Thư mục lưu trữ biểu mẫu báo cáo trống đầu ra mẫu
│   ├── raw_inputs/             # Các tệp báo cáo thô đầu vào phục vụ chạy thử
│   ├── test_samples/           # [NEW] Thư mục chứa bộ dữ liệu mẫu dùng để chạy thử UI
│   └── README.md
│
├── src/                        # Mã nguồn cốt lõi (Core Code của Agent)
│   ├── __init__.py
│   ├── agent.py                # Lớp Agent điều phối chính (ReAct Loop & Tool Registry)
│   ├── server.py               # FastAPI Backend (RESTful APIs & SSE Event Stream)
│   ├── static/                 # Thư mục chứa tài nguyên React đã được biên dịch để phục vụ static
│   ├── hooks/                  # Các Hook bảo mật biên (Security Guardrails)
│   │   ├── anonymizer.py       # Hook ẩn danh PII (CCC/SĐT/Tên công dân)
│   │   └── redaction.py        # Hook kiểm soát tài liệu thuộc danh mục Mật
│   ├── tools/                  # Hộp công cụ hành động của Agent
│   │   ├── doc_parser.py       # Excel/Word Parser, OCR đọc tài liệu thô
│   │   ├── standardizer.py     # Fuzzy match chuẩn hóa địa bàn/phòng ban
│   │   ├── rule_engine.py      # Bộ kiểm tra tính toán & logic số liệu
│   │   └── rag_search.py       # Công cụ tìm kiếm Vector DB tri thức pháp luật
│   └── memory/                 # Quản lý bộ nhớ tác tử
│       ├── short_term.py       # Bộ nhớ ngữ cảnh phiên làm việc hiện tại
│       └── long_term.py        # Bộ nhớ thói quen viết & các phản hồi cũ của cán bộ
│
├── app/                        # Giao diện người dùng Streamlit (Legacy/Tương thích ngược)
│   ├── app.py                  # Dashboard ứng dụng web Streamlit
│   └── assets/                 # Custom CSS, Logo giao diện
│
├── frontend/                   # [NEW] Thư mục mã nguồn React (Vite + TailwindCSS + Lucide Icons)
│   ├── src/                    # Mã nguồn React components & pages
│   ├── package.json            # Cấu hình dependencies frontend
│   └── vite.config.js          # Cấu hình Vite & API Proxy
│
├── evaluation/                 # Bộ kiểm thử tự động của hệ thống
│   ├── test_dataset/           # Ca kiểm thử (Dữ liệu thô + Báo cáo Ground Truth chuẩn)
│   ├── run_eval.py             # Script tự động chạy tính điểm Accuracy, HER, Latency
│   └── README.md
│
├── requirements.txt            # Danh sách thư viện Python cần cài đặt
├── .gitignore                  # Cấu hình bỏ qua tệp của Git (đã cho phép tracking session)
└── README.md                   # Tài liệu tổng quan bối cảnh, kiến trúc
```

