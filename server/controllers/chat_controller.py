# chat_controller.py - Bản cải tiến + sử dụng intent từ unified_processor

from services.flow_engine import flow_engine
from services.unified_processor import process_user_query, detect_flow_intent
from utils.context_manager import ContextManager
from datetime import datetime

class ChatController:
    def __init__(self):
        self.context_manager = ContextManager()
        self.flow_engine = flow_engine
        self.user_sessions = {}

    def _format_step_response(self, flow_result):
        step = flow_result.get("step", {})
        current = flow_result.get("current", "?")
        total = flow_result.get("total", "?")
        flow_name = flow_result.get("flow_name", "Hướng dẫn")

        header = f"📋 **{flow_name}** – Bước {current}/{total}\n\n"
        content = step.get("name", step.get("description", ""))
        footer = ""
        # footer = ("\n\n💡 **Bạn có thể nói:**\n"
        #           "• 'tiếp tục' để sang bước tiếp theo\n"
        #           "• 'quay lại' để về bước trước\n"
        #           "• 'dừng' để kết thúc hướng dẫn")

        return {
            "reply": header + content + footer,
            "tts": step.get("tts", content),
            "image": step.get("image"),
            "link": step.get("link"),
            "flow_id": flow_result.get("flow_id"),
            "step_index": current,
            "total_steps": total,
            "wait_for_user": flow_result.get("wait_for_user", True),
            "step_mode": True,
            "source": "chatbot",
            "type": "step"
        }

    def handle_chat(self, user_id: str, message: str, domain: str = "xuatnhapcanh") -> dict:
        context = self.user_sessions.setdefault(user_id, {
            "mode": "question",
            "answers": [],
            "current_id": "start",
            "current_flow": None,
            "current_step_index": 0,
            "history": []
        })

        message_cleaned = message.strip()
        message_lower = message_cleaned.lower()

        context["history"].append({"user": message_cleaned, "timestamp": self._get_timestamp()})

        # ✅ 1. Nếu đang trong flow step-by-step
        if self.flow_engine.is_in_flow(user_id):
            flow_result = self.flow_engine.handle_user_input(user_id, message_lower)

            if flow_result.get("done"):
                self.flow_engine.reset(user_id)
                return {
                    "reply": flow_result.get("message", "✅ Bạn đã hoàn tất các bước."),
                    "tts": flow_result.get("message", "✅ Bạn đã hoàn tất các bước."),
                    "done": True,
                    "source": "chatbot",
                    "type": "info"
                }

            if "error" in flow_result:
                return {
                    "reply": f"❌ {flow_result['error']}",
                    "tts": flow_result['error'],
                    "source": "chatbot",
                    "type": "error"
                }

            return self._format_step_response(flow_result)

        # ✅ 2. Phát hiện ý định hướng dẫn + loại thủ tục
        intent = detect_flow_intent(message_lower)
        if intent.get("has_guide_intent"):
            # Ánh xạ intent thành flow_id cụ thể
            flow_id = "cap_moi_tu_14"  # Mặc định nếu không rõ
            if intent.get("age_group") == "under_14":
                flow_id = "cap_con_duoi_14"
            elif intent.get("procedure_type") == "bị mất":
                flow_id = "cap_doi_mat_the"
            elif intent.get("procedure_type") == "cấp lại":
                flow_id = "cap_lai"
            elif intent.get("procedure_type") == "lần đầu":
                flow_id = "cap_moi_tu_14"

            result = self.flow_engine.start_flow(user_id, flow_id)
            if result.get("done") or result.get("error"):
                return {
                    "reply": result.get("message", result.get("error", "❌ Không thể bắt đầu flow.")),
                    "tts": result.get("message", result.get("error", "")),
                    "source": "chatbot",
                    "done": True,
                    "type": "info"
                }
            return self._format_step_response(result)

        # ✅ 3. Nếu là câu hỏi thông thường → xử lý truy vấn như cũ
        result = process_user_query(message_cleaned, user_id, domain)
        if not isinstance(result, dict) or "text" not in result:
            return {
                "reply": "⚠️ Hệ thống gặp lỗi khi xử lý câu hỏi.",
                "tts": "Hệ thống gặp lỗi khi xử lý câu hỏi.",
                "source": "error",
                "type": "error"
            }

        if self.context_manager:
            self.context_manager.update_context(user_id, message_cleaned, result)

        reply = result["text"]
        if any(k in message_lower for k in ["hộ chiếu", "thủ tục", "làm"]):
            reply += "\n\n💡 **Bạn có muốn được hướng dẫn từng bước không?**\nNói '**hướng dẫn**' để bắt đầu!"

        return {
            "reply": reply,
            "tts": result.get("tts", reply),
            "source": result.get("source", "unknown"),
            "type": "answer"
        }

    def _get_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
