import speech_recognition as sr
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SpeechToText:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.timeout = 5
        self.language = "vi-VN"

    def listen_and_transcribe(self) -> dict:
        """Return both text and status for better error handling"""
        try:
            with sr.Microphone() as source:
                logging.info("Đang lắng nghe...")
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source, timeout=self.timeout)
                text = self.recognizer.recognize_google(audio, language=self.language)
                logging.info(f"Đã nhận dạng: {text}")
                return {
                    "success": True,
                    "text": text,
                    "error": None
                }

        except sr.UnknownValueError:
            error_msg = "Không nhận diện được giọng nói"
            logging.warning(error_msg)
            return {
                "success": False,
                "text": None,
                "error": error_msg
            }

        except sr.RequestError as e:
            error_msg = f"Lỗi kết nối dịch vụ Google STT: {str(e)}"
            logging.error(error_msg)
            return {
                "success": False,
                "text": None,
                "error": error_msg
            }

        except Exception as e:
            error_msg = f"Lỗi không xác định: {str(e)}"
            logging.error(error_msg)
            return {
                "success": False,
                "text": None,
                "error": error_msg
            }