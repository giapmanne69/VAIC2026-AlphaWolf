import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from config import settings
from src.tools.rag_search import RAGSearchTool

logger = logging.getLogger("MemoryManager")

class MemoryManager:
    def __init__(self):
        self.db_path = Path(settings.DATA_DIR) / "memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.rag_tool = RAGSearchTool()
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """
        Khởi tạo các bảng SQLite phục vụ bộ nhớ tác tử:
        1. task_states: Quản lý trạng thái tiến trình
        2. indicators: Lưu trữ số liệu nghiệp vụ có cấu trúc và nguồn gốc (provenance)
        3. cache_store: Cache đệm cho kết quả phân tích file / OCR
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 1. Bảng Trạng thái Nhiệm vụ
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_states (
                task_id TEXT PRIMARY KEY,
                current_step INTEGER DEFAULT 0,
                current_file TEXT,
                completed_files TEXT,
                total_files INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
        """)

        # 2. Bảng Chỉ tiêu trích xuất (Indicator Memory)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indicators (
                task_id TEXT,
                indicator_name TEXT,
                value REAL,
                unit TEXT,
                source_file TEXT,
                sheet_name TEXT,
                page_number INTEGER,
                cell_reference TEXT,
                confidence REAL,
                metadata TEXT,
                PRIMARY KEY (task_id, indicator_name)
            )
        """)

        # 3. Bảng Cache tạm thời
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_store (
                cache_key TEXT PRIMARY KEY,
                cache_value TEXT
            )
        """)

        conn.commit()
        conn.close()
        logger.info("Đã khởi tạo SQLite Memory Database thành công.")

    # ==========================================
    # 1. TASK STATE MANAGEMENT (REDIS ALTERNATIVE)
    # ==========================================
    
    def create_task(self, task_id: str, total_files: int, status: str = "running"):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO task_states (task_id, total_files, status, current_step, completed_files)
            VALUES (?, ?, ?, 0, '[]')
        """, (task_id, total_files, status))
        conn.commit()
        conn.close()
        logger.info(f"Đã tạo task mới trong bộ nhớ: {task_id}")

    def update_progress(self, task_id: str, current_step: int, current_file: str, completed_files: List[str], status: str = "running"):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE task_states
            SET current_step = ?, current_file = ?, completed_files = ?, status = ?
            WHERE task_id = ?
        """, (current_step, current_file, json.dumps(completed_files), status, task_id))
        conn.commit()
        conn.close()

    def finish_task(self, task_id: str, status: str = "completed"):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE task_states
            SET status = ?
            WHERE task_id = ?
        """, (status, task_id))
        conn.commit()
        conn.close()

    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM task_states WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            res = dict(row)
            try:
                res["completed_files"] = json.loads(res["completed_files"])
            except:
                res["completed_files"] = []
            return res
        return None

    # ==========================================
    # 2. INDICATOR STORAGE & PROVENANCE (POSTGRES ALTERNATIVE)
    # ==========================================

    def save_indicator(
        self,
        task_id: str,
        indicator_name: str,
        value: Optional[float],
        unit: Optional[str] = None,
        source_file: Optional[str] = None,
        sheet_name: Optional[str] = None,
        page_number: Optional[int] = None,
        cell_reference: Optional[str] = None,
        confidence: float = 1.0,
        meta_dict: Optional[Dict[str, Any]] = None
    ):
        conn = self.get_connection()
        cursor = conn.cursor()
        meta_str = json.dumps(meta_dict) if meta_dict else "{}"

        safe_value = value
        if isinstance(value, (list, dict)):
            try:
                safe_value = json.dumps(value, ensure_ascii=False)
            except Exception:
                safe_value = str(value)

        cursor.execute("""
            INSERT OR REPLACE INTO indicators (
                task_id, indicator_name, value, unit, source_file, sheet_name, page_number, cell_reference, confidence, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task_id, indicator_name, safe_value, unit, source_file, sheet_name, page_number, cell_reference, confidence, meta_str))
        conn.commit()
        conn.close()

    def get_indicator(self, task_id: str, indicator_name: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM indicators WHERE task_id = ? AND indicator_name = ?", (task_id, indicator_name))
        row = cursor.fetchone()
        conn.close()
        if row:
            res = dict(row)
            res["metadata"] = json.loads(res["metadata"]) if res.get("metadata") else {}
            return res
        return None

    def search_indicator(self, task_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Tìm kiếm các chỉ tiêu liên quan dựa trên tên chỉ tiêu (Keyword Search).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        # Tìm kiếm tương đối tên chỉ tiêu
        search_query = f"%{query}%"
        cursor.execute("SELECT * FROM indicators WHERE task_id = ? AND indicator_name LIKE ?", (task_id, search_query))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for r in rows:
            res = dict(r)
            res["metadata"] = json.loads(res["metadata"]) if res.get("metadata") else {}
            results.append(res)
        return results

    def list_indicators(self, task_id: str) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM indicators WHERE task_id = ?", (task_id,))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for r in rows:
            res = dict(r)
            res["metadata"] = json.loads(res["metadata"]) if res.get("metadata") else {}
            results.append(res)
        return results

    # ==========================================
    # 3. LOCAL CACHE SYSTEM (REDIS CACHE ALTERNATIVE)
    # ==========================================

    def cache_get(self, key: str) -> Optional[Any]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT cache_value FROM cache_store WHERE cache_key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            try:
                return json.loads(row["cache_value"])
            except:
                return row["cache_value"]
        return None

    def cache_set(self, key: str, value: Any):
        conn = self.get_connection()
        cursor = conn.cursor()
        val_str = json.dumps(value, ensure_ascii=False)
        cursor.execute("INSERT OR REPLACE INTO cache_store (cache_key, cache_value) VALUES (?, ?)", (key, val_str))
        conn.commit()
        conn.close()

    def cache_delete(self, key: str):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_store WHERE cache_key = ?", (key,))
        conn.commit()
        conn.close()

    # ==========================================
    # 4. RAG WRAPPER (CHROMA / FAISS WRAPPER)
    # ==========================================

    def add_document(self, document_path: str):
        """
        Nạp tệp quy chế pháp quy mới vào thư mục RAG và cập nhật lại vector database.
        """
        src = Path(document_path)
        if not src.exists():
            raise FileNotFoundError(f"Không tìm thấy file nguồn RAG: {document_path}")
            
        dst = Path(settings.LEGAL_DOCS_DIR) / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        import shutil
        shutil.copy2(src, dst)
        logger.info(f"Đã sao chép {src.name} vào kho văn bản RAG. Cập nhật lại chỉ mục...")
        self.rag_tool.build_index()

    def search_document(self, query: str, top_k: int = 4, domain_filter: str = None) -> str:
        """
        Wrapper tìm kiếm tri thức pháp quy từ RAG.
        """
        return self.rag_tool.retrieve_context(query, top_k=top_k, domain_filter=domain_filter)

    def delete_document(self, document_name: str):
        """
        Xóa tệp quy chế pháp lý khỏi kho RAG và xây dựng lại chỉ mục.
        """
        path = Path(settings.LEGAL_DOCS_DIR) / document_name
        if path.exists():
            path.unlink()
            logger.info(f"Đã xóa file {document_name} khỏi thư mục RAG. Cập nhật lại chỉ mục...")
            self.rag_tool.build_index()
        else:
            logger.warning(f"Không tìm thấy file {document_name} trong thư mục RAG để xóa.")
