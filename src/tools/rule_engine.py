import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
from config import settings

logger = logging.getLogger("RuleEngine")


class SafeEvalEnv(dict):
    """
    Môi trường eval an toàn tự động trả về 0 cho các khóa biến số liệu bị thiếu hụt
    thay vì ném ra lỗi NameError/TypeError.
    """
    def __missing__(self, key):
        logger.debug(f"Biến số liệu '{key}' bị thiếu trong dữ liệu đầu vào. Tự động gán bằng 0.")
        return 0


class RuleEngine:
    def __init__(self):
        logger.info("Khởi tạo RuleEngine để kiểm chéo số liệu.")
        self.rules: List[Dict[str, Any]] = []
        self.load_rules()

    def load_rules(self):
        rules_path = Path(settings.VALIDATION_RULES_PATH)
        if rules_path.exists():
            logger.info(f"Đang tải danh sách quy tắc kiểm chéo từ: {rules_path.name}")
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.rules = data.get("rules", [])
            logger.info(f"Đã tải thành công {len(self.rules)} quy tắc.")
        else:
            logger.warning(f"Không tìm thấy file quy tắc kiểm chéo tại: {settings.VALIDATION_RULES_PATH}")

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        logger.info("Bắt đầu kiểm tra chéo số liệu...")
        failures = []
        is_valid = True
        
        # Thiết lập môi trường eval an toàn
        eval_env = SafeEvalEnv()
        eval_env["abs"] = abs
        
        # Nạp dữ liệu hiện có
        for k, v in data.items():
            if v is None:
                eval_env[k] = 0
            else:
                try:
                    # Ép kiểu số nguyên hoặc số thực nếu có thể để tính toán chuẩn xác
                    val_str = str(v).strip()
                    if '.' in val_str:
                        eval_env[k] = float(val_str)
                    else:
                        eval_env[k] = int(val_str)
                except ValueError:
                    # Giữ nguyên giá trị chuỗi nếu không thể chuyển đổi
                    eval_env[k] = v

        for rule in self.rules:
            rule_id = rule.get("id")
            formula = rule.get("formula")
            desc = rule.get("description")
            severity = rule.get("severity", "warning")
            
            logger.info(f"Đang kiểm tra quy tắc: {rule_id} -> Công thức: {formula}")
            try:
                result = eval(formula, {"__builtins__": None, "abs": abs}, eval_env)
                if not result:
                    logger.warning(f"🚨 Vi phạm quy tắc {rule_id}: {desc} (Mức độ: {severity})")
                    failure_detail = {
                        "id": rule_id,
                        "description": desc,
                        "severity": severity,
                        "formula": formula,
                        "status": "failed",
                        "error_msg": "Số liệu không khớp công thức logic chéo"
                    }
                    failures.append(failure_detail)
                    if severity == "error":
                        is_valid = False
                else:
                    logger.info(f"✅ Quy tắc {rule_id} đạt yêu cầu.")
            except ZeroDivisionError:
                logger.warning(f"⚠️ Phát hiện phép chia cho 0 khi thực thi quy tắc {rule_id} (mẫu số bằng 0).")
                failures.append({
                    "id": rule_id,
                    "description": desc,
                    "severity": severity,
                    "formula": formula,
                    "status": "failed",
                    "error_msg": "Không thể chia cho 0 (mẫu số bằng 0)"
                })
                if severity == "error":
                    is_valid = False
            except Exception as e:
                logger.error(f"❌ Lỗi nghiêm trọng khi thực thi quy tắc {rule_id}: {str(e)}")
                failures.append({
                    "id": rule_id,
                    "description": desc,
                    "severity": severity,
                    "formula": formula,
                    "status": "error",
                    "error_msg": f"Lỗi thực thi công thức: {str(e)}"
                })
                if severity == "error":
                    is_valid = False
                
        logger.info(f"Kết quả kiểm chéo: Hợp lệ={is_valid}, Số quy tắc lỗi={len(failures)}")
        return is_valid, failures
