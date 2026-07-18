import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple
from openai import OpenAI
from docxtpl import DocxTemplate

from config import settings
from src.hooks import AnonymizerHook, RedactionHook
from src.tools import DocParser, Standardizer, RuleEngine
from src.memory import ShortTermMemory, LongTermMemory


class AgenticReportAgent:
    def __init__(self):
        # 1. Khởi tạo các công cụ và hook
        self.parser = DocParser()
        self.standardizer = Standardizer()
        self.rule_engine = RuleEngine()
        
        self.anonymizer = AnonymizerHook()
        self.redaction = RedactionHook()
        
        self.short_memory = ShortTermMemory()
        self.long_memory = LongTermMemory()
        
        # 2. Khởi tạo OpenAI Client tương thích với FPT AI Factory
        self.client = OpenAI(
            api_key=settings.FPT_API_KEY,
            base_url=settings.FPT_BASE_URL
        )

    def _load_prompt(self, file_name: str) -> Tuple[str, str]:
        """
        Đọc system prompt và user prompt từ file YAML cấu hình.
        """
        path = Path(settings.PROMPTS_DIR) / file_name
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file prompt: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("system_prompt", ""), data.get("user_prompt", "")

    def _call_llm(self, system_prompt: str, user_prompt: str, response_format: str = "text") -> str:
        """
        Gọi mô hình ngôn ngữ lớn (Llama-3.3-70B-Instruct) qua FPT API.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # Định cấu hình response_format nếu yêu cầu JSON
        extra_args = {}
        if response_format == "json":
            extra_args["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0.1,  # Đặt nhiệt độ thấp để tăng tính chính xác của số liệu
            **extra_args
        )
        return response.choices[0].message.content

    def parse_template_schema(self, template_path: str) -> Dict[str, Any]:
        """
        Stage 1 & 2: Phân tích file Word mẫu trống và sinh ra Schema các trường cần điền.
        """
        # Đọc văn bản thô từ mẫu trống
        template_text = self.parser.parse(template_path)
        
        # Load prompt
        sys_p, user_p = self._load_prompt("template_parser.yaml")
        user_p = user_p.format(template_text=template_text)
        
        # Gọi LLM trích xuất Schema dạng JSON
        response_text = self._call_llm(sys_p, user_p, response_format="json")
        schema = json.loads(response_text)
        
        # Lưu schema vào bộ nhớ ngắn hạn
        self.short_memory.set_data("dynamic_schema", schema)
        return schema

    def extract_from_raw_inputs(self, schema: Dict[str, Any], raw_paths: List[str]) -> Dict[str, Any]:
        """
        Stage 2 & 3: Đọc tài liệu thô, chạy Hook ẩn danh, trích xuất số liệu và chuẩn hóa thực thể.
        """
        extracted_data = {}
        schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
        
        sys_p, user_p = self._load_prompt("raw_extractor.yaml")
        
        for path in raw_paths:
            # 1. Đọc văn bản thô
            raw_text = self.parser.parse(path)
            
            # 2. Chạy bộ lọc an toàn Redaction Hook
            is_safe, found_secrets = self.redaction.is_safe(raw_text)
            if not is_safe:
                # Nếu phát hiện từ khóa mật, che giấu trước khi gửi tới LLM Cloud
                raw_text = self.redaction.redact(raw_text)
            
            # 3. Chạy bộ ẩn danh Anonymization Hook
            masked_text, restore_map = self.anonymizer.anonymize(raw_text)
            
            # 4. Gửi LLM trích xuất
            formatted_user_p = user_p.format(
                dynamic_schema=schema_str,
                raw_document_text=masked_text
            )
            response_text = self._call_llm(sys_p, formatted_user_p, response_format="json")
            doc_data = json.loads(response_text)
            
            # 5. Khôi phục PII (De-anonymize) trước khi xử lý nội bộ
            for key, val in doc_data.items():
                if isinstance(val, str):
                    doc_data[key] = self.anonymizer.deanonymize(val, restore_map)
            
            # Gộp dữ liệu trích xuất được
            extracted_data.update(doc_data)
            
        # Lưu trữ tạm thời vào bộ nhớ ngắn hạn
        self.short_memory.set_data("raw_extracted_data", extracted_data)
        return extracted_data

    def run_validation_and_self_correction(self, data: Dict[str, Any], max_retries: int = 2) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Stage 4: Chạy Rule Engine và thực hiện Vòng lặp tự sửa lỗi (Self-Correction Loop).
        """
        current_data = data.copy()
        
        for attempt in range(max_retries + 1):
            is_valid, failures = self.rule_engine.validate(current_data)
            if is_valid or not failures:
                break
                
            # Nếu có lỗi nghiêm trọng (error) và chưa hết lượt thử, kích hoạt LLM tự phản hồi sửa sai
            error_failures = [f for f in failures if f["severity"] == "error"]
            if not error_failures or attempt == max_retries:
                break
                
            print(f"[Self-Correction] Phát hiện vi phạm công thức ở lượt thử {attempt+1}. Tiến hành tự lập luận sửa lỗi...")
            
            # Prompt tự lập luận sửa lỗi
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
            
            try:
                corrected_response = self._call_llm(correction_sys_prompt, correction_user_prompt, response_format="json")
                corrected_json = json.loads(corrected_response)
                # Ghi đè các giá trị đã sửa
                current_data.update(corrected_json)
            except Exception as e:
                print(f"[Self-Correction Error]: {str(e)}")
                break
                
        self.short_memory.set_data("final_kpi_data", current_data)
        return current_data, failures

    def generate_final_report(self, kpi_data: Dict[str, Any], template_path: str, output_path: str, rag_context: str = "") -> str:
        """
        Stage 6: Viết nhận xét và chèn dữ liệu trực tiếp vào tệp tin biểu mẫu trống.
        """
        # 1. Đọc văn phong thói quen từ bộ nhớ dài hạn
        style_preferences = self.long_memory.get_style_preferences()
        
        # 2. Sinh đoạn văn nhận xét bằng LLM
        sys_p, user_p = self._load_prompt("report_commenter.yaml")
        
        # Đưa thêm thói quen viết vào prompt nếu có
        style_str = ""
        if style_preferences:
            style_str = "\nThói quen văn phong ưa thích:\n" + "\n".join([f"- {k}: {v}" for k, v in style_preferences.items()])
            
        formatted_user_p = user_p.format(
            kpi_data=json.dumps(kpi_data, ensure_ascii=False, indent=2),
            rag_context=rag_context if rag_context else "Không có văn cảnh quy định cụ thể."
        )
        if style_str:
            formatted_user_p += style_str

        # Viết nhận xét
        remarks = self._call_llm(sys_p, formatted_user_p)
        
        # 3. Chuẩn bị ngữ cảnh điền mẫu Word
        # Gộp KPI và phần nhận xét tự động vào 1 từ điển
        render_context = kpi_data.copy()
        render_context["nhan_xet_ai"] = remarks
        
        # 4. Sử dụng docxtpl để đổ dữ liệu vào file Word nguyên bản
        doc = DocxTemplate(template_path)
        doc.render(render_context)
        
        # Lưu file báo cáo hoàn chỉnh
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(out_path)
        
        return remarks
