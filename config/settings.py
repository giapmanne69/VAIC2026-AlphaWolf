import os
from pathlib import Path
from dotenv import load_dotenv

# Tự động tìm và load file .env từ thư mục gốc của dự án
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# 1. API Configurations (FPT AI Factory / OpenAI compatible)
FPT_API_KEY = os.getenv("FPT_API_KEY", "YOUR_FPT_API_KEY_HERE")
FPT_BASE_URL = os.getenv("FPT_BASE_URL", "https://api.fpt.ai/v1")  # Cần cập nhật đúng endpoint của FPT AI Factory
LLM_MODEL = os.getenv("LLM_MODEL", "Llama-3.3-70B-Instruct")
VISION_MODEL = os.getenv("VISION_MODEL", "Qwen2.5-VL-7B-Instruct")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "multilingual-e5-large")
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "bge-reranker-v2-m3")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# 2. Directory Configurations (Windows compatible paths)
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"
PROMPTS_DIR = CONFIG_DIR / "prompts"
POPULATION_BUNDLE_CONFIG_PATH = CONFIG_DIR / "population_bundle.yaml"

# Cấu hình danh mục chuẩn
MASTER_DATA_DIR = DATA_DIR / "chuan_hoa_hop_nhat"
WARDS_CSV_PATH = MASTER_DATA_DIR / "dm_don_vi" / "wards.csv"
DEPARTMENTS_CSV_PATH = MASTER_DATA_DIR / "dm_phong_ban" / "phong_ban.csv"
REPORT_SCHEMA_PATH = MASTER_DATA_DIR / "report_schema.json"
VALIDATION_RULES_PATH = MASTER_DATA_DIR / "validation_rules.json"

# Cấu hình RAG & Vector DB
RAG_DIR = DATA_DIR / "rag"
LEGAL_DOCS_DIR = RAG_DIR / "legal_docs"
FAISS_DB_DIR = RAG_DIR / "vector_db"

# Thư mục chứa template và đầu vào phục vụ test
TEMPLATES_DIR = DATA_DIR / "templates"
RAW_INPUTS_DIR = DATA_DIR / "raw_inputs"

# 3. Model Parameters
EMBEDDING_MODEL_NAME = "symanto/sn-xlm-roberta-base-snli-mnli-anli"  # Hoặc 'sentence-transformers/multilingual-e5-large'
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
TARGET_REPORT_PERIOD = os.getenv("TARGET_REPORT_PERIOD", "")

# Tạo các thư mục nếu chưa tồn tại
for folder in [LEGAL_DOCS_DIR, FAISS_DB_DIR, TEMPLATES_DIR, RAW_INPUTS_DIR, PROMPTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)
