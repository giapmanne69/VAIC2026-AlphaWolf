import re
import logging
from typing import Dict, Tuple

logger = logging.getLogger("AnonymizerHook")


class AnonymizerHook:
    def __init__(self):
        logger.info("Khởi tạo AnonymizerHook để ẩn danh thông tin cá nhân (PII).")
        self.phone_pattern = re.compile(
            r'\b(0[35789]\d{8}|0[35789]\d{2}[\s.-]\d{3}[\s.-]\d{3})\b'
        )
        self.cccd_pattern = re.compile(r'\b(\d{12}|\d{9})\b')
        self.address_pattern = re.compile(
            r'(?i)\b(số\s+nhà\s+\d+|số\s+\d+[\w/]*)\s*,\s*(ngõ|ngách|tổ|thôn|xóm|phố|đường)\s+[\w\s]+',
            re.UNICODE
        )
        self.vietnamese_surnames = (
            r'(Nguyễn|Trần|Lê|Phạm|Hoàng|Huỳnh|Phan|Vũ|Võ|Đặng|Bùi|Đỗ|Hồ|Ngô|Dương|Lâm|Trương|Vương|Trịnh|Tống)'
        )
        self.name_pattern = re.compile(
            rf'\b{self.vietnamese_surnames}\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠàáâãèéêìíòóôõùúýăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư][a-zàáâãèéêìíòóôõùúýăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư]*\s*){{1,3}}\b',
            re.UNICODE
        )

    def anonymize(self, text: str) -> Tuple[str, Dict[str, str]]:
        logger.info("Bắt đầu quét và ẩn danh văn bản...")
        restoration_map = {}
        anonymized_text = text
        
        def replace_with_tag(pattern: re.Pattern, tag_prefix: str, content: str) -> str:
            matches = list(set(pattern.findall(content)))
            matches.sort(key=len, reverse=True)
            
            result = content
            for i, match in enumerate(matches):
                val_to_replace = match[0] if isinstance(match, tuple) else match
                if not val_to_replace or len(val_to_replace.strip()) < 3:
                    continue
                    
                val_to_replace = val_to_replace.strip()
                tag = f"[{tag_prefix}_{i+1:03d}]"
                
                if val_to_replace not in restoration_map.values():
                    restoration_map[tag] = val_to_replace
                    result = result.replace(val_to_replace, tag)
                    logger.debug(f"Ẩn danh: {val_to_replace} -> {tag}")
                else:
                    existing_tag = [k for k, v in restoration_map.items() if v == val_to_replace][0]
                    result = result.replace(val_to_replace, existing_tag)
            return result

        anonymized_text = replace_with_tag(self.phone_pattern, "PHONE", anonymized_text)
        anonymized_text = replace_with_tag(self.cccd_pattern, "CCCD", anonymized_text)
        anonymized_text = replace_with_tag(self.address_pattern, "ADDRESS", anonymized_text)
        anonymized_text = replace_with_tag(self.name_pattern, "NAME", anonymized_text)
        
        logger.info(f"Ẩn danh hoàn tất. Tổng số thực thể PII đã ẩn danh: {len(restoration_map)}")
        return anonymized_text, restoration_map

    def deanonymize(self, text: str, restoration_map: Dict[str, str]) -> str:
        logger.info("Bắt đầu khôi phục ngược dữ liệu ẩn danh (De-anonymize)...")
        restored_text = text
        for tag, original_val in restoration_map.items():
            restored_text = restored_text.replace(tag, original_val)
        logger.info(f"Khôi phục hoàn tất {len(restoration_map)} trường dữ liệu.")
        return restored_text
