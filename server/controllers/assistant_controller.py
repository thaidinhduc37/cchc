from services.ollama_service import OllamaService
from services.flow_engine import FlowEngine
from services.speech_services.text_to_speech import TextToSpeech
from services.speech_services.speech_to_text import SpeechToText

class AssistantController:
    def __init__(self, flow_path: str):
        self.engine = FlowEngine(flow_path)
        self.ollama = OllamaService()
        self.tts = TextToSpeech()
        self.stt = SpeechToText()
        self.user_steps = {}  # Lưu trạng thái bước theo user

    # ✅ API khởi động: gửi câu hỏi đầu tiên
    def start_assistant(self, user_id: str):
        first_step = self.engine.get_step("start")
        if not first_step:
            return {"error": "Không tìm thấy bước bắt đầu"}
        self.user_steps[user_id] = first_step.get("id")
        return {"step": first_step}

    # ✅ API bước tiếp theo: nhận trả lời, sinh phản hồi, điều phối bước
    def next_step(self, user_id: str, user_input: str):
        current_id = self.user_steps.get(user_id)
        if not current_id:
            return {"error": "Chưa khởi động trợ lý ảo"}

        # Gửi vào Ollama để tạo phản hồi
        response = self.ollama.ask(user_input)
        self.tts.speak(response)  # Đọc phản hồi

        # Lấy bước kế tiếp
        next_step = self.engine.get_next_step(current_id)
        if next_step:
            self.user_steps[user_id] = next_step.get("id")
            return {"reply": response, "next_step": next_step}
        else:
            return {"reply": response, "done": True}

    # ✅ Dùng để test thực tế bằng mic (CLI test)
    def run_assistant(self, user_id: str):
        print("🚀 Bắt đầu phiên trợ lý ảo (bằng giọng nói)...")
        step = self.engine.get_step("start")
        while step:
            question = step.get("question", "Hãy cung cấp thông tin:")
            print(f"[Trợ lý hỏi]: {question}")
            self.tts.speak(question)

            user_input = self.stt.listen_and_transcribe()
            print(f"[Người dùng]: {user_input}")

            response = self.ollama.ask(user_input)
            print(f"[Trợ lý]: {response}")
            self.tts.speak(response)

            step = self.engine.get_next_step(step.get("id"))
        print("✅ Kết thúc quy trình.")
