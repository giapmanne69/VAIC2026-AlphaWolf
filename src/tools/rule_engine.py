import json
from pathlib import Path
from typing import Dict, Any, List, Tuple
from config import settings


class RuleEngine:
    def __init__(self):
        self.rules: List[Dict[str, Any]] = []
        self.load_rules()

    def load_rules(self):
        """
        Đọc danh sách quy tắc nghiệp vụ từ validation_rules.json.
        """
        rules_path = Path(settings.VALIDATION_RULES_PATH)
        if rules_path.exists():
            with open(rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.rules = data.get("rules", [])

    def validate(self, data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Kiểm tra dữ liệu số liệu dựa trên các công thức quy định.
        Trả về:
            - is_valid (bool): True nếu không vi phạm quy tắc mức độ 'error' nào.
            - failures (list): Danh sách các quy tắc bị vi phạm kèm chi tiết.
        """
        failures = []
        is_valid = True
        
        # Chuẩn hóa dữ liệu đầu vào: Chuyển các giá trị trống hoặc None thành 0 hoặc null
        eval_env = {"abs": abs}
        for k, v in data.items():
            if v is None:
                eval_env[k] = 0  # Default to 0 for numerical comparisons
            else:
                eval_env[k] = v

        for rule in self.rules:
            rule_id = rule.get("id")
            formula = rule.get("formula")
            desc = rule.get("description")
            severity = rule.get("severity", "warning")
            
            # Quét tìm các biến xuất hiện trong công thức xem có trong data không
            # Để tránh lỗi NameError khi chạy eval
            try:
                # Đánh giá công thức bằng hàm eval an toàn với môi trường eval_env chứa số liệu
                # Chỉ cho phép hàm abs và các biến số liệu thực tế
                result = eval(formula, {"__builtins__": None, "abs": abs}, eval_env)
                
                if not result:
                    # Công thức trả về False -> Vi phạm quy tắc
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
            except ZeroDivisionError:
                # Xử lý trường hợp chia cho 0 (ví dụ ho_so_da_giai_quyet = 0)
                failures.append({
                    "id": rule_id,
                    "description": desc,
                    "severity": severity,
                    "formula": formula,
                    "status": "error",
                    "error_msg": "Lỗi phép chia cho 0 trong công thức kiểm tra"
                })
                if severity == "error":
                    is_valid = False
            except Exception as e:
                # Các lỗi cú pháp khác hoặc NameError do thiếu trường
                failures.append({
                    "id": rule_id,
                    "description": desc,
                    "severity": severity,
                    "formula": formula,
                    "status": "error",
                    "error_msg": f"Lỗi cú pháp công thức hoặc thiếu trường số liệu: {str(e)}"
                })
                # Thiếu trường dữ liệu tạm thời cảnh báo, không làm gãy hệ thống trừ phi bắt buộc
                
        return is_valid, failures
