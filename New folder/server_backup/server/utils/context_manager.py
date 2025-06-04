# server/utils/context_manager.py

class ContextManager:
    def __init__(self):
        self.context = {}

    def update_context(self, user_id, message, result):
        self.context.setdefault(user_id, []).append({
            "message": message,
            "reply": result.get("text", ""),
            "source": result.get("source", "")
        })

    def get_history(self, user_id):
        return self.context.get(user_id, [])
