# server/services/assistant_loop.py

from services.speech_services.speech_to_text import SpeechToText
from services.speech_services.text_to_speech import TextToSpeech
from services.unified_processor import process_user_query

class AssistantLoop:
    def __init__(self, domain="xuatnhapcanh"):
        self.domain = domain
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.running = False

    def start(self, user_id="default_user"):
        self.running = True
        print("🎤 Trợ lý ảo đã bật. Đang lắng nghe...")

        while self.running:
            text = self.stt.listen_and_transcribe().strip()
            print(f"👂 Bạn nói: {text}")

            if text.lower() in ["xong", "kết thúc", "tắt", "thoát"]:
                self.tts.speak("Trợ lý ảo đã dừng.")
                print("🛑 Trợ lý ảo kết thúc.")
                self.running = False
                break

            if text:
                response = process_user_query(user_input=text, user_id=user_id, domain=self.domain)
                print(f"🤖 Bot: {response}")
                self.tts.speak(response)
