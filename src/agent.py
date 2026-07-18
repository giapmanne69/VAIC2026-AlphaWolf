import json
import yaml
import logging
import re
import io
from pathlib import Path
from typing import List, Dict, Any, Tuple, Generator
from openai import OpenAI
from docxtpl import DocxTemplate

from config import settings
from src.hooks import AnonymizerHook, RedactionHook
from src.tools import DocParser, Standardizer, RuleEngine, RAGSearchTool
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
            self.rag_search = RAGSearchTool()
            
            self.anonymizer = AnonymizerHook()
            self.redaction = RedactionHook()
            
            self.short_memory = ShortTermMemory()
            self.long_memory = LongTermMemory()
            
            self.client = OpenAI(
                api_key=settings.FPT_API_KEY,
                base_url=settings.FPT_BASE_URL
            )
            self.restore_maps = {}
            self.agent_state = {
                "schema": None,
                "kpi_data": {},
                "remarks": {},
                "raw_text_cache": {}
            }
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

    # --- PIPELINE STAGES (GIỮ CHO TƯƠNG THÍCH NGƯỢC) ---
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
            failures = []
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
    
            # Gọi LLM với định dạng JSON
            response_text = self._call_llm(sys_p, formatted_user_p, response_format="json")
            try:
                remarks_dict = json.loads(response_text)
            except Exception as e:
                logger.error(f"Không thể parse JSON từ phản hồi nhận xét. Thử dùng text thô làm mặc định: {str(e)}")
                remarks_dict = {
                    "nhan_xet_ai_kinh_te": response_text,
                    "nhan_xet_ai_van_hoa_xa_hoi": response_text,
                    "nhan_xet_ai_quoc_phong_an_ninh": response_text,
                    "nhan_xet_ai_phuong_huong": response_text
                }
            
            # Gom tất cả nhận xét thành 1 văn bản để hiển thị ở UI
            combined_remarks = (
                f"=== KHỐI KINH TẾ ===\n{remarks_dict.get('nhan_xet_ai_kinh_te', '')}\n\n"
                f"=== KHỐI VĂN HÓA - XÃ HỘI ===\n{remarks_dict.get('nhan_xet_ai_van_hoa_xa_hoi', '')}\n\n"
                f"=== KHỐI QUỐC PHÒNG - AN NINH ===\n{remarks_dict.get('nhan_xet_ai_quoc_phong_an_ninh', '')}\n\n"
                f"=== PHƯƠNG HƯỚNG KỲ TỚI ===\n{remarks_dict.get('nhan_xet_ai_phuong_huong', '')}"
            )
            
            # Gộp ngữ cảnh và ghi tệp Word
            render_context = kpi_data.copy()
            
            # Sửa lỗi in chữ None/null ra file Word
            for k, v in list(render_context.items()):
                if v is None or v == "None" or v == "null":
                    render_context[k] = ""
                    
            # Đưa toàn bộ các nhận xét riêng lẻ vào ngữ cảnh render
            render_context.update(remarks_dict)
            render_context["nhan_xet_ai"] = combined_remarks
            
            logger.info(f"Đang tiến hành điền mẫu với docxtpl...")
            doc = DocxTemplate(template_path)
            doc.render(render_context)
            
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            doc.save(out_path)
            
            logger.info(f"Lưu file Word thành công tại: {out_path}")
            return combined_remarks
        except Exception as e:
            logger.exception("Lỗi trong Stage 6 (generate_final_report):")
            raise e

    # --- AUTONOMOUS REACT AGENT UPGRADE ---
    def execute_agent_tool(self, tool_name: str, tool_input: Dict[str, Any], rag_context: str = "") -> Any:
        """
        Hộp công cụ nghiệp vụ (Tool Registry) của Tác tử AI.
        """
        logger.info(f"Tác tử gọi công cụ: {tool_name} với tham số: {tool_input}")
        
        if tool_name == "extract_schema_tool":
            template_path = tool_input.get("template_path")
            schema = self.parse_template_schema(template_path)
            self.agent_state["schema"] = schema
            return schema
            
        elif tool_name == "read_and_clean_raw_tool":
            file_path = tool_input.get("file_path")
            raw_text = self.parser.parse(file_path)
            
            is_safe, found_secrets = self.redaction.is_safe(raw_text)
            if not is_safe:
                raw_text = self.redaction.redact(raw_text)
                
            masked_text, restore_map = self.anonymizer.anonymize(raw_text)
            self.restore_maps[file_path] = restore_map
            self.agent_state["raw_text_cache"]["masked_text"] = masked_text
            return {
                "masked_text": masked_text,
                "restore_map_len": len(restore_map),
                "is_redacted": not is_safe
            }
            
        elif tool_name == "extract_kpis_tool":
            raw_text = tool_input.get("raw_text") or self.agent_state.get("raw_text_cache", {}).get("masked_text", "")
            schema = tool_input.get("schema") or self.agent_state.get("schema", {})
            
            sys_p, user_p = self._load_prompt("raw_extractor.yaml")
            formatted_user_p = user_p.format(
                dynamic_schema=json.dumps(schema, ensure_ascii=False),
                raw_document_text=raw_text
            )
            response = self._call_llm(sys_p, formatted_user_p, response_format="json")
            doc_data = json.loads(response)
            
            for file_path, restore_map in self.restore_maps.items():
                for k, v in list(doc_data.items()):
                    if isinstance(v, str):
                        doc_data[k] = self.anonymizer.deanonymize(v, restore_map)
            return doc_data
            
        elif tool_name == "validate_and_correct_tool":
            kpi_data = tool_input.get("kpi_data") or self.agent_state.get("kpi_data", {})
            is_valid, failures = self.rule_engine.validate(kpi_data)
            return {"is_valid": is_valid, "failures": failures}
            
        elif tool_name == "rag_search_tool":
            query = tool_input.get("query")
            domain = tool_input.get("domain")
            return self.rag_search.retrieve_context(query, domain_filter=domain)
            
        elif tool_name == "generate_section_remarks_tool":
            kpi_data = tool_input.get("kpi_data") or self.agent_state.get("kpi_data", {})
            sys_p, user_p = self._load_prompt("report_commenter.yaml")
            
            effective_rag_context = rag_context
            if not effective_rag_context:
                queries = ["chế độ báo cáo thông tư nghị định", "quy trình giải quyết khiếu nại tố cáo", "dân cư cư trú hộ tịch"]
                context_blocks = []
                for q in queries:
                    res = self.rag_search.retrieve_context(q, top_k=2)
                    if "Không tìm thấy" not in res:
                        context_blocks.append(res)
                effective_rag_context = "\n\n".join(context_blocks) if context_blocks else "Không có văn cảnh quy định cụ thể."

            formatted_user_p = user_p.format(
                kpi_data=json.dumps(kpi_data, ensure_ascii=False, indent=2),
                rag_context=effective_rag_context
            )
            response = self._call_llm(sys_p, formatted_user_p, response_format="json")
            return json.loads(response)
            
        elif tool_name == "render_docx_report_tool":
            template_path = tool_input.get("template_path")
            kpi_data = tool_input.get("kpi_data") or self.agent_state.get("kpi_data", {})
            remarks_dict = tool_input.get("remarks_dict") or self.agent_state.get("remarks", {})
            output_path = tool_input.get("output_path")
            
            combined_remarks = (
                f"=== KHỐI KINH TẾ ===\n{remarks_dict.get('nhan_xet_ai_kinh_te', '')}\n\n"
                f"=== KHỐI VĂN HÓA - XÃ HỘI ===\n{remarks_dict.get('nhan_xet_ai_van_hoa_xa_hoi', '')}\n\n"
                f"=== KHỐI QUỐC PHÒNG - AN NINH ===\n{remarks_dict.get('nhan_xet_ai_quoc_phong_an_ninh', '')}\n\n"
                f"=== PHƯƠNG HƯỚNG KỲ TỚI ===\n{remarks_dict.get('nhan_xet_ai_phuong_huong', '')}"
            )
            
            render_context = kpi_data.copy()
            for k, v in list(render_context.items()):
                if v is None or v == "None" or v == "null":
                    render_context[k] = ""
            render_context.update(remarks_dict)
            render_context["nhan_xet_ai"] = combined_remarks
            
            doc = DocxTemplate(template_path)
            doc.render(render_context)
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            doc.save(out_p)
            
            return {
                "status": "success",
                "output_path": output_path,
                "combined_remarks": combined_remarks
            }
        else:
            raise ValueError(f"Không tìm thấy công cụ nghiệp vụ: {tool_name}")

    def run_react_agent_generator(
        self, template_path: str, raw_paths: List[str], output_path: str, rag_context: str = ""
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Khởi chạy vòng lặp ReAct tự trị và sinh ra (yield) từng bước logs, thoughts, actions
        dưới dạng JSON string phục vụ Server-Sent Events (SSE) hiển thị tư duy AI lên React.
        """
        logger.info("BẮT ĐẦU VÒNG LẶP REACT AGENT TỰ TRỊ")
        
        sys_p, user_p = self._load_prompt("agent_react.yaml")
        formatted_user_p = user_p.format(
            template_path=template_path,
            raw_paths=json.dumps(raw_paths, ensure_ascii=False),
            output_path=output_path
        )
        
        history = [
            {"role": "system", "content": sys_p},
            {"role": "user", "content": formatted_user_p}
        ]
        
        step_counter = 1
        max_steps = 15
        
        # Biến số trạng thái toàn cục trong phiên chạy của Tác tử
        self.agent_state = {
            "schema": None,
            "kpi_data": {},
            "remarks": {},
            "raw_text_cache": {}
        }
        
        while step_counter <= max_steps:
            logger.info(f"Vòng lặp ReAct - Bước {step_counter}")
            
            # Gọi LLM để lấy bước suy nghĩ tiếp theo
            try:
                response = self.client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=history,
                    temperature=0.1,
                    max_tokens=4096
                )
                content = response.choices[0].message.content
                logger.info(f"LLM phản hồi: \n{content}")
            except Exception as e:
                logger.exception("Lỗi khi kết nối FPT AI Factory trong ReAct Loop:")
                yield {"status": "error", "message": f"Lỗi kết nối FPT AI Factory: {str(e)}"}
                return
                
            # Thêm phản hồi của LLM vào lịch sử hội thoại
            history.append({"role": "assistant", "content": content})
            
            # Parse nội dung phản hồi (Thought, Action, Action Input, Final Answer)
            thought = ""
            action = None
            action_input = {}
            final_answer = None
            
            thought_match = re.search(r"Thought:\s*(.*)", content, re.IGNORECASE)
            if thought_match:
                thought = thought_match.group(1).strip()
                
            action_match = re.search(r"Action:\s*(\w+)", content, re.IGNORECASE)
            action_input_match = re.search(r"Action Input:\s*(\{.*?\})", content, re.DOTALL)
            
            final_match = re.search(r"Final Answer:\s*(\{.*?\})", content, re.DOTALL)
            if not final_match:
                final_match = re.search(r"Final Answer:\s*(.*)", content, re.IGNORECASE)
                if final_match:
                    try:
                        final_answer = json.loads(final_match.group(1).strip())
                    except Exception:
                        final_answer = {"status": "success", "message": final_match.group(1).strip()}
            else:
                try:
                    final_answer = json.loads(final_match.group(1).strip())
                except Exception:
                    final_answer = {"status": "success"}

            # Trường hợp 1: Tác tử đưa ra Final Answer (Hoàn thành nhiệm vụ)
            if final_answer:
                if not isinstance(final_answer, dict):
                    final_answer = {"status": "success", "message": str(final_answer)}
                if "kpi_data" not in final_answer or not final_answer["kpi_data"]:
                    final_answer["kpi_data"] = self.agent_state["kpi_data"]
                if "combined_remarks" not in final_answer or not final_answer["combined_remarks"]:
                    rem = self.agent_state.get("remarks", {})
                    combined_remarks = (
                        f"=== KHỐI KINH TẾ ===\n{rem.get('nhan_xet_ai_kinh_te', '')}\n\n"
                        f"=== KHỐI VĂN HÓA - XÃ HỘI ===\n{rem.get('nhan_xet_ai_van_hoa_xa_hoi', '')}\n\n"
                        f"=== KHỐI QUỐC PHÒNG - AN NINH ===\n{rem.get('nhan_xet_ai_quoc_phong_an_ninh', '')}\n\n"
                        f"=== PHƯƠNG HƯỚNG KỲ TỚI ===\n{rem.get('nhan_xet_ai_phuong_huong', '')}"
                    )
                    final_answer["combined_remarks"] = combined_remarks
                yield {
                    "status": "completed",
                    "step": step_counter,
                    "thought": thought or "Tôi đã hoàn thành toàn bộ mục tiêu.",
                    "final_answer": final_answer
                }
                return
                
            # Trường hợp 2: Tác tử gọi công cụ
            if action_match and action_input_match:
                action = action_match.group(1).strip()
                try:
                    action_input = json.loads(action_input_match.group(1).strip())
                except Exception as e:
                    observation = f"Lỗi cú pháp JSON ở Action Input: {str(e)}"
                    history.append({"role": "user", "content": f"Observation: {observation}"})
                    yield {
                        "status": "running",
                        "step": step_counter,
                        "thought": thought,
                        "action": action,
                        "action_input": action_input_match.group(1).strip(),
                        "observation": observation
                    }
                    step_counter += 1
                    continue

                # Thực thi công cụ nghiệp vụ
                try:
                    observation_result = self.execute_agent_tool(action, action_input, rag_context)
                    
                    # Cập nhật trạng thái Agent để theo dõi
                    if action == "extract_schema_tool":
                        self.agent_state["schema"] = observation_result
                    elif action == "extract_kpis_tool":
                        self.agent_state["kpi_data"].update(observation_result)
                    elif action == "generate_section_remarks_tool":
                        self.agent_state["remarks"] = observation_result
                        
                    observation = json.dumps(observation_result, ensure_ascii=False)
                except Exception as e:
                    logger.exception(f"Lỗi khi thực thi công cụ {action}:")
                    observation = f"Lỗi thực thi công cụ {action}: {str(e)}"
                
                # Trả kết quả quan sát cho LLM ở lượt tiếp theo
                history.append({"role": "user", "content": f"Observation: {observation}"})
                
                yield {
                    "status": "running",
                    "step": step_counter,
                    "thought": thought,
                    "action": action,
                    "action_input": action_input,
                    "observation": observation
                }
            else:
                # Fallback: Nếu mô hình phản hồi không đúng ReAct format
                observation = "Hệ thống: Vui lòng sử dụng đúng định dạng ReAct (Thought, Action, Action Input hoặc Final Answer)."
                history.append({"role": "user", "content": f"Observation: {observation}"})
                yield {
                    "status": "running",
                    "step": step_counter,
                    "thought": content,
                    "action": "Không rõ",
                    "action_input": {},
                    "observation": observation
                }
                
            step_counter += 1
            
        yield {"status": "error", "message": "Vượt quá giới hạn bước suy nghĩ tối đa của Tác tử."}
