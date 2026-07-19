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
from src.tools.memory_manager import MemoryManager
from src.tools.population_bundle import PopulationWorkbookExtractor, PopulationBundleStandardizer
from src.memory import ShortTermMemory, LongTermMemory

# Đảm bảo thư mục data/ đã được khởi tạo
Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)

# Cấu hình logging ghi file agent_execution.log tiếng Việt UTF-8
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.DATA_DIR / "agent_execution.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
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
            self.memory_manager = MemoryManager()
            self.population_extractor = PopulationWorkbookExtractor()
            self.population_standardizer = PopulationBundleStandardizer()
            
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
                "raw_text_cache": {},
                "file_period_labels": {},
                "target_report_period": settings.TARGET_REPORT_PERIOD or "Tuần 3",
                "numerical_accumulator": {},
                "textual_accumulator": {},
                "extraction_conflicts": []
            }
            self.session_id = None
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
                temperature=settings.LLM_TEMPERATURE,
                **extra_args
            )
            content = response.choices[0].message.content
            logger.info("Gọi LLM thành công, nhận phản hồi từ API.")
            return content
        except Exception as e:
            logger.exception("Lỗi xảy ra trong quá trình gọi API LLM:")
            raise e

    def _scan_template_placeholders(self, template_text: str) -> Dict[str, Any]:
        pattern = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}|\[([^\[\]]+?)\]")
        variables = []
        seen = set()

        for line in (template_text or "").splitlines():
            for match in pattern.finditer(line):
                name = match.group(1) or match.group(2)
                if not name:
                    continue
                canonical = re.sub(r"[^\w]+", "_", name.strip().lower(), flags=re.UNICODE).strip("_")
                if not canonical or canonical in seen:
                    continue
                seen.add(canonical)
                variables.append({
                    "name": canonical,
                    "description": "",
                    "type": "string"
                })

        return {"variables": variables}

    def _validate_schema(self, schema: Any) -> bool:
        if not isinstance(schema, dict) or "variables" not in schema:
            return False
        if not isinstance(schema["variables"], list):
            return False
        for variable in schema["variables"]:
            if not isinstance(variable, dict):
                return False
            name = variable.get("name")
            var_type = variable.get("type")
            if not isinstance(name, str) or not name.strip():
                return False
            if var_type not in ("number", "string"):
                return False
        return True

    def _find_schema_variable(self, schema: Dict[str, Any], name: str) -> Dict[str, Any]:
        if not isinstance(schema, dict):
            return {}
        for variable in schema.get("variables", []):
            if isinstance(variable, dict) and variable.get("name") == name:
                return variable
        return {}

    def _get_schema_field_names(self, schema: Dict[str, Any]) -> List[str]:
        if not isinstance(schema, dict):
            return []
        return [var["name"] for var in schema.get("variables", []) if isinstance(var, dict) and var.get("name")]

    def _get_numeric_schema_fields(self, schema: Dict[str, Any]) -> List[str]:
        if not isinstance(schema, dict):
            return []
        return [var["name"] for var in schema.get("variables", []) if isinstance(var, dict) and var.get("type") == "number"]

    def _get_textual_schema_fields(self, schema: Dict[str, Any]) -> List[str]:
        if not isinstance(schema, dict):
            return []
        return [var["name"] for var in schema.get("variables", []) if isinstance(var, dict) and var.get("type") != "number"]

    def _is_period_variable(self, name: str) -> bool:
        if not isinstance(name, str):
            return False
        lower = name.lower()
        return any(tok in lower for tok in ["ky_bao_cao", "bao_cao", "period", "report", "thoi_gian"])

    def _normalize_string_to_number(self, value: str) -> Any:
        if value is None or not isinstance(value, str):
            return None
        match = re.search(r"(\d+)\s*hộ.*?(\d+)\s*nhân khẩu", value, re.IGNORECASE)
        if match:
            return int(match.group(2))

        match = re.search(r"(\d+)\s*nhân khẩu", value, re.IGNORECASE)
        if match:
            return int(match.group(1))

        match = re.search(r"(\d+)\s*hộ", value, re.IGNORECASE)
        if match:
            return int(match.group(1)) * 3

        digits = re.findall(r"\d+", value)
        if digits:
            return int(digits[-1])

        try:
            return int(float(value.replace(",", "")))
        except Exception:
            return None

    # --- PIPELINE STAGES (GIỮ CHO TƯƠNG THÍCH NGƯỢC) ---
    def parse_template_schema(self, template_path: str) -> Dict[str, Any]:
        """
        Stage 1 & 2: Phân tích file Word mẫu trống và sinh ra Schema các trường cần điền.
        """
        logger.info(f"[Stage 1] Bắt đầu phân tích biểu mẫu trống tại: {template_path}")
        try:
            template_text = self.parser.parse(template_path)
            schema = self._scan_template_placeholders(template_text)
            sys_p, user_p = self._load_prompt("template_parser.yaml")
            user_p = user_p.format(template_text=template_text)
            response_text = self._call_llm(sys_p, user_p, response_format="json")
            try:
                parsed_schema = json.loads(response_text)
                if self._validate_schema(parsed_schema):
                    schema = parsed_schema
                else:
                    logger.warning("Schema trả về từ LLM không hợp lệ. Giữ schema placeholder thô từ template.")
            except Exception as e:
                logger.warning(f"Không thể parse schema JSON từ LLM: {e}. Giữ schema placeholder thô từ template.")

            self.short_memory.set_data("dynamic_schema", schema)
            self.agent_state["schema"] = schema
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
                    target_report_period=self.agent_state.get("target_report_period", ""),
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

    def extract_kpis_for_file(self, file_path: str, schema: Dict[str, Any] = None) -> Dict[str, Any]:
        """Trích xuất KPI riêng cho một file thô."""
        if not file_path:
            raise ValueError("file_path là bắt buộc để trích xuất KPI từng file.")
        schema = schema or self.agent_state.get("schema", {})
        raw_text = self.agent_state.get("raw_text_cache", {}).get(file_path)
        if raw_text is None:
            if Path(file_path).exists():
                raw_text = self.parser.parse(file_path)
            else:
                raise FileNotFoundError(f"Không tìm thấy file raw để trích xuất: {file_path}")

        if Path(file_path).suffix.lower() in {".xlsx", ".xls"}:
            try:
                extracted_source = self.population_extractor.extract(Path(file_path), Path(file_path).name)
                standardized = self.population_standardizer.standardize([extracted_source])
                return standardized["values"]
            except Exception as exc:
                logger.warning(f"Không thể dùng population bundle extractor cho {file_path}: {exc}")

        try:
            sys_p, user_p = self._load_prompt("subagent_file_extractor.yaml")
        except FileNotFoundError:
            sys_p, user_p = self._load_prompt("raw_extractor.yaml")

        formatted_user_p = user_p.format(
            dynamic_schema=json.dumps(schema, ensure_ascii=False),
            raw_document_text=raw_text,
            target_report_period=self.agent_state.get("target_report_period", "")
        )
        response = self._call_llm(sys_p, formatted_user_p, response_format="json")
        doc_data = json.loads(response)
        doc_data = self._normalize_subagent_extraction_result(doc_data, schema)

        restore_map = self.restore_maps.get(file_path, {})
        for k, v in list(doc_data.items()):
            if isinstance(v, str):
                doc_data[k] = self.anonymizer.deanonymize(v, restore_map)

        doc_data = self._normalize_synonym_keys(doc_data, schema)
        for k, v in list(doc_data.items()):
            doc_data[k] = self._normalize_entity_value(k, v, schema)

        doc_data = self._ensure_subagent_output_shape(file_path, doc_data, raw_text, schema)
        return doc_data

    def _normalize_subagent_extraction_result(self, doc_data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(doc_data, dict):
            if "variables" in doc_data and isinstance(doc_data["variables"], list):
                normalized = {}
                for item in doc_data["variables"]:
                    if not isinstance(item, dict):
                        continue
                    name = item.get("name") or item.get("field") or item.get("key")
                    value = item.get("value") if "value" in item else item.get("data") or item.get("text") or item.get("result")
                    if name is not None:
                        normalized[name] = value
                return normalized

            if "result" in doc_data and isinstance(doc_data["result"], dict):
                return doc_data["result"]
            if "data" in doc_data and isinstance(doc_data["data"], dict):
                return doc_data["data"]

            fallback_flat = {}
            for key, value in doc_data.items():
                if isinstance(value, (str, int, float, bool)):
                    fallback_flat[key] = value
            if fallback_flat:
                return fallback_flat

            return {key: value for key, value in doc_data.items() if not isinstance(value, (list, dict))}

        if isinstance(doc_data, list):
            normalized = {}
            for item in doc_data:
                if not isinstance(item, dict):
                    continue
                name = item.get("name") or item.get("field") or item.get("key")
                value = item.get("value") if "value" in item else item.get("data") or item.get("text") or item.get("result")
                if name is not None:
                    normalized[name] = value
            return normalized

        return {}

    def _normalize_synonym_keys(self, doc_data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(doc_data, dict) or not isinstance(schema, dict):
            return doc_data

        canonical = {var["name"]: var for var in schema.get("variables", []) if isinstance(var, dict)}
        synonym_map = {
            "thuong_tru_moi": ["khai sinh moi", "tre em moi sinh", "nhap khau", "chuyen den sinh song chinh thuc"],
            "xoa_thuong_tru": ["khai tu", "cu gia mat", "cat khau", "chuyen di tinh khac", "chuyen di nuoc ngoai dinh cu"]
        }

        normalized = {}
        for key, value in doc_data.items():
            if key in canonical:
                normalized[key] = value
                continue

            lower_key = str(key).strip().lower()
            mapped = None
            for canonical_name, synonyms in synonym_map.items():
                if canonical_name == lower_key or any(s in lower_key for s in synonyms):
                    mapped = canonical_name
                    break

            if mapped and mapped not in normalized:
                normalized[mapped] = value
            else:
                normalized[key] = value

        return normalized

    def _normalize_entity_value(self, key: str, value: Any, schema: Dict[str, Any]) -> Any:
        if value is None or not isinstance(value, str):
            return value

        if self._find_schema_variable(schema, key).get("type") == "number":
            normalized = self._normalize_string_to_number(value)
            return normalized if normalized is not None else value

        return value

    def _ensure_subagent_output_shape(self, file_path: str, doc_data: Dict[str, Any], raw_text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(doc_data, dict):
            doc_data = {}

        file_name = Path(file_path).name
        result: Dict[str, Any] = {"file_name": file_name}

        def int_or_none(value):
            if value is None or value == "":
                return None
            try:
                return int(value)
            except Exception:
                try:
                    return int(float(str(value).replace(",", "")))
                except Exception:
                    return None

        for variable in schema.get("variables", []):
            if not isinstance(variable, dict):
                continue
            name = variable.get("name")
            if not name:
                continue

            if name in doc_data:
                value = doc_data[name]
                if variable.get("type") == "number":
                    result[name] = int_or_none(value)
                else:
                    result[name] = str(value).strip() if isinstance(value, str) else value
                continue

            if self._is_period_variable(name):
                period_label = self._infer_file_period_label(raw_text, file_name)
                if period_label == "Kỳ_Tuần":
                    result[name] = "Tuần 3"
                elif period_label == "Kỳ_Tháng":
                    result[name] = "Tháng"
                else:
                    result[name] = ""
                continue

            if variable.get("type") == "number":
                result[name] = None
            else:
                result[name] = ""

        return result

    def _infer_file_period_label(self, raw_text: str, file_name: str = "") -> str:
        raw_lower = (raw_text or "").lower()
        filename_lower = (file_name or "").lower()
        week_pattern = ["tuần 3", "tuan 3", "tuần", "tuan"]
        month_pattern = ["tháng", "thang"]

        if any(token in filename_lower for token in week_pattern):
            return "Kỳ_Tuần"
        if any(token in filename_lower for token in month_pattern):
            return "Kỳ_Tháng"

        if any(token in raw_lower for token in week_pattern):
            return "Kỳ_Tuần"
        if any(token in raw_lower for token in month_pattern):
            return "Kỳ_Tháng"

        return "unknown"

    def _subagent_cross_check_needs_rerun(self, extracted: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        if not isinstance(extracted, dict) or not isinstance(schema, dict):
            return False

        numeric_fields = self._get_numeric_schema_fields(schema)
        if not numeric_fields:
            return False

        has_nonzero_numeric = False
        for field in numeric_fields:
            value = extracted.get(field)
            numeric_value = self._normalize_number(value)
            if numeric_value not in (None, 0):
                has_nonzero_numeric = True
                break

        if has_nonzero_numeric:
            return False

        combined_text = " ".join(
            str(value).lower() for key, value in extracted.items() if isinstance(value, str)
        )
        if any(keyword in combined_text for keyword in ["xử phạt", "tiền phạt", "phạt", "xuly phat", "xu phat"]):
            return True

        return False

    def _merge_textual_fields(self, extraction_results: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, str]:
        text_fields = self._get_textual_schema_fields(schema)
        summaries = {field: [] for field in text_fields}
        seen = {field: set() for field in text_fields}

        for result in extraction_results:
            for field in text_fields:
                value = str(result.get(field, "")).strip()
                if not value:
                    continue
                if value not in seen[field]:
                    seen[field].add(value)
                    summaries[field].append(value)

        return {
            field: ("\n- " + "\n- ".join(values)) if values else ""
            for field, values in summaries.items()
        }

    def merge_extracted_kpi_results(self, extraction_results: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Gộp kết quả trích xuất KPI từ nhiều file theo priority-first và thu thập conflict."""
        merged_data: Dict[str, Any] = {}
        conflicts: List[Dict[str, Any]] = []

        if not extraction_results:
            return merged_data, conflicts

        valid_results = [r for r in extraction_results if not r.get("_out_of_scope", False)]
        out_of_scope_files = [r.get("_source_file") for r in extraction_results if r.get("_out_of_scope", False)]
        if out_of_scope_files:
            logger.info(f"Các file bị loại khỏi gộp do nằm ngoài phạm vi thời gian: {out_of_scope_files}")

        if not valid_results:
            valid_results = extraction_results

        schema = self.agent_state.get("schema", {})
        numeric_fields = set(self._get_numeric_schema_fields(schema))
        text_fields = set(self._get_textual_schema_fields(schema))
        period_field = next((field for field in self._get_schema_field_names(schema) if self._is_period_variable(field)), None)
        has_period_var = period_field is not None

        weekly_results = [r for r in valid_results if has_period_var and str(r.get(period_field, "")).strip().lower() == "tuần 3"]
        monthly_results = [r for r in valid_results if has_period_var and str(r.get(period_field, "")).strip().lower() == "tháng"]

        if has_period_var and weekly_results and len(weekly_results) != len(valid_results):
            logger.info("Loại bỏ các kết quả không phải Kỳ Tuần 3 trước khi tổng hợp.")
            valid_results = weekly_results
        elif has_period_var and not weekly_results and monthly_results:
            logger.info("Không tìm thấy kết quả Tuần 3; tiếp tục với các kết quả Kỳ Tháng.")
            valid_results = monthly_results

        for result in valid_results:
            source_file = result.get("_source_file")
            period_label = result.get("_period_label", "unknown")
            for key, value in result.items():
                if key.startswith("_") or key in {"file_name", period_field}:
                    continue
                if value is None or value == "" or value == "null":
                    continue

                if key in numeric_fields:
                    numeric_value = self._normalize_number(value)
                    if numeric_value is not None:
                        merged_data[key] = merged_data.get(key, 0) + numeric_value
                    else:
                        if key not in merged_data:
                            merged_data[key] = value
                        elif str(merged_data[key]) != str(value):
                            conflicts.append({
                                "key": key,
                                "existing_value": merged_data[key],
                                "new_value": value,
                                "source_file": source_file,
                                "period_label": period_label
                            })
                elif key in text_fields:
                    continue
                else:
                    if key not in merged_data:
                        merged_data[key] = value
                    else:
                        existing_value = merged_data[key]
                        if existing_value is None or existing_value == "" or existing_value == "null":
                            merged_data[key] = value
                        elif str(existing_value) != str(value):
                            conflicts.append({
                                "key": key,
                                "existing_value": existing_value,
                                "new_value": value,
                                "source_file": source_file,
                                "period_label": period_label
                            })

        merged_data.update(self._merge_textual_fields(valid_results, schema))

        if has_period_var and (period_field not in merged_data or merged_data.get(period_field) in [None, "", "unknown"]):
            if weekly_results:
                merged_data[period_field] = "Tuần 3"
            elif monthly_results:
                merged_data[period_field] = "Tháng"

        return merged_data, conflicts

    def _normalize_number(self, value: Any) -> Any:
        if value is None:
            return None
        try:
            if isinstance(value, str):
                value = value.replace(".", "").replace(",", "")
            if isinstance(value, float) or isinstance(value, int):
                return value
            return int(value)
        except Exception:
            try:
                return float(value)
            except Exception:
                return None

    def accumulate_numerical_values(self, extracted_data: Dict[str, Any]) -> None:
        accumulator = self.agent_state.get("numerical_accumulator", {})
        numeric_fields = set(self._get_numeric_schema_fields(self.agent_state.get("schema", {})))
        for key, value in extracted_data.items():
            if key in numeric_fields:
                numeric_value = self._normalize_number(value)
                if numeric_value is not None:
                    accumulator[key] = accumulator.get(key, 0) + numeric_value
        self.agent_state["numerical_accumulator"] = accumulator

    def append_textual_observation(self, category: str, text: str) -> None:
        if not text or not isinstance(text, str):
            return
        self.agent_state.setdefault("textual_accumulator", {}).setdefault(category, []).append(text.strip())

    def accumulate_textual_values(self, extracted_data: Dict[str, Any]) -> None:
        if not isinstance(extracted_data, dict):
            return
        schema = self.agent_state.get("schema", {})
        textual_fields = set(self._get_textual_schema_fields(schema))
        textual_acc = self.agent_state.get("textual_accumulator", {})
        for key, value in extracted_data.items():
            if key not in textual_fields:
                continue
            if not isinstance(value, str) or len(value.strip()) < 20:
                continue
            textual_acc.setdefault(key, []).append(value.strip())
        self.agent_state["textual_accumulator"] = textual_acc

    def get_textual_context(self) -> str:
        parts = []
        for cat, items in self.agent_state.get("textual_accumulator", {}).items():
            if items:
                parts.append(f"=== {cat} ===")
                parts.extend(items)
        return "\n\n".join(parts)

    def _build_combined_remarks(self, remarks_dict: Dict[str, Any]) -> str:
        if not isinstance(remarks_dict, dict):
            remarks_dict = {}
        sections = []
        for key, value in remarks_dict.items():
            if not isinstance(value, str) or not value.strip():
                continue
            label = key.replace("_", " ").strip()
            sections.append(f"=== {label.upper()} ===\n{value.strip()}")
        if not sections:
            return ""
        return "\n\n".join(sections)

    def _normalize_schema_remarks(self, remarks_dict: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(remarks_dict, dict):
            return {}

        textual_fields = self._get_textual_schema_fields(schema)
        if not textual_fields:
            return {k: v for k, v in remarks_dict.items() if isinstance(v, str) and v.strip()}

        normalized = {}
        for field in textual_fields:
            value = remarks_dict.get(field)
            if isinstance(value, str) and value.strip():
                normalized[field] = value.strip()
            elif field in remarks_dict and remarks_dict[field] is not None:
                normalized[field] = str(remarks_dict[field]).strip()

        for key, value in remarks_dict.items():
            if isinstance(value, str) and value.strip() and key not in normalized:
                normalized[key] = value.strip()

        return normalized

    def _build_render_context_from_schema(self, schema: Dict[str, Any], kpi_data: Dict[str, Any], remarks_dict: Dict[str, Any]) -> Dict[str, Any]:
        render_context: Dict[str, Any] = {}
        if not isinstance(kpi_data, dict):
            kpi_data = {}
        if not isinstance(remarks_dict, dict):
            remarks_dict = {}

        for variable in schema.get("variables", []):
            if not isinstance(variable, dict):
                continue
            name = variable.get("name")
            if not name:
                continue
            if name in kpi_data and kpi_data[name] not in [None, "", "null"]:
                render_context[name] = kpi_data[name]
            elif name in remarks_dict and remarks_dict[name] not in [None, "", "null"]:
                render_context[name] = remarks_dict[name]
            elif variable.get("type") == "number":
                render_context[name] = None
            else:
                render_context[name] = ""

        for key, value in remarks_dict.items():
            if key not in render_context and value not in [None, "", "null"]:
                render_context[key] = value

        for key, value in list(render_context.items()):
            if value is None or value == "None" or value == "null":
                render_context[key] = ""

        return render_context

    def _merge_remarks_into_kpi_data(self, kpi_data: Dict[str, Any], remarks_dict: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(kpi_data, dict):
            kpi_data = {}
        if not isinstance(remarks_dict, dict):
            return kpi_data

        merged = kpi_data.copy()
        textual_fields = set(self._get_textual_schema_fields(schema))

        for key, value in remarks_dict.items():
            if key in textual_fields and (merged.get(key) in [None, "", "null"] or key not in merged):
                if isinstance(value, str) and value.strip():
                    merged[key] = value.strip()
            elif key not in merged and isinstance(value, str) and value.strip():
                merged[key] = value.strip()

        return merged

    def run_structural_reducer(self, schema: Dict[str, Any], extraction_results: List[Dict[str, Any]], merged_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tầng 2: dùng prompt schema-driven để tạo object JSON duy nhất và tích lũy dữ liệu."""
        if not isinstance(schema, dict):
            return merged_data or {}

        try:
            sys_p, user_p = self._load_prompt("structural_reducer.yaml")
        except FileNotFoundError:
            logger.warning("Không tìm thấy prompt structural_reducer.yaml; fallback về merge_data thông thường.")
            return merged_data or {}

        formatted_user_p = user_p.format(
            schema=json.dumps(schema, ensure_ascii=False, indent=2),
            target_report_period=self.agent_state.get("target_report_period", "Tuần 3"),
            extraction_results=json.dumps(extraction_results, ensure_ascii=False, indent=2),
            merged_data=json.dumps(merged_data, ensure_ascii=False, indent=2)
        )

        response = self._call_llm(sys_p, formatted_user_p, response_format="json")
        try:
            reduced = json.loads(response)
        except Exception:
            return merged_data or {}

        if not isinstance(reduced, dict):
            return merged_data or {}

        normalized = {}
        for variable in schema.get("variables", []):
            if not isinstance(variable, dict):
                continue
            name = variable.get("name")
            if not name:
                continue
            if name in reduced and reduced[name] is not None and reduced[name] != "":
                normalized[name] = reduced[name]
            elif name in merged_data and merged_data[name] is not None and merged_data[name] != "":
                normalized[name] = merged_data[name]
            else:
                normalized[name] = reduced.get(name, "")

        return normalized

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
                
            template_context = self.parser.parse(template_path) if template_path and Path(template_path).exists() else ""
            schema = self.agent_state.get("schema", {}) or {}
            textual_fields = self._get_textual_schema_fields(schema)
            formatted_user_p = user_p.format(
                kpi_data=json.dumps(kpi_data, ensure_ascii=False, indent=2),
                rag_context=rag_context if rag_context else "Không có văn cảnh quy định cụ thể.",
                textual_context=self.get_textual_context(),
                template_context=template_context,
                schema=json.dumps(schema, ensure_ascii=False, indent=2),
                textual_fields=json.dumps(textual_fields, ensure_ascii=False)
            )
            if style_str:
                formatted_user_p += style_str
    
            # Gọi LLM với định dạng JSON
            response_text = self._call_llm(sys_p, formatted_user_p, response_format="json")
            try:
                remarks_dict = json.loads(response_text)
            except Exception as e:
                logger.error(f"Không thể parse JSON từ phản hồi nhận xét. Thử dùng text thô làm mặc định: {str(e)}")
                remarks_dict = {"nhan_xet_ai": response_text}

            remarks_dict = self._normalize_schema_remarks(remarks_dict, schema)
            combined_remarks = self._build_combined_remarks(remarks_dict)

            render_context = self._build_render_context_from_schema(schema, kpi_data, remarks_dict)
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
            
            # Check cache
            cache_val = self.memory_manager.cache_get(file_path)
            if cache_val:
                masked_text = cache_val["masked_text"]
                self.restore_maps[file_path] = cache_val["restore_map"]
                self.agent_state["raw_text_cache"][file_path] = masked_text
                if cache_val.get("period_label"):
                    self.agent_state["file_period_labels"][file_path] = cache_val["period_label"]
                logger.info(f"Đọc tệp tin {file_path} từ Cache thành công.")
                return {
                    "masked_text": masked_text[:1000] + "\n... [Văn bản được rút gọn trong ReAct Context] ...",
                    "restore_map_len": len(cache_val["restore_map"]),
                    "is_redacted": False
                }
                
            raw_text = self.parser.parse(file_path)
            is_safe, found_secrets = self.redaction.is_safe(raw_text)
            if not is_safe:
                raw_text = self.redaction.redact(raw_text)
                
            masked_text, restore_map = self.anonymizer.anonymize(raw_text)
            self.restore_maps[file_path] = restore_map
            self.agent_state["raw_text_cache"][file_path] = masked_text
            period_label = self._infer_file_period_label(raw_text, file_path)
            self.agent_state["file_period_labels"][file_path] = period_label
            logger.info(f"Đã gắn nhãn kỳ báo cáo cho file {Path(file_path).name}: {period_label}")
            
            # Save to Cache
            self.memory_manager.cache_set(file_path, {
                "masked_text": masked_text,
                "restore_map": restore_map,
                "period_label": period_label
            })
            
            # Update task progress
            if self.session_id:
                progress = self.memory_manager.get_progress(self.session_id)
                if progress:
                    comp_files = progress.get("completed_files", [])
                    if file_path not in comp_files:
                        comp_files.append(file_path)
                    self.memory_manager.update_progress(
                        task_id=self.session_id,
                        current_step=progress["current_step"] + 1,
                        current_file=file_path,
                        completed_files=comp_files,
                        status="running"
                    )
            
            return {
                "masked_text": masked_text[:1000] + "\n... [Văn bản được rút gọn trong ReAct Context] ...",
                "restore_map_len": len(restore_map),
                "is_redacted": not is_safe
            }
            
        elif tool_name == "extract_kpis_tool":
            file_path = tool_input.get("file_path")
            schema = tool_input.get("schema") or self.agent_state.get("schema", {})
            extracted_data: Dict[str, Any] = {}
            raw_text_cache = self.agent_state.get("raw_text_cache", {})

            if file_path:
                extracted_data = self.extract_kpis_for_file(file_path, schema)
                source_file = file_path
            else:
                extraction_results = []
                for path in raw_text_cache.keys():
                    extraction_results.append(self.extract_kpis_for_file(path, schema))

                if not extraction_results:
                    raise ValueError("Không có raw text để trích xuất KPI.")

                merged_data, conflicts = self.merge_extracted_kpi_results(extraction_results)
                self.agent_state["extraction_conflicts"] = conflicts
                extracted_data = merged_data
                source_file = "multiple_files" if len(raw_text_cache) > 1 else (next(iter(raw_text_cache.keys())) if raw_text_cache else "unknown_source")

            self.accumulate_numerical_values(extracted_data)
            self.accumulate_textual_values(extracted_data)

            # Lưu vào MemoryManager và cập nhật kpi_data
            for key, val in extracted_data.items():
                unit = None
                if schema and "variables" in schema:
                    for var in schema["variables"]:
                        if var["name"] == key:
                            desc = var.get("description", "").lower()
                            if "đồng" in desc:
                                unit = "đồng"
                            elif "người" in desc:
                                unit = "người"
                            elif "vụ" in desc:
                                unit = "vụ"
                            elif "ngày" in desc:
                                unit = "ngày"
                            break

                if self.session_id:
                    self.memory_manager.save_indicator(
                        task_id=self.session_id,
                        indicator_name=key,
                        value=val,
                        unit=unit,
                        source_file=source_file,
                        confidence=1.0
                    )

            self.agent_state["kpi_data"].update(extracted_data)

            return extracted_data

        elif tool_name == "extract_kpis_file_tool":
            file_path = tool_input.get("file_path")
            schema = tool_input.get("schema") or self.agent_state.get("schema", {})
            return self.extract_kpis_for_file(file_path, schema)

        elif tool_name == "merge_kpi_extractions_tool":
            extraction_results = tool_input.get("results", [])
            if not isinstance(extraction_results, list):
                raise ValueError("Results phải là danh sách các kết quả trích xuất KPI từ từng file.")

            merged_data, conflicts = self.merge_extracted_kpi_results(extraction_results)
            self.agent_state["extraction_conflicts"] = conflicts
            self.agent_state["kpi_data"].update(merged_data)
            self.accumulate_numerical_values(merged_data)
            self.accumulate_textual_values(merged_data)

            source_file = "multiple_files" if len(extraction_results) > 1 else "unknown_source"
            for key, val in merged_data.items():
                if self.session_id:
                    self.memory_manager.save_indicator(
                        task_id=self.session_id,
                        indicator_name=key,
                        value=val,
                        unit=None,
                        source_file=source_file,
                        confidence=1.0
                    )

            return {
                "merged_kpi_data": merged_data,
                "conflicts": conflicts
            }
            
        elif tool_name == "retrieve_memory_tool":
            query = tool_input.get("query")
            if not self.session_id:
                return []
            indicators = self.memory_manager.search_indicator(self.session_id, query)
            simplified = []
            for ind in indicators:
                simplified.append({
                    "indicator_name": ind["indicator_name"],
                    "value": ind["value"],
                    "unit": ind["unit"],
                    "source_file": Path(ind["source_file"]).name if ind["source_file"] else None,
                    "confidence": ind["confidence"]
                })
            return simplified
            
        elif tool_name == "validate_and_correct_tool":
            kpi_data = tool_input.get("kpi_data") or self.agent_state.get("kpi_data", {})
            is_valid, failures = self.rule_engine.validate(kpi_data)
            return {"is_valid": is_valid, "failures": failures}
            
        elif tool_name == "rag_search_tool":
            query = tool_input.get("query")
            domain = tool_input.get("domain")
            return self.memory_manager.search_document(query, domain_filter=domain)
            
        elif tool_name == "generate_section_remarks_tool":
            kpi_data = tool_input.get("kpi_data") or self.agent_state.get("kpi_data", {})
            template_path = tool_input.get("template_path") or self.agent_state.get("template_path")
            schema = tool_input.get("schema") or self.agent_state.get("schema", {}) or {}
            sys_p, user_p = self._load_prompt("report_commenter.yaml")
            
            effective_rag_context = rag_context
            if not effective_rag_context:
                queries = ["chế độ báo cáo thông tư nghị định", "quy trình giải quyết khiếu nại tố cáo", "dân cư cư trú hộ tịch"]
                context_blocks = []
                for q in queries:
                    res = self.memory_manager.search_document(q, top_k=2)
                    if "Không tìm thấy" not in res:
                        context_blocks.append(res)
                effective_rag_context = "\n\n".join(context_blocks) if context_blocks else "Không có văn cảnh quy định cụ thể."

            textual_context = self.get_textual_context() or "Không có ngữ cảnh văn bản tích lũy."
            template_context = self.parser.parse(template_path) if template_path and Path(template_path).exists() else ""
            textual_fields = self._get_textual_schema_fields(schema)
            formatted_user_p = user_p.format(
                kpi_data=json.dumps(kpi_data, ensure_ascii=False, indent=2),
                rag_context=effective_rag_context,
                textual_context=textual_context,
                template_context=template_context,
                schema=json.dumps(schema, ensure_ascii=False, indent=2),
                textual_fields=json.dumps(textual_fields, ensure_ascii=False)
            )
            response = self._call_llm(sys_p, formatted_user_p, response_format="json")
            remarks_dict = json.loads(response)
            return self._normalize_schema_remarks(remarks_dict, schema)
            
        elif tool_name == "render_docx_report_tool":
            template_path = tool_input.get("template_path")
            kpi_data = tool_input.get("kpi_data") or self.agent_state.get("kpi_data", {})
            remarks_dict = tool_input.get("remarks_dict") or self.agent_state.get("remarks", {})
            output_path = tool_input.get("output_path")
            
            self._assert_required_output_fields(kpi_data)
            self._validate_output_against_memory(kpi_data)

            combined_remarks = self._build_combined_remarks(remarks_dict)
            
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
            
            if self.session_id:
                self.memory_manager.finish_task(self.session_id, "completed")
            
            return {
                "status": "success",
                "output_path": output_path,
                "combined_remarks": combined_remarks
            }
        else:
            raise ValueError(f"Không tìm thấy công cụ nghiệp vụ: {tool_name}")

    def run_file_subagent(self, file_path: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Chạy subagent cho một file raw, bao gồm đọc/làm sạch và trích xuất KPI từng file."""
        self.execute_agent_tool("read_and_clean_raw_tool", {"file_path": file_path})
        result = self.execute_agent_tool("extract_kpis_file_tool", {"file_path": file_path, "schema": schema})

        raw_text = self.parser.parse(file_path)
        raw_period = self._infer_raw_data_period(raw_text)
        self.agent_state["file_period_labels"][file_path] = raw_period

        if isinstance(result, dict) and self._subagent_cross_check_needs_rerun(result, schema):
            logger.warning(f"Subagent cần quét lại file do phát hiện dấu hiệu an ninh/pháp luật nhưng chưa có số liệu định lượng: {Path(file_path).name}")
            retry_result = self.execute_agent_tool("extract_kpis_file_tool", {"file_path": file_path, "schema": schema})
            if isinstance(retry_result, dict):
                result = retry_result

        if isinstance(result, dict):
            result["_source_file"] = Path(file_path).name
            result["_period_label"] = self.agent_state.get("file_period_labels", {}).get(file_path, "unknown")
            result["_raw_data_period"] = raw_period
            result["_out_of_scope"] = self._is_out_of_scope(raw_period, self.agent_state.get("target_report_period", "Tuần 3"))
        return result


    def _infer_raw_data_period(self, raw_text: str) -> str:
        raw_lower = (raw_text or "").lower()
        if "tuần 3" in raw_lower or "tuan 3" in raw_lower:
            return "Tuần 3"
        if "tuần" in raw_lower or "tuan" in raw_lower:
            return "Tuần"
        if "tháng" in raw_lower or "thang" in raw_lower:
            return "Tháng"
        return "unknown"

    def _is_out_of_scope(self, raw_period: str, target_period: str) -> bool:
        if not raw_period or raw_period == "unknown":
            return False
        raw_period = raw_period.strip().lower()
        target_period = target_period.strip().lower()
        if target_period == raw_period:
            return False
        return True

    def _assert_required_output_fields(self, kpi_data: Dict[str, Any]) -> None:
        schema = self.agent_state.get("schema") or {}
        required_fields = []
        for var in schema.get("variables", []):
            if isinstance(var, dict) and var.get("name"):
                required_fields.append(var["name"])

        if not required_fields:
            return

        missing = []
        for field in required_fields:
            value = kpi_data.get(field)
            if value is None or value == "" or str(value).strip().lower() in ["null", "undefined"]:
                missing.append(field)

        if missing:
            raise ValueError(f"Thiếu trường dữ liệu bắt buộc trước khi xuất báo cáo: {', '.join(missing)}")

    def _validate_output_against_memory(self, kpi_data: Dict[str, Any]) -> None:
        if not self.session_id:
            return
        indicators = self.memory_manager.list_indicators(self.session_id)
        mismatches = []
        for ind in indicators:
            name = ind["indicator_name"]
            if name in kpi_data:
                expected = str(ind["value"]).strip()
                actual = str(kpi_data.get(name, "")).strip()
                if actual != expected:
                    mismatches.append({
                        "indicator": name,
                        "expected": expected,
                        "actual": actual,
                        "source_file": ind.get("source_file")
                    })
        if mismatches:
            raise ValueError(f"Phát hiện không khớp giữa kpi_data và log chỉ tiêu trung gian: {json.dumps(mismatches, ensure_ascii=False)}")

    def run_multi_agent_pipeline(
        self, template_path: str, raw_paths: List[str], output_path: str, rag_context: str = "", session_id: str = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Chạy supervisor pipeline với các subagent xử lý từng file riêng biệt."""
        logger.info("BẮT ĐẦU MULTI-AGENT SUPERVISOR PIPELINE")

        import uuid
        self.session_id = session_id or str(uuid.uuid4())
        self.memory_manager.create_task(self.session_id, len(raw_paths))

        self.agent_state = {
            "schema": None,
            "kpi_data": {},
            "remarks": {},
            "raw_text_cache": {},
            "file_period_labels": {},
            "numerical_accumulator": {},
            "textual_accumulator": {},
            "extraction_conflicts": []
        }

        step_counter = 1
        try:
            sys_p, user_p = self._load_prompt("supervisor.yaml")
            formatted_user_p = user_p.format(
                template_path=template_path,
                raw_paths=json.dumps(raw_paths, ensure_ascii=False),
                output_path=output_path
            )
            plan_text = self._call_llm(sys_p, formatted_user_p, response_format="text")
            yield {
                "status": "running",
                "step": step_counter,
                "thought": "Supervisor lập kế hoạch và điều phối các subagent.",
                "action": "supervisor_plan",
                "action_input": {
                    "template_path": template_path,
                    "raw_paths": raw_paths,
                    "output_path": output_path
                },
                "observation": plan_text
            }
        except Exception as e:
            logger.warning(f"Không thể lấy kế hoạch supervisor: {e}")
            yield {
                "status": "running",
                "step": step_counter,
                "thought": "Supervisor bắt đầu điều phối mà không cần plan chi tiết từ LLM.",
                "action": "supervisor_plan",
                "action_input": {},
                "observation": "Không có kế hoạch chi tiết từ supervisor prompt."
            }
        step_counter += 1

        schema = self.execute_agent_tool("extract_schema_tool", {"template_path": template_path})
        yield {
            "status": "running",
            "step": step_counter,
            "thought": "Đã phân tích biểu mẫu trống và xác định schema.",
            "action": "extract_schema_tool",
            "action_input": {"template_path": template_path},
            "observation": schema
        }
        step_counter += 1

        extraction_results = []
        for raw_path in raw_paths:
            subagent_result = self.run_file_subagent(raw_path, schema)
            extraction_results.append(subagent_result)
            yield {
                "status": "running",
                "step": step_counter,
                "thought": f"Subagent đã xử lý file: {Path(raw_path).name}.",
                "action": "extract_kpis_file_tool",
                "action_input": {"file_path": raw_path},
                "observation": subagent_result
            }
            step_counter += 1

        merge_obs = self.execute_agent_tool("merge_kpi_extractions_tool", {"results": extraction_results})
        merged_data = merge_obs.get("merged_kpi_data", {}) if isinstance(merge_obs, dict) else {}
        reducer_obs = self.run_structural_reducer(schema, extraction_results, merged_data)
        if isinstance(reducer_obs, dict):
            self.agent_state["kpi_data"] = reducer_obs
        yield {
            "status": "running",
            "step": step_counter,
            "thought": "Đã gộp kết quả trích xuất KPI từ tất cả subagent và chuyển sang tầng 2 để tích lũy theo schema.",
            "action": "structural_reducer",
            "action_input": {"results": extraction_results},
            "observation": reducer_obs
        }
        step_counter += 1

        validate_obs = self.execute_agent_tool("validate_and_correct_tool", {})
        yield {
            "status": "running",
            "step": step_counter,
            "thought": "Đã kiểm tra chéo số liệu và ghi nhận lỗi nếu có.",
            "action": "validate_and_correct_tool",
            "action_input": {},
            "observation": validate_obs
        }
        step_counter += 1

        self.agent_state["template_path"] = template_path
        remarks_obs = self.execute_agent_tool("generate_section_remarks_tool", {"template_path": template_path, "schema": schema})
        self.agent_state["remarks"] = remarks_obs
        self.agent_state["kpi_data"] = self._merge_remarks_into_kpi_data(self.agent_state["kpi_data"], remarks_obs, schema)
        yield {
            "status": "running",
            "step": step_counter,
            "thought": "Đã tạo nhận xét báo cáo dựa trên dữ liệu hiện tại.",
            "action": "generate_section_remarks_tool",
            "action_input": {},
            "observation": remarks_obs
        }
        step_counter += 1

        final_answer = {
            "status": "success",
            "kpi_data": self.agent_state["kpi_data"],
            "remarks": remarks_obs,
            "combined_remarks": self._build_combined_remarks(remarks_obs),
            "render_context": self._build_render_context_from_schema(self.agent_state.get("schema", {}) or {}, self.agent_state.get("kpi_data", {}), remarks_obs),
            "output_path": output_path,
            "conflicts": self.agent_state.get("extraction_conflicts", [])
        }

        yield {
            "status": "completed",
            "step": step_counter,
            "thought": "Pipeline supervisor + subagent hoàn tất.",
            "final_answer": final_answer
        }

    def run_react_agent_generator(
        self, template_path: str, raw_paths: List[str], output_path: str, rag_context: str = "", session_id: str = None
    ) -> Generator[Dict[str, Any], None, None]:
        return self.run_multi_agent_pipeline(template_path, raw_paths, output_path, rag_context, session_id)
