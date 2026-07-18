# README.md

# Dữ liệu sử dụng trong dự án

## Giới thiệu

Dự án xây dựng **tác tử Agentic AI hỗ trợ UBND phường tự động tổng hợp và sinh báo cáo quản trị** theo đúng biểu mẫu của cơ quan nhà nước.

Phạm vi dữ liệu của dự án tập trung vào **03 nhóm lĩnh vực chính**:

- Dân cư
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

### 1.2. Khiếu nại - tố cáo

- Hồ sơ tiếp nhận
- Hồ sơ đã giải quyết
- Hồ sơ tồn đọng
- Kết quả xử lý

### 1.3. Chỉ tiêu thực hiện nhiệm vụ

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

Do hệ thống tập trung vào 03 lĩnh vực chính, dữ liệu RAG được tinh giản để chú trọng cao nhất vào các **biểu mẫu báo cáo chuẩn (Report Templates)**, quy định cấu trúc và hướng dẫn điền báo cáo:
- Biểu mẫu báo cáo hành chính chuẩn (đặc biệt là khung báo cáo tuần/tháng/quý/năm của UBND)
- Các văn bản quy định về chế độ báo cáo (Nghị định 09/2019/NĐ-CP, Thông tư 01/2020/TT-VPCP, Thông tư 02/2021/TT-TTCP, Thông tư 04/2020/TT-BTP)
- Quy chế báo cáo, hướng dẫn lập báo cáo và quy trình nghiệp vụ tương ứng với 03 lĩnh vực (Dân cư, Khiếu nại - Tố cáo, Chỉ tiêu nhiệm vụ)

## Nguồn dữ liệu

- Cổng thông tin điện tử Chính phủ (chinhphu.vn)
- Cơ sở dữ liệu quốc gia về văn bản quy phạm pháp luật (vbpl.vn)
- Bộ Tư pháp, Thanh tra Chính phủ, Bộ Nội vụ
- UBND cấp Huyện/Quận chủ quản
- UBND cấp Tỉnh/Thành phố

## Cách lấy dữ liệu & Tiền xử lý (Pipeline 1)

Quy trình tiền xử lý và xây dựng hệ cơ sở tri thức (Knowledge Base) phục vụ RAG:

```text
Tài liệu Knowledge Base
        │
        ▼
Phân loại tài liệu
        │
        ▼
  Parser / OCR
        │
        ▼
Làm sạch nội dung
        │
        ▼
Phân tích cấu trúc tài liệu
        │
        ▼
Chia thành các đoạn nhỏ
   (Chunking)
        │
        ▼
  Gắn Metadata
        │
        ▼
  Tạo Embedding
        │
        ▼
Lưu vào Vector Database
        │
        ▼
Tạo chỉ mục tìm kiếm
        │
        ▼
Knowledge Base sẵn sàng
```

Các bước thực hiện chính:
- **Thu thập:** Gom các văn bản quy định hành chính, thông tư, nghị định và hướng dẫn của 03 lĩnh vực (Dân cư, Khiếu nại, KPI).
- **Trích xuất (Parser/OCR):** Sử dụng các thư viện chuyển đổi văn bản hoặc công cụ OCR đối với các tài liệu quét.
- **Làm sạch & Chia nhỏ (Chunking):** Định dạng lại văn bản sạch sẽ và chia nhỏ theo cấu trúc điều/khoản để đảm bảo không bị mất ngữ nghĩa.
- **Embedding & Vector Storage:** Sử dụng mô hình nhúng (`multilingual-e5-large`) chuyển hóa văn bản thành vector và lưu trữ vào ChromaDB/FAISS kèm metadata (tên văn bản, điều luật) phục vụ tìm kiếm chính xác.

---

# 4. Dữ liệu Đánh giá (Evaluation)

## Dữ liệu sử dụng

Bộ dữ liệu đánh giá thực chất là **bộ dữ liệu gốc (báo cáo lịch sử đã được phê duyệt làm Ground Truth)** cùng với tệp dữ liệu thô tương ứng để đối sánh chất lượng đầu ra của AI:
- Các báo cáo tuần/tháng/quý/năm cũ đã được lãnh đạo phê duyệt chính thức (làm Ground Truth để so sánh)
- Các tệp dữ liệu thô (đầu vào của kỳ báo cáo lịch sử đó) dùng để nạp cho AI chạy thử nghiệm
- Điểm đánh giá mức độ sai lệch số liệu (Data Accuracy) giữa kết quả của AI và Ground Truth
- Nhật ký chỉnh sửa của cán bộ (Human Edit Rate) trên giao diện báo cáo nháp của AI

## Nguồn dữ liệu

- Kho lưu trữ văn bản, báo cáo cũ của UBND phường
- Log ghi nhận chỉnh sửa thực tế của cán bộ trên hệ thống

## Cách lấy dữ liệu

- Thu thập báo cáo lịch sử cùng các tệp dữ liệu thô đầu vào của các kỳ báo cáo đó
- Số hóa báo cáo lịch sử thành file số liệu chuẩn để làm Ground Truth phục vụ đối sánh tự động bằng code
- Chạy thử nghiệm AI trên tệp dữ liệu thô lịch sử và tự động tính toán sai số

---

# 5. Thành phần Agentic AI (Memory, Tools, Hooks & Rules)

Để chuyển đổi từ một AI Pipeline thông thường sang **Agentic AI** (Hệ tác tử AI tự trị), hệ thống bổ sung các thành phần sau:

## 5.1. Memory (Bộ nhớ tác tử)
Giúp tác tử lưu giữ ngữ cảnh để phản hồi tự nhiên và nhất quán:
- **Short-term Memory (Bộ nhớ ngắn hạn):** Lưu trữ toàn bộ hội thoại của phiên làm việc (session history) và các tài liệu, bảng biểu vừa được tải lên trong luồng xử lý hiện tại.
- **Long-term Memory (Bộ nhớ dài hạn):** Lưu giữ các thông tin cấu hình đặc thù của phường, thói quen viết báo cáo của cán bộ tổng hợp, và các phản hồi/chỉnh sửa của lãnh đạo từ các kỳ báo cáo trước để tự động điều chỉnh hành vi sinh văn bản trong tương lai.

## 5.2. Tools (Hộp công cụ hành động)
Cung cấp cho tác tử khả năng chủ động tương tác với hệ thống và dữ liệu thông qua các công cụ chuyên biệt:
- **Parser Tools:** Trích xuất nội dung từ các định dạng Word, Excel, PDF và OCR tài liệu quét.
- **Standardization Tools:** So khớp fuzzy tên địa bàn (với Master GSO) và phòng ban hành chính.
- **Rule Engine Tool:** Thực thi các phép tính toán logic và kiểm tra chéo số liệu dựa trên `validation_rules.json`.
- **RAG Search Tool:** Tìm kiếm ngữ cảnh luật pháp và biểu mẫu báo cáo liên quan.

## 5.3. Hooks (Bộ lọc bảo mật & Kiểm soát thông tin mật)
Cơ chế bảo mật dữ liệu nhạy cảm và thông tin mật trước khi xử lý hoặc gửi tới mô hình ngôn ngữ lớn (nhất là khi sử dụng LLM Cloud API):
- **Anonymization Hook (Mã hóa thông tin cá nhân):** Tự động phát hiện và che giấu (masking/anonymize) các thông tin định danh cá nhân (PII) như: Họ tên công dân, Số CCCD, Số điện thoại, Địa chỉ nhà chi tiết,... nhằm tuân thủ **Nghị định số 13/2023/NĐ-CP** về bảo vệ dữ liệu cá nhân.
- **Redaction Hook (Kiểm soát thông tin mật):** Bộ lọc kiểm tra các từ khóa thuộc danh mục tài liệu mật (bí mật nhà nước, kế hoạch quốc phòng địa phương, ngân sách mật) để ngăn chặn rò rỉ dữ liệu ra ngoài phạm vi máy chủ nội bộ (On-premise).

## 5.4. Rules (Quy tắc tác tử)
Các quy chế và ranh giới hoạt động quy định hành vi của tác tử:
- Quy tắc kiểm tra tính hợp lệ số liệu bắt buộc (Error) và cảnh báo (Warning).
- Quy trình phê duyệt có sự tham gia của con người (Human-in-the-loop) để kiểm duyệt báo cáo trước khi ký số.

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
      Agentic AI (LLM + RAG + Tools + Memory)
                 │
                 ▼
Tổng hợp và chuẩn hóa số liệu thuộc 3 lĩnh vực:
- Dân cư
- Khiếu nại - tố cáo
- Chỉ tiêu thực hiện nhiệm vụ
                 │
                 ▼
      Sinh báo cáo đúng mẫu UBND
                 │
                 ▼
            Evaluation
```

## Ghi chú

- Dự án **không Fine-tuning mô hình LLM**.
- Hệ thống triển khai theo hướng **Agentic AI** sử dụng **LLM kết hợp RAG, Memory, Tools và Rules Engine** để tự động hóa xử lý và tổng hợp.
- Các **Hooks bảo mật** nằm ở biên (edge) của Agent để đảm bảo lọc bỏ thông tin định danh cá nhân (PII) và thông tin mật trước khi tương tác với các dịch vụ bên ngoài.
- AI đóng vai trò trung tâm trong toàn bộ quy trình; cán bộ chủ yếu thực hiện kiểm duyệt và phê duyệt báo cáo cuối cùng.



