import re
from typing import Dict, Tuple

class AnonymizerHook:
    def __init__(self):
        # 1. Regex định vị Số điện thoại Việt Nam (các đầu số 03, 05, 07, 08, 09 kèm định dạng)
        self.phone_pattern = re.compile(
            r'\b(0[35789]\d{8}|0[35789]\d{2}[\s.-]\d{3}[\s.-]\d{3})\b'
        )
        
        # 2. Regex định vị Số CCCD / CMND (9 hoặc 12 chữ số liên tiếp)
        self.cccd_pattern = re.compile(r'\b(\d{12}|\d{9})\b')
        
        # 3. Regex định vị địa chỉ nhà chi tiết (ví dụ: Số nhà 12, Ngõ 45, Tổ 3...)
        self.address_pattern = re.compile(
            r'(?i)\b(số\s+nhà\s+\d+|số\s+\d+[\w/]*)\s*,\s*(ngõ|ngách|tổ|thôn|xóm|phố|đường)\s+[\w\s]+',
            re.UNICODE
        )
        
        # 4. Các họ phổ biến của người Việt để làm điểm bắt đầu quét tên riêng
        self.vietnamese_surnames = (
            r'(Nguyễn|Trần|Lê|Phạm|Hoàng|Huỳnh|Phan|Vũ|Võ|Đặng|Bùi|Đỗ|Hồ|Ngô|Dương|Lâm|Trương|Vương|Trịnh|Tống)'
        )
        # Regex khớp tên riêng viết hoa chữ cái đầu (2 đến 4 từ bắt đầu bằng họ phổ biến)
        self.name_pattern = re.compile(
            rf'\b{self.vietnamese_surnames}\s+([A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐĨŨƠàáâãèéêìíòóôõùúýăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư][a-zàáâãèéêìíòóôõùúýăđĩũơƯĂÂĐÊÔƠƯưăâđêôơư]*\s*){{1,3}}\b',
            re.UNICODE
        )

    def anonymize(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Ẩn danh hóa các thông tin nhạy cảm trong văn bản.
        Trả về:
            - Văn bản đã ẩn danh (anonymized_text)
            - Từ điển map giữa mã ẩn danh và giá trị gốc (restoration_map)
        """
        restoration_map = {}
        anonymized_text = text
        
        # Helper để thay thế và lưu bản đồ khôi phục
        def replace_with_tag(pattern: re.Pattern, tag_prefix: str, content: str) -> str:
            matches = list(set(pattern.findall(content)))
            # Sắp xếp matches theo độ dài giảm dần để tránh thay thế chuỗi con trước
            matches.sort(key=len, reverse=True)
            
            result = content
            for i, match in enumerate(matches):
                # Trường hợp pattern.findall trả về tuple (ví dụ do name_pattern có group)
                val_to_replace = match[0] if isinstance(match, tuple) else match
                if not val_to_replace or len(val_to_replace.strip()) < 3:
                    continue
                    
                val_to_replace = val_to_replace.strip()
                tag = f"[{tag_prefix}_{i+1:03d}]"
                
                # Chỉ thay thế nếu chưa được lưu trong map
                if val_to_replace not in restoration_map.values():
                    restoration_map[tag] = val_to_replace
                    result = result.replace(val_to_replace, tag)
                else:
                    # Lấy tag cũ đã tạo
                    existing_tag = [k for k, v in restoration_map.items() if v == val_to_replace][0]
                    result = result.replace(val_to_replace, existing_tag)
            return result

        # Chạy ẩn danh theo thứ tự ưu tiên
        anonymized_text = replace_with_tag(self.phone_pattern, "PHONE", anonymized_text)
        anonymized_text = replace_with_tag(self.cccd_pattern, "CCCD", anonymized_text)
        anonymized_text = replace_with_tag(self.address_pattern, "ADDRESS", anonymized_text)
        anonymized_text = replace_with_tag(self.name_pattern, "NAME", anonymized_text)
        
        return anonymized_text, restoration_map

    def deanonymize(self, text: str, restoration_map: Dict[str, str]) -> str:
        """
        Khôi phục lại dữ liệu gốc từ mã ẩn danh.
        """
        restored_text = text
        # Thay thế ngược lại từ map
        for tag, original_val in restoration_map.items():
            restored_text = restored_text.replace(tag, original_val)
        return restored_text
