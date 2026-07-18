import json
import logging
import pickle
import re
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import pdfplumber
import docx
from openai import OpenAI

from config import settings

logger = logging.getLogger("RAGSearchTool")

class RAGSearchTool:
    def __init__(self):
        self.db_path = Path(settings.FAISS_DB_DIR) / "rag_store.pkl"
        self.docs_dir = Path(settings.LEGAL_DOCS_DIR)
        
        self.client = OpenAI(
            api_key=settings.FPT_API_KEY,
            base_url=settings.FPT_BASE_URL
        )
        self.chunks: List[Dict[str, Any]] = []
        self.vectors: np.ndarray = np.array([])
        
        # Tạo thư mục lưu DB nếu chưa có
        Path(settings.FAISS_DB_DIR).mkdir(parents=True, exist_ok=True)
        
        # Tự động nạp cơ sở dữ liệu nếu đã được build
        self.load_index()

    def load_index(self):
        """
        Nạp cơ sở dữ liệu và vector nhúng từ đĩa.
        """
        if self.db_path.exists():
            try:
                with open(self.db_path, "rb") as f:
                    data = pickle.load(f)
                    self.chunks = data.get("chunks", [])
                    self.vectors = np.array(data.get("vectors", []))
                logger.info(f"Đã nạp thành công RAG Database với {len(self.chunks)} phân đoạn.")
            except Exception as e:
                logger.error(f"Lỗi khi nạp RAG Database: {str(e)}")
        else:
            logger.info("Chưa có cơ sở dữ liệu RAG sẵn có. Cần chạy build_index().")

    def save_index(self):
        """
        Lưu cơ sở dữ liệu và vector nhúng lên đĩa.
        """
        try:
            with open(self.db_path, "wb") as f:
                pickle.dump({
                    "chunks": self.chunks,
                    "vectors": self.vectors.tolist()
                }, f)
            logger.info(f"Lưu cơ sở dữ liệu RAG thành công tại: {self.db_path}")
        except Exception as e:
            logger.error(f"Lỗi khi lưu RAG Database: {str(e)}")

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Trích xuất văn bản từ tệp PDF sử dụng pdfplumber.
        """
        text_list = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_list.append(f"[Trang {i+1}]\n{page_text}")
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất PDF {pdf_path.name}: {str(e)}")
        return "\n\n".join(text_list)

    def extract_text_from_docx(self, docx_path: Path) -> str:
        """
        Trích xuất văn bản từ tệp DOCX sử dụng python-docx.
        """
        text_list = []
        try:
            doc = docx.Document(docx_path)
            for p in doc.paragraphs:
                if p.text.strip():
                    text_list.append(p.text)
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                    if row_text:
                        text_list.append(row_text)
        except Exception as e:
            logger.error(f"Lỗi khi trích xuất DOCX {docx_path.name}: {str(e)}")
        return "\n".join(text_list)

    def chunk_text(self, text: str, doc_name: str, doc_type: str, domain: str) -> List[Dict[str, Any]]:
        """
        Phân mảnh văn bản thông minh (khoảng 800 ký tự mỗi chunk, gối đầu 150 ký tự).
        """
        chunks = []
        # Tách dòng
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        
        current_chunk = ""
        current_pages = set()
        chunk_idx = 0
        
        for p in paragraphs:
            # Tìm số trang nếu có dạng [Trang X]
            page_match = re.search(r"\[Trang (\d+)\]", p)
            if page_match:
                current_pages.add(int(page_match.group(1)))
                
            if len(current_chunk) + len(p) < 800:
                current_chunk += "\n" + p
            else:
                if current_chunk.strip():
                    chunks.append({
                        "chunk_id": f"{doc_name}_chunk_{chunk_idx}",
                        "document_name": doc_name,
                        "document_type": doc_type,
                        "domain": domain,
                        "chunk_index": chunk_idx,
                        "content": current_chunk.strip(),
                        "pages": list(current_pages)
                    })
                    chunk_idx += 1
                # Gối đầu một chút từ đoạn hiện tại
                current_chunk = p
                current_pages = set()
                if page_match:
                    current_pages.add(int(page_match.group(1)))
                    
        # Phần dư thừa cuối cùng
        if current_chunk.strip():
            chunks.append({
                "chunk_id": f"{doc_name}_chunk_{chunk_idx}",
                "document_name": doc_name,
                "document_type": doc_type,
                "domain": domain,
                "chunk_index": chunk_idx,
                "content": current_chunk.strip(),
                "pages": list(current_pages)
            })
            
        return chunks

    def build_index(self) -> int:
        """
        Quét thư mục data/rag/legal_docs, trích xuất, phân mảnh và nhúng vector qua FPT API.
        """
        logger.info("Đang khởi chạy xây dựng cơ sở dữ liệu RAG...")
        self.chunks = []
        vectors_list = []
        
        # Quét tất cả các file trong thư mục tri thức pháp luật
        for filepath in self.docs_dir.rglob("*"):
            if not filepath.is_file():
                continue
            suffix = filepath.suffix.lower()
            if suffix not in [".pdf", ".docx"]:
                continue
                
            # Xác định domain và loại tài liệu từ thư mục cha
            domain = "common_reporting"
            if "population" in filepath.parts or "dân cư" in str(filepath).lower():
                domain = "population"
            elif "complaint" in filepath.parts or "khiếu nại" in str(filepath).lower():
                domain = "complaints"
            elif "task" in filepath.parts or "nhiệm vụ" in str(filepath).lower():
                domain = "tasks"
                
            doc_type = "legal_document"
            if "guideline" in str(filepath).lower() or "hướng dẫn" in str(filepath).lower():
                doc_type = "reporting_guideline"
            elif "template" in str(filepath).lower() or "biểu mẫu" in str(filepath).lower():
                doc_type = "report_template"

            logger.info(f"Đang xử lý tệp: {filepath.name} (Domain: {domain}, Loại: {doc_type})")
            
            # Trích xuất văn bản
            if suffix == ".pdf":
                text = self.extract_text_from_pdf(filepath)
            else:
                text = self.extract_text_from_docx(filepath)
                
            if not text.strip():
                continue
                
            # Phân mảnh
            doc_chunks = self.chunk_text(text, filepath.name, doc_type, domain)
            self.chunks.extend(doc_chunks)
            logger.info(f"Tạo ra {len(doc_chunks)} phân đoạn từ {filepath.name}.")
            
        if not self.chunks:
            logger.warning("Không tìm thấy tệp tin tri thức hợp lệ để lập chỉ mục.")
            return 0
            
        # Gọi API nhúng vector cho từng phân đoạn theo lô để tránh vượt giới hạn token
        logger.info(f"Đang sinh vector nhúng cho {len(self.chunks)} phân đoạn bằng API FPT...")
        batch_size = 16
        
        for i in range(0, len(self.chunks), batch_size):
            batch = self.chunks[i:i+batch_size]
            texts = [item["content"] for item in batch]
            try:
                response = self.client.embeddings.create(
                    model=settings.EMBEDDING_MODEL,
                    input=texts
                )
                # Đọc vector nhúng từ response
                for idx, embedding_item in enumerate(response.data):
                    vectors_list.append(embedding_item.embedding)
            except Exception as e:
                logger.error(f"Lỗi gọi API nhúng vector tại lô {i}: {str(e)}")
                # Điền vector rỗng nếu bị lỗi để không lệch index
                dummy_vector = [0.0] * 1024  # default dimension của multilingual-e5
                for _ in range(len(batch)):
                    vectors_list.append(dummy_vector)
                    
        self.vectors = np.array(vectors_list, dtype=np.float32)
        self.save_index()
        return len(self.chunks)

    def search(self, query: str, top_k: int = 5, domain_filter: str = None) -> List[Dict[str, Any]]:
        """
        Tìm kiếm tương đồng Cosine Similarity trên cơ sở dữ liệu local.
        """
        if not self.chunks or self.vectors.size == 0:
            logger.warning("Cơ sở dữ liệu RAG rỗng. Đang tự động chạy build_index()...")
            count = self.build_index()
            if count == 0:
                return []
                
        try:
            # Nhúng vector truy vấn
            response = self.client.embeddings.create(
                model=settings.EMBEDDING_MODEL,
                input=[query]
            )
            query_vector = np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"Lỗi khi nhúng câu truy vấn RAG: {str(e)}")
            return []
            
        # Tính khoảng cách Cosine
        # Cosine similarity = dot(A, B) / (norm(A) * norm(B))
        dot_products = np.dot(self.vectors, query_vector)
        norms_vectors = np.linalg.norm(self.vectors, axis=1)
        norm_query = np.linalg.norm(query_vector)
        
        # Tránh lỗi chia cho 0
        norms_vectors[norms_vectors == 0] = 1e-9
        if norm_query == 0:
            norm_query = 1e-9
            
        scores = dot_products / (norms_vectors * norm_query)
        
        # Xếp hạng kết quả
        ranked_indices = np.argsort(scores)[::-1]
        
        results = []
        for idx in ranked_indices:
            chunk = self.chunks[idx]
            
            # Áp dụng bộ lọc lọc domain nếu có
            if domain_filter and chunk["domain"] != domain_filter:
                continue
                
            score = float(scores[idx])
            results.append({
                "chunk_id": chunk["chunk_id"],
                "document_name": chunk["document_name"],
                "document_type": chunk["document_type"],
                "domain": chunk["domain"],
                "content": chunk["content"],
                "pages": chunk["pages"],
                "score": score
            })
            
            if len(results) >= top_k:
                break
                
        return results

    def retrieve_context(self, query: str, top_k: int = 4, domain_filter: str = None) -> str:
        """
        Trả về ngữ cảnh dạng văn bản đã format đẹp đẽ để chèn vào Prompt của LLM.
        """
        results = self.search(query, top_k=top_k, domain_filter=domain_filter)
        if not results:
            return "Không tìm thấy văn bản quy chế quy định hành chính nào liên quan."
            
        context_parts = []
        for i, res in enumerate(results):
            pages_str = f", Trang: {res['pages']}" if res['pages'] else ""
            context_parts.append(
                f"[Tài liệu tham khảo {i+1}]: {res['document_name']} (Lĩnh vực: {res['domain']}{pages_str})\n"
                f"Nội dung quy định:\n{res['content']}\n"
                f"----------------------------------------"
            )
        return "\n\n".join(context_parts)
