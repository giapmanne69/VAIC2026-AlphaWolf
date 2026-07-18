import json
from pathlib import Path
from typing import Dict, Any, List
from config import settings


class LongTermMemory:
    def __init__(self, memory_file_path: str = None):
        if memory_file_path:
            self.memory_path = Path(memory_file_path)
        else:
            self.memory_path = Path(settings.DATA_DIR) / "long_term_memory.json"
            
        self.data: Dict[str, Any] = {
            "style_preferences": {},  # Lưu thói quen từ ngữ, ví dụ: "tỷ lệ giải quyết" -> "hiệu suất Một cửa"
            "human_corrections": []   # Lưu trace lịch sử sửa đổi: [{"field": "abc", "ai": 10, "human": 12, "timestamp": ...}]
        }
        self.load_memory()

    def load_memory(self):
        """
        Đọc bộ nhớ dài hạn từ file JSON.
        """
        if self.memory_path.exists():
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                # Nếu file lỗi định dạng, khởi tạo lại
                self.save_memory()

    def save_memory(self):
        """
        Ghi lại bộ nhớ dài hạn xuống đĩa.
        """
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add_style_preference(self, key: str, value: str):
        """
        Thêm/Cập nhật thói quen văn phong viết báo cáo.
        """
        self.data["style_preferences"][key] = value
        self.save_memory()

    def get_style_preferences(self) -> Dict[str, str]:
        """
        Lấy danh sách các thói quen viết văn bản.
        """
        return self.data.get("style_preferences", {})

    def record_human_correction(self, field_name: str, ai_val: Any, human_val: Any):
        """
        Ghi nhận lịch sử chỉnh sửa của cán bộ để Agent tự rút kinh nghiệm kỳ sau.
        """
        import time
        correction = {
            "field": field_name,
            "ai_value": ai_val,
            "human_value": human_val,
            "timestamp": time.time()
        }
        self.data["human_corrections"].append(correction)
        self.save_memory()

    def get_corrections(self) -> List[Dict[str, Any]]:
        """
        Lấy lịch sử chỉnh sửa.
        """
        return self.data.get("human_corrections", [])
