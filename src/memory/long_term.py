import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from config import settings

logger = logging.getLogger("LongTermMemory")


class LongTermMemory:
    def __init__(self, memory_file_path: str = None):
        logger.info("Khởi tạo bộ nhớ dài hạn LongTermMemory.")
        if memory_file_path:
            self.memory_path = Path(memory_file_path)
        else:
            self.memory_path = Path(settings.DATA_DIR) / "long_term_memory.json"
            
        self.data: Dict[str, Any] = {
            "style_preferences": {},
            "human_corrections": []
        }
        self.load_memory()

    def load_memory(self):
        if self.memory_path.exists():
            logger.info(f"Đang tải bộ nhớ dài hạn từ file: {self.memory_path.name}")
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                logger.info("Đã tải thành công bộ nhớ dài hạn.")
            except Exception as e:
                logger.exception("Lỗi khi tải bộ nhớ dài hạn. Đang reset lại:")
                self.save_memory()

    def save_memory(self):
        try:
            self.memory_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info(f"Đã lưu trữ bộ nhớ dài hạn xuống đĩa tại: {self.memory_path.name}")
        except Exception as e:
            logger.exception("Lỗi khi lưu bộ nhớ dài hạn xuống đĩa:")

    def add_style_preference(self, key: str, value: str):
        logger.info(f"Bộ nhớ dài hạn: Thêm thói quen văn phong mới: {key} -> {value[:50]}...")
        self.data["style_preferences"][key] = value
        self.save_memory()

    def get_style_preferences(self) -> Dict[str, str]:
        prefs = self.data.get("style_preferences", {})
        logger.info(f"Bộ nhớ dài hạn: Đọc danh sách {len(prefs)} thói quen văn phong.")
        return prefs

    def record_human_correction(self, field_name: str, ai_val: Any, human_val: Any):
        import time
        logger.warning(f"🚨 Bộ nhớ dài hạn: Ghi nhận cán bộ sửa chỉ tiêu '{field_name}' từ '{ai_val}' -> '{human_val}'")
        correction = {
            "field": field_name,
            "ai_value": ai_val,
            "human_value": human_val,
            "timestamp": time.time()
        }
        self.data["human_corrections"].append(correction)
        self.save_memory()

    def get_corrections(self) -> List[Dict[str, Any]]:
        return self.data.get("human_corrections", [])
