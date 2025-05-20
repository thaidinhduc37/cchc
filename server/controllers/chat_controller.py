from services.ollama_service import OllamaService
from utils.context_manager import ContextManager
from utils.prompt_builder import build_prompt
from utils.response_formatter import format_response
from services.vector_db import VectorDatabase  # 🟢 thêm

class ChatController:
    def __init__(self):
        self.ollama = OllamaService()
        self.context_manager = ContextManager()
        self.vector_db = VectorDatabase()
        self.default_domain = "cancuoc"  # 🟢 có thể mở rộng về sau

    def handle_chat(self, user_id: str, message: str) -> str:
        # Bước 1: lấy ngữ cảnh hội thoại
        context = self.context_manager.get_context(user_id)

        # Bước 2: tìm kiếm dữ liệu có liên quan trong vector
        results = self.vector_db.search(self.default_domain, message)

        retrieved_text = ""
        if results:
            for i, (doc, score) in enumerate(results):
                retrieved_text += f"[Tài liệu {i+1} - độ liên quan {round(score,2)}]:\n{doc}\n\n"

        # Bước 3: tạo prompt gồm ngữ cảnh + dữ liệu
        prompt = ""
        if retrieved_text:
            prompt += f"Đây là một số thông tin liên quan được tìm thấy:\n{retrieved_text}\n\n"
        prompt += build_prompt(message, context)

        # Bước 4: gửi đến mô hình Genma/Gemma
        raw_response = self.ollama.ask(prompt)
        response = format_response(raw_response)

        # Bước 5: lưu lại hội thoại
        self.context_manager.update_context(user_id, message, response)

        return response
