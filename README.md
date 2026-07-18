# VAIC AI Report Agent - Trợ lý tổng hợp báo cáo hành chính UBND Phường

Chào mừng bạn đến với **VAIC AI Report Agent** – Hệ thống trợ lý tác tử thông minh (Autonomous ReAct Agent) hỗ trợ cán bộ hành chính UBND Phường tự động hóa việc đọc tài liệu báo cáo thô của các phòng ban (Kinh tế, Tư pháp, An ninh,...), kiểm lỗi logic số liệu chéo, tự sửa sai, tra cứu tri thức pháp luật (RAG) và tự động điền kết quả kèm theo nhận xét đánh giá vào biểu mẫu báo cáo Word (`.docx`).

---

## 1. Yêu cầu hệ thống tối thiểu (Prerequisites)

Hệ thống hoạt động tương thích trên mọi nền tảng phổ biến (**Windows, macOS, Linux**). Hãy chuẩn bị sẵn:

*   **Python:** Phiên bản từ `3.9` đến `3.12` (Khuyên dùng `3.10` hoặc `3.11`).
*   **Node.js:** Phiên bản từ `18.0` trở lên (Dùng để biên dịch giao diện React).
*   **Git:** Dùng để clone mã nguồn (tùy chọn).

---

## 2. Các bước cài đặt chi tiết (Step-by-Step Installation)

### Bước 1: Tải mã nguồn về máy tính
Giải nén mã nguồn hoặc sử dụng lệnh Git:
```bash
git clone https://github.com/giapmanne69/VAIC2026-AlphaWolf.git
cd VAIC2026-AlphaWolf
```

### Bước 2: Thiết lập cấu hình môi trường (`.env`)
Tạo một tệp tin tên `.env` tại thư mục gốc của dự án (cùng cấp với tệp `README.md`) và nhập nội dung cấu hình sau:

```env
# Khóa API FPT AI Factory (Hoặc nhà cung cấp tương thích OpenAI)
FPT_API_KEY=your_api_key_here
FPT_API_BASE=https://api.fpt.ai/v1

# Cấu hình các mô hình bổ trợ
LLM_MODEL=Llama-3.3-70B-Instruct
VISION_MODEL=Qwen2.5-VL-7B-Instruct
EMBEDDING_MODEL=multilingual-e5-large
RERANKER_MODEL=bge-reranker-v2-m3
```
*(Nếu bạn chạy không cần khóa API riêng, hệ thống sẽ sử dụng khóa mặc định của hệ thống).*

---

### Bước 3: Thiết lập môi trường ảo Python (Backend)

Hãy chọn dòng lệnh tương ứng với hệ điều hành của bạn:

#### Trên Windows (PowerShell):
```powershell
# Khởi tạo môi trường ảo venv
python -m venv venv

# Kích hoạt môi trường ảo
.\venv\Scripts\Activate.ps1

# Nâng cấp pip và cài đặt các thư viện Python
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Trên Windows (CMD - Command Prompt):
```cmd
# Khởi tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo
call venv\Scripts\activate.bat

# Nâng cấp pip và cài đặt thư viện
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Trên macOS / Linux:
```bash
# Khởi tạo môi trường ảo
python3 -m venv venv

# Kích hoạt môi trường ảo
source venv/bin/activate

# Cài đặt các thư viện
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### Bước 4: Tự động biên dịch giao diện Frontend (React)
Để giúp việc cài đặt được diễn ra thông suốt trên mọi hệ điều hành mà không cần gõ nhiều lệnh phức tạp, chúng tôi cung cấp tệp script tự động:

```bash
# Hãy chắc chắn rằng bạn đang kích hoạt môi trường ảo Python
python build_frontend.py
```
*Script này sẽ tự động: Chạy `npm install` tải các gói npm ➔ Chạy `npm run build` đóng gói React SPA ➔ Tự động đồng bộ các tệp tĩnh vào thư mục `src/static/` phục vụ cho Backend.*

---

### Bước 5: Khởi chạy ứng dụng
Bây giờ, bạn chỉ cần khởi động máy chủ FastAPI:

```bash
# Trên Windows/macOS/Linux
python -m uvicorn src.server:app --host 0.0.0.0 --port 8000
```

Mở trình duyệt web của bạn và truy cập:
👉 **[http://localhost:8000/](http://localhost:8000/)**

---

## 3. Cách kiểm thử nhanh luồng hoạt động (Test Samples)

Dự án đi kèm bộ dữ liệu kiểm thử mẫu tại thư mục [data/test_samples/](file:///e:/Project/VAIC_Project/data/test_samples). Bạn thực hiện chạy thử như sau:

1.  Mở trình duyệt truy cập: **`http://localhost:8000/`**.
2.  **Tại Bước 1 (Nạp file)**:
    *   Tải tệp `1_bieu_mau_chuan.docx` lên ô *Biểu mẫu báo cáo trống*.
    *   Chọn đồng thời và tải 3 tệp `2_bao_cao_kinh_te.xlsx`, `3_bao_cao_tu_phap.docx`, `4_bao_cao_an_ninh.docx` lên ô *Tài liệu thô phòng ban*.
3.  **Tại Bước 2 (Chạy AI)**: Bấm **Khởi chạy Tác tử AI** và theo dõi logs ReAct Loop phân tích trực tiếp trên màn hình console.
4.  **Tại Bước 3 (Duyệt số & Nhận xét)**: Kiểm tra lại các chỉ số đã được trích xuất trên bảng, hiệu chỉnh nếu muốn và nhấn **Tải báo cáo Word (.docx)** để nhận tệp tin kết quả cuối cùng.

---

## 4. Hướng dẫn dành cho Lập trình viên (Developer Mode)

Nếu bạn muốn thay đổi trực tiếp mã nguồn Frontend (React) và xem thay đổi ngay lập tức (HMR), hãy khởi chạy hai máy chủ độc lập:

1.  **Chạy Backend**: Khởi chạy FastAPI ở cổng `8000` (xem Bước 5).
2.  **Chạy Frontend**:
    ```bash
    cd frontend
    npm run dev
    ```
3.  Truy cập qua cổng của Vite: **`http://localhost:5173/`**. 
    *   *Mọi yêu cầu kết nối API sẽ được tự động chuyển tiếp sang cổng `8000` thông qua cấu hình proxy trong `vite.config.js`.*

---

## 5. Bản đồ cấu trúc thư mục chính của dự án

```text
VAIC_Project/
│
├── config/                     # Lời nhắc (Prompts Registry) & cấu hình settings.py
├── data/                       # Dữ liệu của hệ thống
│   ├── chuan_hoa_hop_nhat/     # Quy định logic kiểm chéo số liệu
│   ├── templates/              # Thư mục lưu biểu mẫu gốc
│   └── test_samples/           # [NEW] Dữ liệu mẫu phục vụ kiểm thử giao diện
│
├── src/                        # Mã nguồn cốt lõi của Agent (Python)
│   ├── agent.py                # ReAct Loop AI Agent chính
│   ├── server.py               # FastAPI Backend & SSE stream event
│   ├── static/                 # Folder chứa React App đã biên dịch (FastAPI serve trực tiếp)
│   ├── hooks/                  # Bộ lọc bảo mật an toàn thông tin (Masking PII)
│   └── tools/                  # Hộp công cụ đọc file, Rule engine, RAG
│
├── frontend/                   # Mã nguồn Frontend React SPA (Vite + TailwindCSS v4)
│   ├── src/                    # Components & Pages của giao diện
│   ├── vite.config.js          # Cấu hình build & API Proxy
│   └── package.json            # Thư viện npm phụ trợ
│
├── build_frontend.py           # [NEW] Script tự động cài npm & build React trên mọi HĐH
├── requirements.txt            # Thư viện Python cần cài đặt
└── README.md                   # Tài liệu hướng dẫn vận hành
```

---

## 6. Xử lý sự cố thường gặp (Troubleshooting)

*   **Lỗi: `node` hoặc `npm` không được nhận diện**:
    *   Đảm bảo bạn đã cài đặt Node.js và đã khởi động lại Terminal hoặc IDE (VSCode, PyCharm,...) để hệ thống cập nhật biến môi trường `$PATH`.
*   **Lỗi: `Port 8000 is already in use`**:
    *   Cổng 8000 đã có ứng dụng khác sử dụng (ví dụ tiến trình uvicorn cũ chạy ngầm).
    *   Khắc phục nhanh bằng cách đổi cổng khi chạy uvicorn:
        `python -m uvicorn src.server:app --port 8001`
*   **Lỗi phân quyền (Permission Denied) trên Windows PowerShell**:
    *   Nếu PowerShell chặn kích hoạt venv, hãy mở PowerShell bằng quyền Admin và chạy lệnh:
        `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` và nhập `Y`.
