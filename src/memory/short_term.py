from typing import List, Dict, Any

class ShortTermMemory:
    def __init__(self):
        # Lưu lịch sử chat dạng: [{"role": "user/assistant/system", "content": "..."}]
        self.messages: List[Dict[str, str]] = []
        # Lưu các dữ liệu trích xuất tạm thời của phiên xử lý hiện tại (ví dụ: các biến số)
        self.session_data: Dict[str, Any] = {}

    def add_message(self, role: str, content: str):
        """
        Thêm một tin nhắn mới vào bộ nhớ ngắn hạn của phiên đối thoại.
        """
        self.messages.append({"role": role, "content": content})

    def get_history(self) -> List[Dict[str, str]]:
        """
        Lấy toàn bộ lịch sử hội thoại hiện tại.
        """
        return self.messages

    def set_data(self, key: str, value: Any):
        """
        Lưu dữ liệu tạm thời cho phiên làm việc.
        """
        self.session_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """
        Đọc dữ liệu tạm thời.
        """
        return self.session_data.get(key, default)

    def clear(self):
        """
        Làm sạch bộ nhớ ngắn hạn để bắt đầu phiên mới.
        """
        self.messages.clear()
        self.session_data.clear()
