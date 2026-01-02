import speech_recognition as sr

class SpeechToText:
    def __init__(self):
        self.recognizer = sr.Recognizer()

    def listen_and_transcribe(self) -> str:
        try:
            with sr.Microphone() as source:
                print("Đang lắng nghe...")
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source, timeout=5)
                return self.recognizer.recognize_google(audio, language="vi-VN")
        except sr.UnknownValueError:
            return "Không nghe rõ, vui lòng nói lại."
        except sr.RequestError:
            return "Không thể kết nối đến dịch vụ nhận diện giọng nói."
        except Exception as e:
            print(f"Lỗi STT: {e}")
            return ""
