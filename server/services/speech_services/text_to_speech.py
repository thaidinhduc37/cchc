# services/speech_services/text_to_speech.py - Cải thiện version
import pyttsx3
import os
import logging
from gtts import gTTS
import pygame
import io
import threading
import time

logger = logging.getLogger(__name__)

class TextToSpeech:
    def __init__(self):
        self.engine = None
        self.use_gtts = True  # Ưu tiên Google TTS cho tiếng Việt
        self.use_pyttsx3_fallback = True
        self._init_engines()

    def _init_engines(self):
        """Khởi tạo các engine TTS"""
        try:
            # Khởi tạo pygame mixer cho gtts
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            logger.info("✅ Pygame mixer initialized for gTTS")
        except Exception as e:
            logger.warning(f"⚠️ Cannot init pygame mixer: {e}")
            self.use_gtts = False

        try:
            # Khởi tạo pyttsx3 như fallback
            self.engine = pyttsx3.init()
            self._configure_pyttsx3()
            logger.info("✅ pyttsx3 engine initialized")
        except Exception as e:
            logger.error(f"❌ Cannot init pyttsx3: {e}")
            self.use_pyttsx3_fallback = False

    def _configure_pyttsx3(self):
        """Cấu hình pyttsx3 cho tiếng Việt tốt nhất"""
        if not self.engine:
            return

        # Tốc độ nói chậm hơn để rõ ràng
        self.engine.setProperty('rate', 160)
        
        # Âm lượng tối đa
        self.engine.setProperty('volume', 1.0)
        
        # Tìm giọng nói tiếng Việt hoặc giọng nữ
        voices = self.engine.getProperty('voices')
        selected_voice = None
        
        # Ưu tiên 1: Giọng tiếng Việt
        for voice in voices:
            if voice.languages and any('vi' in lang.lower() for lang in voice.languages):
                selected_voice = voice
                logger.info(f"✅ Found Vietnamese voice: {voice.name}")
                break
        
        # Ưu tiên 2: Giọng nữ (thường nghe dễ hơn)
        if not selected_voice:
            for voice in voices:
                if 'female' in voice.name.lower() or 'woman' in voice.name.lower():
                    selected_voice = voice
                    logger.info(f"📢 Using female voice: {voice.name}")
                    break
        
        # Ưu tiên 3: Giọng chất lượng cao (Microsoft voices)
        if not selected_voice:
            for voice in voices:
                if 'microsoft' in voice.name.lower() or 'sapi' in voice.name.lower():
                    selected_voice = voice
                    logger.info(f"📢 Using Microsoft voice: {voice.name}")
                    break
        
        if selected_voice:
            self.engine.setProperty('voice', selected_voice.id)
        else:
            logger.warning("⚠️ No suitable voice found, using default")

    def speak_with_gtts(self, text: str) -> bool:
        """Sử dụng Google TTS (chất lượng tốt nhất cho tiếng Việt)"""
        try:
            # Tạo TTS object
            tts = gTTS(text=text, lang='vi', slow=False)
            
            # Chuyển đổi thành audio stream
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            # Phát âm thanh
            pygame.mixer.music.load(audio_buffer)
            pygame.mixer.music.play()
            
            # Đợi cho đến khi phát xong
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            logger.info("✅ gTTS speech completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ gTTS error: {e}")
            return False

    def speak_with_pyttsx3(self, text: str) -> bool:
        """Sử dụng pyttsx3 (offline, nhưng chất lượng tiếng Việt hạn chế)"""
        try:
            if not self.engine:
                return False
                
            self.engine.say(text)
            self.engine.runAndWait()
            logger.info("✅ pyttsx3 speech completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ pyttsx3 error: {e}")
            return False

    def speak(self, text: str):
        """Phương thức chính để nói - thử các engine theo thứ tự ưu tiên"""
        if not text or not text.strip():
            return

        text = text.strip()
        logger.info(f"🔊 Speaking: {text[:50]}...")

        def _speak_thread():
            success = False
            
            # Thử Google TTS trước (chất lượng tốt nhất)
            if self.use_gtts:
                success = self.speak_with_gtts(text)
                if success:
                    return
            
            # Fallback sang pyttsx3
            if self.use_pyttsx3_fallback:
                success = self.speak_with_pyttsx3(text)
                if success:
                    return
            
            logger.error("❌ All TTS engines failed")

        # Chạy trong thread riêng để không block
        thread = threading.Thread(target=_speak_thread, daemon=True)
        thread.start()

    def speak_async(self, text: str):
        """Phiên bản async của speak (không đợi)"""
        thread = threading.Thread(target=self.speak, args=(text,), daemon=True)
        thread.start()

    def stop(self):
        """Dừng phát âm"""
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except:
            pass
            
        try:
            if self.engine:
                self.engine.stop()
        except:
            pass

    def is_available(self) -> bool:
        """Kiểm tra xem TTS có khả dụng không"""
        return self.use_gtts or self.use_pyttsx3_fallback

    def get_status(self) -> dict:
        """Trả về trạng thái của các TTS engine"""
        return {
            "gtts_available": self.use_gtts,
            "pyttsx3_available": self.use_pyttsx3_fallback,
            "preferred_engine": "gtts" if self.use_gtts else "pyttsx3"
        }