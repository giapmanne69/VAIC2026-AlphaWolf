import logging
from typing import List, Dict, Any

logger = logging.getLogger("ShortTermMemory")


class ShortTermMemory:
    def __init__(self):
        logger.info("Khởi tạo bộ nhớ ngắn hạn ShortTermMemory.")
        self.messages: List[Dict[str, str]] = []
        self.session_data: Dict[str, Any] = {}

    def add_message(self, role: str, content: str):
        logger.info(f"Bộ nhớ ngắn hạn: Thêm tin nhắn từ vai trò [{role}].")
        self.messages.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        return self.messages

    def set_data(self, key: str, value: Any):
        logger.info(f"Bộ nhớ ngắn hạn: Lưu trữ dữ liệu tạm thời '{key}'.")
        self.session_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        val = self.session_data.get(key, default)
        logger.debug(f"Bộ nhớ ngắn hạn: Truy xuất dữ liệu '{key}' -> Trạng thái tồn tại: {val is not None}")
        return val

    def clear(self):
        logger.info("Làm sạch bộ nhớ ngắn hạn ShortTermMemory.")
        self.messages.clear()
        self.session_data.clear()
