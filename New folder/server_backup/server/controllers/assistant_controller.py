# assistant_controller.py - Enhanced version
from services.unified_processor import process_user_query
from services.speech_services.text_to_speech import TextToSpeech
from services.speech_services.speech_to_text import SpeechToText
from typing import Dict, Any
import logging
import time
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AssistantUnifiedController")

class AssistantController:
    def __init__(self, domain: str = "xuatnhapcanh"):
        self.tts = TextToSpeech()
        self.stt = SpeechToText()
        self.domain = domain
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.exit_commands = ["xong", "kết thúc", "tắt", "thoát", "exit", "bye", "goodbye", "dừng lại"]
        
        # Cấu hình TTS
        self.tts_enabled = True
        self.auto_speak = True  # Tự động đọc phản hồi

    def start_assistant(self, user_id: str, enable_tts: bool = True) -> Dict[str, Any]:
        """Khởi động trợ lý với tùy chọn bật/tắt TTS"""
        logger.info(f"[Assistant] Khởi động trợ lý cho {user_id}")
        
        self.sessions[user_id] = {
            "start_time": time.time(),
            "last_interaction": time.time(),
            "context": {},
            "tts_enabled": enable_tts,
            "conversation_count": 0
        }
        
        welcome_message = "🎤 Trợ lý ảo đã sẵn sàng. Mời bạn nói câu hỏi hoặc gõ tin nhắn."
        
        # Đọc lời chào mở đầu
        if enable_tts and self.tts.is_available():
            self.tts.speak_async(welcome_message)
        
        return {
            "text": welcome_message,
            "source": "assistant",
            "success": True,
            "tts_status": self.tts.get_status()
        }

    def toggle_tts(self, user_id: str, enabled: bool) -> Dict[str, Any]:
        """Bật/tắt TTS cho session"""
        if user_id in self.sessions:
            self.sessions[user_id]["tts_enabled"] = enabled
            status = "bật" if enabled else "tắt"
            message = f"Đã {status} chức năng đọc tin nhắn."
            
            if enabled and self.tts.is_available():
                self.tts.speak_async(message)
                
            return {
                "text": message,
                "source": "assistant",
                "success": True,
                "tts_enabled": enabled
            }
        
        return {
            "text": "Phiên làm việc không tồn tại.",
            "source": "assistant",
            "success": False
        }

    def _clean_text_for_speech(self, text: str) -> str:
        """Làm sạch text để TTS đọc tốt hơn"""
        # Loại bỏ emoji và ký tự đặc biệt
        text = re.sub(r'[🎤🤖✅❌⚠️📝🔊👂🛑]', '', text)
        
        # Thay thế một số từ viết tắt
        replacements = {
            'CCCD': 'Căn cước công dân',
            'CMND': 'Chứng minh nhân dân',
            'VNeID': 'Vê nê ID',
            'QR': 'cửu a',
            'SMS': 'S M S',
            'OTP': 'O T P'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Loại bỏ khoảng trắng thừa
        text = ' '.join(text.split())
        
        return text

    def next_step(self, user_id: str, user_input: str) -> Dict[str, Any]:
        """Xử lý bước tiếp theo trong cuộc hội thoại"""
        lowered = user_input.strip().lower()

        # Kiểm tra lệnh thoát
        if any(cmd in lowered for cmd in self.exit_commands):
            session = self.sessions.pop(user_id, None)
            farewell_message = "✅ Trợ lý ảo đã tắt. Hẹn gặp lại!"
            
            # Đọc lời tạm biệt
            if session and session.get("tts_enabled", True):
                self.tts.speak_async(farewell_message)
            
            return {
                "text": farewell_message,
                "source": "assistant",
                "user_input": user_input,
                "done": True
            }

        # Kiểm tra session
        if user_id not in self.sessions:
            return {
                "text": "⚠️ Bạn chưa khởi động trợ lý ảo. Vui lòng bấm nút mic trước.",
                "source": "assistant",
                "user_input": user_input,
                "success": False
            }

        # Kiểm tra lệnh điều khiển TTS
        if "tắt giọng nói" in lowered or "dừng nói" in lowered:
            return self.toggle_tts(user_id, False)
        elif "bật giọng nói" in lowered or "mở giọng nói" in lowered:
            return self.toggle_tts(user_id, True)

        try:
            # Cập nhật thông tin session
            session = self.sessions[user_id]
            session["last_interaction"] = time.time()
            session["conversation_count"] += 1

            # Xử lý query
            result = process_user_query(user_input, user_id, domain=self.domain)
            response_text = result.get("text", "Xin lỗi, tôi không có câu trả lời.")

            # Làm sạch text và đọc phản hồi nếu TTS được bật
            if session.get("tts_enabled", True) and self.tts.is_available():
                clean_text = self._clean_text_for_speech(response_text)
                self.tts.speak_async(clean_text)

            return {
                "text": response_text,
                "source": result.get("source", "assistant"),
                "user_input": user_input,
                "success": True,
                "conversation_count": session["conversation_count"],
                "session_duration": time.time() - session["start_time"]
            }
            
        except Exception as e:
            logger.exception("❌ Lỗi trong assistant:")
            error_message = "❌ Trợ lý gặp lỗi. Vui lòng thử lại."
            
            # Đọc thông báo lỗi
            session = self.sessions.get(user_id, {})
            if session.get("tts_enabled", True):
                self.tts.speak_async("Xin lỗi, tôi gặp lỗi kỹ thuật. Vui lòng thử lại.")
            
            return {
                "text": error_message,
                "source": "assistant",
                "user_input": user_input,
                "success": False,
                "error": str(e)
            }

    def get_session_info(self, user_id: str) -> Dict[str, Any]:
        """Lấy thông tin session"""
        if user_id not in self.sessions:
            return {"exists": False}
        
        session = self.sessions[user_id]
        return {
            "exists": True,
            "start_time": session["start_time"],
            "last_interaction": session["last_interaction"],
            "conversation_count": session["conversation_count"],
            "tts_enabled": session.get("tts_enabled", True),
            "duration": time.time() - session["start_time"],
            "tts_status": self.tts.get_status()
        }

    def stop_all_speech(self):
        """Dừng tất cả phát âm"""
        self.tts.stop()

    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Dọn dẹp các session cũ"""
        current_time = time.time()
        old_sessions = []
        
        for user_id, session in self.sessions.items():
            age_hours = (current_time - session["start_time"]) / 3600
            if age_hours > max_age_hours:
                old_sessions.append(user_id)
        
        for user_id in old_sessions:
            self.sessions.pop(user_id, None)
            logger.info(f"Cleaned up old session for {user_id}")
        
        return len(old_sessions)