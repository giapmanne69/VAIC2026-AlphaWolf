import sys
from pathlib import Path

# Tự động cấu hình PYTHONPATH trỏ về thư mục gốc của dự án
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import json
import tempfile
import pandas as pd

# Thiết lập cấu hình trang Streamlit (phải ở dòng đầu tiên)
st.set_page_config(
    page_title="Hệ thống Tác tử Tổng hợp Báo cáo UBND Phường",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS để làm nổi bật thẩm mỹ (Gradients, Glassmorphism, Google Fonts)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Cấu hình tiêu đề gradient */
    .title-gradient {
        background: linear-gradient(135deg, #FF4B4B, #FF8F00, #00C853);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        color: #757575;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Thiết kế Glassmorphism cho các khung thông tin */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        margin-bottom: 1.5rem;
    }
    
    .status-badge-pass {
        background-color: #E8F5E9;
        color: #2E7D32;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    .status-badge-fail {
        background-color: #FFEBEE;
        color: #C62828;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Lớp Agent và bộ nhớ
from src.agent import AgenticReportAgent
from config import settings

# Khởi tạo hoặc tái sử dụng instance Agent trong Session State của Streamlit
if "agent" not in st.session_state:
    st.session_state.agent = AgenticReportAgent()

agent = st.session_state.agent

# --- SIDEBAR: CẤU HÌNH HỆ THỐNG ---
st.sidebar.markdown("<h2 style='font-weight:800;'>⚙️ CẤU HÌNH AI</h2>", unsafe_allow_html=True)
st.sidebar.info("Hệ thống đang cấu hình chạy trực tiếp với mô hình Llama-3.3-70B-Instruct thông qua FPT AI Factory API.")

# Điền nhanh API Key
api_key = st.sidebar.text_input("FPT AI Factory API Key", value=settings.FPT_API_KEY, type="password")
model_name = st.sidebar.text_input("LLM Model Name", value=settings.LLM_MODEL)

if api_key != settings.FPT_API_KEY:
    settings.FPT_API_KEY = api_key
    agent.client.api_key = api_key

# --- MÀN HÌNH CHÍNH ---
st.markdown("<h1 class='title-gradient'>🏛️ UBND Phường - Agentic AI Report Hub</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Tác tử AI hỗ trợ tự động hóa phân tích biểu mẫu động, trích xuất dữ liệu đa nguồn và viết báo cáo hành chính công chuẩn quy định.</p>", unsafe_allow_html=True)

col_upload, col_process = st.columns([1, 2])

with col_upload:
    st.markdown("### 📥 Tải dữ liệu đầu vào")
    
    # 1. Upload file mẫu Word trống
    template_file = st.file_uploader(
        "Tải lên Biểu mẫu trống (.docx)", 
        type=["docx"], 
        help="Cán bộ tải biểu mẫu có sẵn hoặc mẫu có chứa Jinja tags {{placeholder}} để AI điền vào."
    )
    
    # 2. Upload các file báo cáo phòng ban chuyên ngành thô
    raw_files = st.file_uploader(
        "Tải lên các Báo cáo thô phòng ban", 
        type=["docx", "xlsx", "pdf", "png", "jpg"], 
        accept_multiple_files=True,
        help="Tải lên báo cáo thô của Tư pháp, Một cửa, Địa chính, Công an... định dạng Word, Excel, PDF hoặc ảnh chụp."
    )
    
    # 3. Custom RAG Context input (Cho phép cán bộ nhập/stubs tài liệu luật pháp thủ công do chưa có DB)
    st.markdown("---")
    st.markdown("#### 📖 Tri thức luật bổ sung (RAG)")
    rag_context = st.text_area(
        "Cơ sở pháp lý cần viện dẫn (RAG):", 
        value="Nghị định 61/2018/NĐ-CP ngày 23/4/2018 của Chính phủ quy định về thực hiện cơ chế một cửa, một cửa liên thông trong giải quyết thủ tục hành chính.",
        height=100
    )

with col_process:
    st.markdown("### ⚙️ Tiến trình trích xuất & Sinh báo cáo")
    if not template_file or not raw_files:
        st.warning("Vui lòng tải lên đầy đủ file biểu mẫu trống và ít nhất 1 báo cáo thô để bắt đầu.")
    else:
        if st.button("🚀 BẮT ĐẦU XỬ LÝ REPORT PIPELINE", type="primary", width="stretch"):
            
            # Sử dụng thư mục tạm thời để xử lý file tải lên
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_dir_path = Path(tmp_dir)
                
                # Lưu file template
                temp_template_path = tmp_dir_path / template_file.name
                with open(temp_template_path, "wb") as f:
                    f.write(template_file.getbuffer())
                
                # Lưu các file thô
                temp_raw_paths = []
                for rf in raw_files:
                    path = tmp_dir_path / rf.name
                    with open(path, "wb") as f:
                        f.write(rf.getbuffer())
                    temp_raw_paths.append(str(path))
                
                # --- STAGE 1: Phân tích biểu mẫu mẫu ---
                with st.status("🔍 Stage 1: Đang quét cấu hình biểu mẫu mẫu trống...", expanded=True) as status:
                    st.write("Đang đọc file biểu mẫu...")
                    schema = agent.parse_template_schema(str(temp_template_path))
                    st.write("Đã phát hiện Schema các chỉ tiêu cần điền:")
                    st.json(schema)
                    status.update(label="Stage 1: Hoàn tất phân tích biểu mẫu!", state="complete")
                
                # --- STAGE 2 & 3: Trích xuất và bảo mật thông tin ---
                with st.status("🛡️ Stage 2 & 3: Đang ẩn danh PII và trích xuất số liệu...", expanded=True) as status:
                    st.write("Đang quét từ khóa nhạy cảm (Redaction Hook)...")
                    st.write("Đang che giấu thông tin cá nhân (Anonymizer Hook)...")
                    st.write("Đang gửi LLM trích xuất số liệu thô...")
                    raw_data = agent.extract_from_raw_inputs(schema, temp_raw_paths)
                    st.write("Dữ liệu trích xuất thô thu được:")
                    st.json(raw_data)
                    status.update(label="Stage 2 & 3: Hoàn tất trích xuất và bảo mật!", state="complete")
                
                # --- STAGE 4: Chạy Rule Engine và tự sửa lỗi ---
                with st.status("🧮 Stage 4: Đang kiểm tra logic số liệu chéo...", expanded=True) as status:
                    st.write("Chạy kiểm tra quy tắc validation_rules.json...")
                    final_data, failures = agent.run_validation_and_self_correction(raw_data)
                    
                    if not failures:
                        st.markdown("<span class='status-badge-pass'>PASS</span> Không phát hiện mâu thuẫn số liệu.", unsafe_allow_html=True)
                    else:
                        st.write("Kết quả kiểm tra chéo:")
                        for fail in failures:
                            status_badge = "FAIL (ERROR)" if fail["severity"] == "error" else "WARNING"
                            badge_class = "status-badge-fail" if fail["severity"] == "error" else "status-badge-pass"
                            st.markdown(
                                f"- <span class='{badge_class}'>{status_badge}</span> **{fail['id']}**: {fail['description']}<br>"
                                f"  *Công thức: `{fail['formula']}` (Trạng thái: {fail['error_msg']})*", 
                                unsafe_allow_html=True
                            )
                    
                    status.update(label="Stage 4: Kiểm lỗi hoàn tất!", state="complete")
                
                # --- STAGE 6: Sinh nhận định và ghi tệp Word ---
                with st.status("📝 Stage 6: Đang sinh đoạn văn nhận định & điền mẫu...", expanded=True) as status:
                    st.write("Đang tìm kiếm cơ sở pháp lý (RAG stubs)...")
                    st.write("Đang gọi Llama-3.3 viết nhận định hành chính...")
                    
                    # Tạo file output tạm
                    output_file_name = f"Bao_cao_tong_hop_{Path(template_file.name).stem}.docx"
                    temp_output_path = Path(settings.DATA_DIR) / "output_reports" / output_file_name
                    
                    remarks = agent.generate_final_report(
                        kpi_data=final_data,
                        template_path=str(temp_template_path),
                        output_path=str(temp_output_path),
                        rag_context=rag_context
                    )
                    st.write("Nhận định do AI viết:")
                    st.info(remarks)
                    
                    # Lưu trữ các biến vào session state để tải về
                    st.session_state.final_remarks = remarks
                    st.session_state.final_kpi = final_data
                    st.session_state.output_path_str = str(temp_output_path)
                    st.session_state.output_file_name = output_file_name
                    
                    status.update(label="Stage 6: Hoàn thành sinh báo cáo!", state="complete")
                    
                st.balloons()

        # Hiển thị kết quả tải về nếu báo cáo đã được sinh ra thành công
        if "output_path_str" in st.session_state and Path(st.session_state.output_path_str).exists():
            st.markdown("---")
            st.markdown("### 🏆 Báo cáo đã hoàn thành!")
            
            # Cho phép cán bộ sửa trực tiếp văn bản AI nhận xét (Human-in-the-loop)
            st.markdown("#### 🖊️ Hiệu chỉnh nhận xét tự động (Human-in-the-loop)")
            user_edited_remarks = st.text_area(
                "Bạn có thể tinh chỉnh lại đoạn văn nhận định bên dưới. Mọi chỉnh sửa sẽ được lưu vào bộ nhớ thói quen để AI tự học hỏi cho lần sau:",
                value=st.session_state.final_remarks,
                height=150
            )
            
            # Ghi nhận chỉnh sửa của cán bộ vào LongTermMemory nếu có thay đổi
            if user_edited_remarks != st.session_state.final_remarks:
                agent.long_memory.add_style_preference("user_adjusted_remarks", user_edited_remarks)
                st.toast("Đã lưu thói quen chỉnh sửa của cán bộ vào bộ nhớ dài hạn!", icon="🧠")
                
            # Nút tải file báo cáo Word
            with open(st.session_state.output_path_str, "rb") as f:
                btn = st.download_button(
                    label="📥 Tải xuống báo cáo hoàn chỉnh (.docx)",
                    data=f,
                    file_name=st.session_state.output_file_name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    width="stretch"
                )
            
            # Bảng tổng hợp số liệu trích xuất chuẩn hóa
            st.markdown("#### 📊 Bảng số liệu trích xuất chuẩn hóa:")
            kpi_df = pd.DataFrame(
                [{"Chỉ số": k, "Giá trị trích xuất": str(v) if v is not None else ""} for k, v in st.session_state.final_kpi.items()]
            )
            st.dataframe(kpi_df, width="stretch")
