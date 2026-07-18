import re
import logging
from typing import List, Tuple

logger = logging.getLogger("RedactionHook")


class RedactionHook:
    def __init__(self, custom_keywords: List[str] = None):
        logger.info("Khởi tạo RedactionHook để rà soát tài liệu mật.")
        self.default_keywords = [
            "tối mật", "tuyệt mật", "tài liệu mật", "danh mục mật",
            "bí mật nhà nước", "bí mật quốc gia", "ngân sách quốc phòng",
            "kế hoạch quân sự", "kế hoạch tác chiến", "kế hoạch mật",
            "dự án quốc phòng", "an ninh quốc phòng địa phương", "tin mật"
        ]
        if custom_keywords:
            self.default_keywords.extend(custom_keywords)
            
        joined_keywords = "|".join([re.escape(kw) for kw in self.default_keywords])
        self.redact_pattern = re.compile(rf'\b({joined_keywords})\b', re.IGNORECASE)

    def is_safe(self, text: str) -> Tuple[bool, List[str]]:
        logger.info("Đang rà soát từ khóa mật trong văn bản...")
        found_matches = self.redact_pattern.findall(text)
        if found_matches:
            unique_matches = list(set([m.lower() for m in found_matches]))
            logger.warning(f"🚨 CẢNH BÁO: Phát hiện {len(unique_matches)} từ khóa mật: {unique_matches}")
            return False, unique_matches
        logger.info("Văn bản an toàn (không chứa từ khóa mật).")
        return True, []

    def redact(self, text: str, replacement: str = "[REDACTED]") -> str:
        logger.info("Đang che giấu các từ khóa tài liệu mật bằng [REDACTED]...")
        redacted_text = self.redact_pattern.sub(replacement, text)
        logger.info("Che giấu hoàn tất.")
        return redacted_text
