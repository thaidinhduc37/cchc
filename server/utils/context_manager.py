import os
import json

class ContextManager:
    def __init__(self, base_path="dataset/context"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def get_context(self, user_id: str) -> list:
        path = os.path.join(self.base_path, f"{user_id}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def update_context(self, user_id: str, user_msg: str, bot_reply: str):
        path = os.path.join(self.base_path, f"{user_id}.json")
        history = self.get_context(user_id)
        history.append({"user": user_msg, "bot": bot_reply})
        with open(path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def clear_context(self, user_id: str):
        path = os.path.join(self.base_path, f"{user_id}.json")
        if os.path.exists(path):
            os.remove(path)
