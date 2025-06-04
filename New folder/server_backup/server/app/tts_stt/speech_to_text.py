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
                text = self.recognizer.recognize_google(audio, language="vi-VN")
                print(f"Đã nhận dạng: {text}")
                return text
        except sr.UnknownValueError:
            return "Không nhận diện được giọng nói."
        except sr.RequestError:
            return "Không thể kết nối dịch vụ nhận diện giọng nói."
        except Exception as e:
            print(f"Error in STT: {e}")
            return ""