import sys
from pathlib import Path

# Tự động cấu hình PYTHONPATH trỏ về thư mục gốc của dự án
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
import json
import tempfile
import pandas as pd
import io
import logging
from docxtpl import DocxTemplate

# Khởi tạo logger cho Frontend
logger = logging.getLogger("StreamlitApp")

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

# --- HELPER: RENDER WORD IN-MEMORY (TRÁNH LỖI FILE TRỐNG) ---
def render_docx_in_memory(template_bytes: bytes, kpi_data: dict, remarks: str) -> bytes:
    """
    Render biểu mẫu Word trực tiếp trên bộ nhớ RAM để đảm bảo tính đồng bộ dữ liệu
    và cho phép cập nhật tức thì các chỉnh sửa thủ công của cán bộ (Human-in-the-loop).
    """
    try:
        doc = DocxTemplate(io.BytesIO(template_bytes))
        context = kpi_data.copy()
        context["nhan_xet_ai"] = remarks
        
        logger.info(f"Đang render Word trực tiếp trên bộ nhớ với {len(kpi_data)} chỉ số.")
        doc.render(context)
        
        output_stream = io.BytesIO()
        doc.save(output_stream)
        return output_stream.getvalue()
    except Exception as e:
        logger.exception("Lỗi khi render biểu mẫu Word trong bộ nhớ:")
        raise e

# --- SIDEBAR: CẤU HÌNH HỆ THỐNG ---
st.sidebar.markdown("<h2 style='font-weight:800;'>⚙️ CẤU HÌNH AI</h2>", unsafe_allow_html=True)
st.sidebar.info("Hệ thống đang cấu hình chạy trực tiếp với mô hình Llama-3.3-70B-Instruct thông qua FPT AI Factory API.")

# Điền nhanh API Key
api_key = st.sidebar.text_input("FPT AI Factory API Key", value=settings.FPT_API_KEY, type="password")
model_name = st.sidebar.text_input("LLM Model Name", value=settings.LLM_MODEL)

if api_key != settings.FPT_API_KEY:
    settings.FPT_API_KEY = api_key
    agent.client.api_key = api_key
    logger.info("Cập nhật FPT_API_KEY từ sidebar.")

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
    
    # 3. Custom RAG Context input
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
            logger.info("--- BẮT ĐẦU CHẠY PIPELINE TRÍCH XUẤT ---")
            
            # Lưu trữ file bytes của template vào session state
            st.session_state.template_bytes = template_file.getvalue()
            st.session_state.output_file_name = f"Bao_cao_tong_hop_{Path(template_file.name).stem}.docx"
            
            # Sử dụng thư mục tạm thời để lưu file vật lý chạy Parser
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_dir_path = Path(tmp_dir)
                
                temp_template_path = tmp_dir_path / template_file.name
                with open(temp_template_path, "wb") as f:
                    f.write(st.session_state.template_bytes)
                
                temp_raw_paths = []
                for rf in raw_files:
                    path = tmp_dir_path / rf.name
                    with open(path, "wb") as f:
                        f.write(rf.getbuffer())
                    temp_raw_paths.append(str(path))
                
                try:
                    # --- STAGE 1: Phân tích biểu mẫu mẫu ---
                    with st.status("🔍 Stage 1: Đang quét cấu hình biểu mẫu mẫu trống...", expanded=True) as status:
                        schema = agent.parse_template_schema(str(temp_template_path))
                        st.write("Schema chỉ tiêu phát hiện được:")
                        st.json(schema)
                        status.update(label="Stage 1: Hoàn tất!", state="complete")
                    
                    # --- STAGE 2 & 3: Trích xuất số liệu ---
                    with st.status("🛡️ Stage 2 & 3: Đang ẩn danh PII và trích xuất số liệu...", expanded=True) as status:
                        raw_data = agent.extract_from_raw_inputs(schema, temp_raw_paths)
                        st.write("Dữ liệu trích xuất:")
                        st.json(raw_data)
                        status.update(label="Stage 2 & 3: Hoàn tất!", state="complete")
                    
                    # --- STAGE 4: Kiểm chéo và tự sửa lỗi ---
                    with st.status("🧮 Stage 4: Đang kiểm tra logic số liệu chéo...", expanded=True) as status:
                        final_data, failures = agent.run_validation_and_self_correction(raw_data)
                        
                        if not failures:
                            st.markdown("<span class='status-badge-pass'>PASS</span> Không phát hiện lỗi logic.", unsafe_allow_html=True)
                        else:
                            for fail in failures:
                                status_badge = "FAIL (ERROR)" if fail["severity"] == "error" else "WARNING"
                                badge_class = "status-badge-fail" if fail["severity"] == "error" else "status-badge-pass"
                                st.markdown(
                                    f"- <span class='{badge_class}'>{status_badge}</span> **{fail['id']}**: {fail['description']}<br>"
                                    f"  *Công thức: `{fail['formula']}` ({fail['error_msg']})*", 
                                    unsafe_allow_html=True
                                )
                        status.update(label="Stage 4: Kiểm lỗi hoàn tất!", state="complete")
                    
                    # --- STAGE 6: Sinh nhận định ---
                    with st.status("📝 Stage 6: Đang sinh đoạn văn nhận định...", expanded=True) as status:
                        # Sinh nhận xét thô bằng LLM và lưu vào bộ nhớ
                        remarks = agent.generate_final_report(
                            kpi_data=final_data,
                            template_path=str(temp_template_path),
                            output_path=str(tmp_dir_path / "mock.docx"), # Chỉ ghi file mock thô
                            rag_context=rag_context
                        )
                        st.write("Nhận định từ LLM:")
                        st.info(remarks)
                        
                        # Lưu trữ kết quả trích xuất vào Session State
                        st.session_state.final_remarks = remarks
                        st.session_state.final_kpi = final_data
                        
                        status.update(label="Stage 6: Hoàn tất sinh nhận định!", state="complete")
                        
                    st.balloons()
                    logger.info("Pipeline trích xuất báo cáo chạy thành công.")
                except Exception as e:
                    logger.exception("Lỗi xảy ra trong quá trình chạy Report Pipeline:")
                    st.error(f"Đã xảy ra lỗi nghiêm trọng: {str(e)}. Xem chi tiết tại data/agent_execution.log")

        # Màn hình kết quả khi dữ liệu đã sẵn sàng trong session state
        if "final_kpi" in st.session_state and "template_bytes" in st.session_state:
            st.markdown("---")
            st.markdown("### 🏆 Báo cáo đã sẵn sàng tải về")
            
            # Khung Human-in-the-loop cho phép sửa trực tiếp nhận xét
            st.markdown("#### 🖊️ Hiệu chỉnh nhận xét tự động (Human-in-the-loop)")
            user_edited_remarks = st.text_area(
                "Bạn có thể tinh chỉnh đoạn văn dưới đây. File Word tải xuống sẽ tự động cập nhật theo nội dung mới này:",
                value=st.session_state.final_remarks,
                height=150
            )
            
            # Đồng bộ chỉnh sửa vào bộ nhớ dài hạn
            if user_edited_remarks != st.session_state.final_remarks:
                agent.long_memory.add_style_preference("user_adjusted_remarks", user_edited_remarks)
                st.session_state.final_remarks = user_edited_remarks
                st.toast("Đã lưu thói quen chỉnh sửa và cập nhật tệp tải về!", icon="🧠")
            
            # RENDER TRÊN BỘ NHỚ RAM TRƯỚC KHI TẢI VỀ
            try:
                docx_bytes = render_docx_in_memory(
                    template_bytes=st.session_state.template_bytes,
                    kpi_data=st.session_state.final_kpi,
                    remarks=st.session_state.final_remarks
                )
                
                st.download_button(
                    label="📥 Tải xuống báo cáo hoàn chỉnh (.docx)",
                    data=docx_bytes,
                    file_name=st.session_state.output_file_name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    width="stretch"
                )
            except Exception as e:
                st.error(f"Lỗi khi xuất tệp báo cáo: {str(e)}")
            
            # Bảng tổng hợp số liệu trích xuất chuẩn hóa
            st.markdown("#### 📊 Bảng số liệu trích xuất chuẩn hóa:")
            kpi_df = pd.DataFrame(
                [{"Chỉ số": k, "Giá trị trích xuất": str(v) if v is not None else ""} for k, v in st.session_state.final_kpi.items()]
            )
            st.dataframe(kpi_df, width="stretch")
