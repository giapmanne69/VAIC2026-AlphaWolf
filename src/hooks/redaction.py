import re
from typing import List, Tuple

class RedactionHook:
    def __init__(self, custom_keywords: List[str] = None):
        # Danh mục từ khóa tài liệu mật mặc định trong khối cơ quan nhà nước
        self.default_keywords = [
            "tối mật", "tuyệt mật", "tài liệu mật", "danh mục mật",
            "bí mật nhà nước", "bí mật quốc gia", "ngân sách quốc phòng",
            "kế hoạch quân sự", "kế hoạch tác chiến", "kế hoạch mật",
            "dự án quốc phòng", "an ninh quốc phòng địa phương", "tin mật"
        ]
        if custom_keywords:
            self.default_keywords.extend(custom_keywords)
            
        # Compile regex không phân biệt chữ hoa chữ thường
        joined_keywords = "|".join([re.escape(kw) for kw in self.default_keywords])
        self.redact_pattern = re.compile(rf'\b({joined_keywords})\b', re.IGNORECASE)

    def is_safe(self, text: str) -> Tuple[bool, List[str]]:
        """
        Kiểm tra xem văn bản có chứa thông tin mật hay không.
        Trả về:
            - True nếu an toàn (không chứa từ mật)
            - Danh sách các từ mật phát hiện được
        """
        found_matches = self.redact_pattern.findall(text)
        if found_matches:
            # Loại bỏ trùng lặp và chuyển về chữ thường để hiển thị cảnh báo
            unique_matches = list(set([m.lower() for m in found_matches]))
            return False, unique_matches
        return True, []

    def redact(self, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Che giấu toàn bộ từ khóa mật bằng thẻ [REDACTED].
        """
        return self.redact_pattern.sub(replacement, text)
