import pyttsx3

class TextToSpeech:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1)

        # Thiết lập giọng Tiếng Việt nếu có
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'Vietnam' in voice.name or 'vi' in voice.languages:
                self.engine.setProperty('voice', voice.id)
                break

    def speak(self, text: str):
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Error in TTS: {e}")