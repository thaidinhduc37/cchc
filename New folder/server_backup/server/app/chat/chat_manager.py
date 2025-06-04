# app/chat/chat_manager.py
import json
from datetime import datetime

class ChatManager:
    def __init__(self):
        self.contexts = {}

    def get_context(self, user_id):
        return self.contexts.get(user_id, [])

    def update_context(self, user_id, message):
        if user_id not in self.contexts:
            self.contexts[user_id] = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.contexts[user_id].append({"timestamp": timestamp, "message": message})

    def clear_context(self, user_id):
        if user_id in self.contexts:
            del self.contexts[user_id]

    def save_context(self, user_id):
        with open(f"data/context_{user_id}.json", "w", encoding="utf-8") as f:
            json.dump(self.contexts.get(user_id, []), f, ensure_ascii=False, indent=4)
