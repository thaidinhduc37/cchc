import pyttsx3

class TextToSpeech:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 1)
        voices = self.engine.getProperty('voices')
        for voice in voices:
            if 'vi' in voice.languages or 'Vietnam' in voice.name:
                self.engine.setProperty('voice', voice.id)
                break

    def speak(self, text: str):
        self.engine.say(text)
        self.engine.runAndWait()