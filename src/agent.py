import json
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from openai import OpenAI
from docxtpl import DocxTemplate

from config import settings
from src.hooks import AnonymizerHook, RedactionHook
from src.tools import DocParser, Standardizer, RuleEngine
from src.memory import ShortTermMemory, LongTermMemory

# Đảm bảo thư mục data/ đã được khởi tạo
Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)

# Cấu hình logging ghi file agent_execution.log tiếng Việt UTF-8
logging.basicConfig(
    filename=str(Path(settings.DATA_DIR) / "agent_execution.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("AgenticReportAgent")


class AgenticReportAgent:
    def __init__(self):
        logger.info("Khởi tạo AgenticReportAgent và các công cụ bổ trợ.")
        try:
            self.parser = DocParser()
            self.standardizer = Standardizer()
            self.rule_engine = RuleEngine()
            
            self.anonymizer = AnonymizerHook()
            self.redaction = RedactionHook()
            
            self.short_memory = ShortTermMemory()
            self.long_memory = LongTermMemory()
            
            self.client = OpenAI(
                api_key=settings.FPT_API_KEY,
                base_url=settings.FPT_BASE_URL
            )
            logger.info("Khởi tạo thành công OpenAI Client kết nối FPT AI Factory.")
        except Exception as e:
            logger.exception("Lỗi khi khởi tạo AgenticReportAgent:")
            raise e

    def _load_prompt(self, file_name: str) -> Tuple[str, str]:
        """
        Đọc system prompt và user prompt từ file YAML cấu hình.
        """
        path = Path(settings.PROMPTS_DIR) / file_name
        if not path.exists():
            logger.error(f"Không tìm thấy file prompt tại đường dẫn: {path}")
            raise FileNotFoundError(f"Không tìm thấy file prompt: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("system_prompt", ""), data.get("user_prompt", "")

    def _call_llm(self, system_prompt: str, user_prompt: str, response_format: str = "text") -> str:
        """
        Gọi mô hình ngôn ngữ lớn (Llama-3.3-70B-Instruct) qua FPT API.
        """
        logger.info(f"Đang gửi yêu cầu tới mô hình LLM ({settings.LLM_MODEL})...")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        extra_args = {}
        if response_format == "json":
            extra_args["response_format"] = {"type": "json_object"}

        try:
            response = self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                temperature=0.1,
                **extra_args
            )
            content = response.choices[0].message.content
            logger.info("Gọi LLM thành công, nhận phản hồi từ API.")
            return content
        except Exception as e:
            logger.exception("Lỗi xảy ra trong quá trình gọi API LLM:")
            raise e

    def parse_template_schema(self, template_path: str) -> Dict[str, Any]:
        """
        Stage 1 & 2: Phân tích file Word mẫu trống và sinh ra Schema các trường cần điền.
        """
        logger.info(f"[Stage 1] Bắt đầu phân tích biểu mẫu trống tại: {template_path}")
        try:
            template_text = self.parser.parse(template_path)
            sys_p, user_p = self._load_prompt("template_parser.yaml")
            user_p = user_p.format(template_text=template_text)
            
            response_text = self._call_llm(sys_p, user_p, response_format="json")
            schema = json.loads(response_text)
            
            self.short_memory.set_data("dynamic_schema", schema)
            logger.info(f"[Stage 1] Phân tích Schema thành công. Số lượng biến phát hiện: {len(schema.get('variables', []))}")
            return schema
        except Exception as e:
            logger.exception("Lỗi trong Stage 1 (parse_template_schema):")
            raise e

    def extract_from_raw_inputs(self, schema: Dict[str, Any], raw_paths: List[str]) -> Dict[str, Any]:
        """
        Stage 2 & 3: Đọc tài liệu thô, chạy Hook ẩn danh, trích xuất số liệu và chuẩn hóa thực thể.
        """
        logger.info(f"[Stage 2 & 3] Bắt đầu trích xuất số liệu từ {len(raw_paths)} file nguồn.")
        extracted_data = {}
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
        sys_p, user_p = self._load_prompt("raw_extractor.yaml")
        
        try:
            for path in raw_paths:
                logger.info(f"Đang xử lý file thô: {Path(path).name}")
                raw_text = self.parser.parse(path)
                
                # Check từ khóa mật
                is_safe, found_secrets = self.redaction.is_safe(raw_text)
                if not is_safe:
                    logger.warning(f"Phát hiện {len(found_secrets)} từ khóa mật trong file {Path(path).name}. Tiến hành che giấu.")
                    raw_text = self.redaction.redact(raw_text)
                
                # Ẩn danh PII
                masked_text, restore_map = self.anonymizer.anonymize(raw_text)
                logger.info(f"Đã ẩn danh PII. Số lượng khóa khôi phục: {len(restore_map)}")
                
                formatted_user_p = user_p.format(
                    dynamic_schema=schema_str,
                    raw_document_text=masked_text
                )
                
                response_text = self._call_llm(sys_p, formatted_user_p, response_format="json")
                doc_data = json.loads(response_text)
                
                # De-anonymize
                for key, val in doc_data.items():
                    if isinstance(val, str):
                        doc_data[key] = self.anonymizer.deanonymize(val, restore_map)
                
                extracted_data.update(doc_data)
                
            self.short_memory.set_data("raw_extracted_data", extracted_data)
            logger.info("Trích xuất số liệu thô hoàn tất.")
            return extracted_data
        except Exception as e:
            logger.exception("Lỗi trong Stage 2 & 3 (extract_from_raw_inputs):")
            raise e

    def run_validation_and_self_correction(self, data: Dict[str, Any], max_retries: int = 2) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Stage 4: Chạy Rule Engine và thực hiện Vòng lặp tự sửa lỗi (Self-Correction Loop).
        """
        logger.info("[Stage 4] Khởi động bộ kiểm chéo và tự sửa lỗi số liệu.")
        current_data = data.copy()
        
        try:
            for attempt in range(max_retries + 1):
                is_valid, failures = self.rule_engine.validate(current_data)
                logger.info(f"Lượt thử {attempt}: Hợp lệ={is_valid}, Số quy tắc lỗi={len(failures)}")
                
                if is_valid or not failures:
                    break
                    
                error_failures = [f for f in failures if f["severity"] == "error"]
                if not error_failures or attempt == max_retries:
                    break
                    
                logger.warning(f"Phát hiện lỗi nghiêm trọng (error) ở lượt {attempt}. Đang kích hoạt Self-Correction Loop...")
                
                correction_sys_prompt = (
                    "Bạn là một kiểm soát viên số liệu. Nhiệm vụ của bạn là sửa lại các lỗi mâu thuẫn số liệu "
                    "dựa trên bảng báo cáo lỗi và dữ liệu thô hiện tại. Chỉ trả về đối tượng JSON chứa các trường số liệu được sửa đổi."
                )
                correction_user_prompt = f"""
                ### Dữ liệu hiện tại:
                {json.dumps(current_data, ensure_ascii=False, indent=2)}
    
                ### Lỗi phát hiện:
                {json.dumps(error_failures, ensure_ascii=False, indent=2)}
    
                Hãy phân tích logic và trả về JSON chứa các giá trị đúng đã được sửa lại.
                """
                
                corrected_response = self._call_llm(correction_sys_prompt, correction_user_prompt, response_format="json")
                corrected_json = json.loads(corrected_response)
                logger.info(f"LLM phản hồi các trường sửa đổi: {corrected_json}")
                current_data.update(corrected_json)
                
            self.short_memory.set_data("final_kpi_data", current_data)
            logger.info("Hoàn tất Stage 4.")
            return current_data, failures
        except Exception as e:
            logger.exception("Lỗi trong Stage 4 (run_validation_and_self_correction):")
            raise e

    def generate_final_report(self, kpi_data: Dict[str, Any], template_path: str, output_path: str, rag_context: str = "") -> str:
        """
        Stage 6: Viết nhận xét và chèn dữ liệu trực tiếp vào tệp tin biểu mẫu trống.
        """
        logger.info(f"[Stage 6] Bắt đầu sinh nhận định báo cáo. Path đầu ra: {output_path}")
        try:
            style_preferences = self.long_memory.get_style_preferences()
            sys_p, user_p = self._load_prompt("report_commenter.yaml")
            
            style_str = ""
            if style_preferences:
                style_str = "\nThói quen văn phong ưa thích:\n" + "\n".join([f"- {k}: {v}" for k, v in style_preferences.items()])
                
            formatted_user_p = user_p.format(
                kpi_data=json.dumps(kpi_data, ensure_ascii=False, indent=2),
                rag_context=rag_context if rag_context else "Không có văn cảnh quy định cụ thể."
            )
            if style_str:
                formatted_user_p += style_str
    
            remarks = self._call_llm(sys_p, formatted_user_p)
            
            # Gộp ngữ cảnh và ghi tệp Word
            render_context = kpi_data.copy()
            render_context["nhan_xet_ai"] = remarks
            
            logger.info(f"Đang tiến hành điền mẫu với docxtpl...")
            doc = DocxTemplate(template_path)
            doc.render(render_context)
            
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(out_path)
            
            logger.info(f"Lưu file Word thành công tại: {out_path}")
            return remarks
        except Exception as e:
            logger.exception("Lỗi trong Stage 6 (generate_final_report):")
            raise e
