from services.unified_processor import process_user_query
from services.speech_services.text_to_speech import TextToSpeech
from services.speech_services.speech_to_text import SpeechToText
from typing import Dict, Any
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AssistantUnifiedController")

class AssistantController:
    def __init__(self, domain: str = "xuatnhapcanh"):
        self.tts = TextToSpeech()
        self.stt = SpeechToText()
        self.domain = domain
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.exit_commands = ["xong", "kết thúc", "tắt", "thoát", "exit", "bye", "goodbye"]

    def start_assistant(self, user_id: str) -> Dict[str, Any]:
        logger.info(f"[Assistant] Khởi động trợ lý cho {user_id}")
        self.sessions[user_id] = {
            "start_time": time.time(),
            "last_interaction": time.time(),
            "context": {}
        }
        return {
            "text": "🎤 Trợ lý ảo đã sẵn sàng. Mời bạn nói câu hỏi.",
            "source": "assistant",
            "success": True
        }

    def next_step(self, user_id: str, user_input: str) -> Dict[str, Any]:
        lowered = user_input.strip().lower()

        if any(cmd in lowered for cmd in self.exit_commands):
            self.sessions.pop(user_id, None)
            return {
                "text": "✅ Trợ lý ảo đã tắt. Hẹn gặp lại!",
                "source": "assistant",
                "user_input": user_input,
                "done": True
            }

        if user_id not in self.sessions:
            return {
                "text": "⚠️ Bạn chưa khởi động trợ lý ảo. Vui lòng bấm nút mic trước.",
                "source": "assistant",
                "user_input": user_input,
                "success": False
            }

        try:
            self.sessions[user_id]["last_interaction"] = time.time()

            result = process_user_query(user_input, user_id, domain=self.domain)
            response_text = result.get("text", "Xin lỗi, tôi không có câu trả lời.")

            # Đọc lại phản hồi
            self.tts.speak(response_text)

            return {
                "text": response_text,
                "source": result.get("source", "assistant"),
                "user_input": user_input,
                "success": True
            }
        except Exception as e:
            logger.exception("❌ Lỗi trong assistant:")
            return {
                "text": "❌ Trợ lý gặp lỗi. Vui lòng thử lại.",
                "source": "assistant",
                "user_input": user_input,
                "success": False,
                "error": str(e)
            }
