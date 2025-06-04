# --- 🔧 FULLY FIXED chat_controller.py ---
from services.flow_engine import FlowEngine
from services.unified_processor import process_user_query
from utils.context_manager import ContextManager

class ChatController:
    def __init__(self):
        self.context_manager = ContextManager()
        self.flow_engine = FlowEngine()
        self.user_sessions = {}

    def handle_chat(self, user_id: str, message: str, domain: str = "xuatnhapcanh") -> dict:
        context = self.user_sessions.setdefault(user_id, {
            "mode": "question",
            "answers": [],
            "current_id": "start",
            "current_flow": None,
            "current_step_index": 0
        })

        message_lower = message.strip().lower()

        # ✅ 1. Nếu đang trong flow step-by-step
        if context["mode"] == "step":
            if message_lower in ["tiếp tục", "next"]:
                context["current_step_index"] += 1
            elif message_lower in ["quay lại", "back"]:
                context["current_step_index"] = max(0, context["current_step_index"] - 1)

            step_list = self.flow_engine.get_steps(context["current_flow"])
            if context["current_step_index"] >= len(step_list):
                context["mode"] = "question"
                return {"reply": "✅ Bạn đã hoàn tất các bước.", "source": "chatbot"}

            step_id = step_list[context["current_step_index"]]
            step_text = self.flow_engine.get_step_text(step_id)

            return {
                "reply": f"Bước {step_id}: {step_text}",
                "source": "chatbot",
                "step_mode": True,
                "show_back": context["current_step_index"] > 0,
                "show_next": context["current_step_index"] < len(step_list) - 1
            }

        # ✅ 2. Nếu khởi động flow qua nút "Hướng dẫn quy trình"
        if message_lower in ["hướng dẫn quy trình", "xem quy trình"]:
            context.update({"mode": "question", "answers": [], "current_id": "start"})
            result = self.flow_engine.navigate(context["answers"])

            # 🔧 PATCH: Nếu result là None, kiểm tra trực tiếp option.flow trong current_id
            if result is None and context["answers"]:
                last = context["answers"][-1]
                question = self.flow_engine.get_question_by_id(last["id"])
                if question:
                    for opt in question.get("options", []):
                        if opt["label"].strip().lower() == last["option"].strip().lower() and "flow" in opt:
                            result = opt["flow"]
                            break
            if isinstance(result, dict):
                context["current_id"] = result["id"]
                return {
                    "reply": result.get("question", "Xin chọn tiếp:"),
                    "source": "chatbot",
                    "options": [opt["label"] for opt in result.get("options", [])]
                }
            return {"reply": "❌ Không tìm thấy quy trình.", "source": "chatbot"}

        # ✅ 3. Đang ở trạng thái chọn lựa option từ question-id
        if context["mode"] == "question":
            context["answers"].append({"id": context["current_id"], "option": message})
            result = self.flow_engine.navigate(context["answers"])

            # ✅ Nếu navigate trả về None, kiểm tra xem option có flow không
            if result is None and context["answers"]:
                last = context["answers"][-1]
                question = self.flow_engine.get_question_by_id(last["id"])
                if question:
                    for opt in question.get("options", []):
                        if opt["label"] == last["option"] and "flow" in opt:
                            result = opt["flow"]
                            break

            if isinstance(result, dict):
                context["current_id"] = result["id"]
                return {
                    "reply": result.get("question", "Xin chọn tiếp:"),
                    "source": "chatbot",
                    "options": [opt["label"] for opt in result.get("options", [])]
                }
            elif isinstance(result, str) and result in self.flow_engine.get_all_flows():
                context["mode"] = "step"
                context["current_flow"] = result
                context["current_step_index"] = 0
                step_text = self.flow_engine.get_step_content(result, 0)
                return {
                    "reply": f"Bước 1: {step_text}",
                    "step_mode": True,
                    "source": "chatbot"
                }
            elif isinstance(result, str):
                return {"reply": "❌ Không hiểu lựa chọn hoặc flow không hợp lệ.", "source": "chatbot"}

        # ✅ 4. Nếu người dùng hỏi bằng từ khóa
        keywords = ["quy trình", "các bước", "hướng dẫn", "thủ tục"]
        if any(kw in message_lower for kw in keywords):
            return {
                "reply": "📌 Bạn muốn xem hướng dẫn quy trình không?",
                "source": "chatbot",
                "show_flow_button": True
            }

        # ✅ 5. Fallback dùng AI
        result = process_user_query(message, user_id, domain)
        if not isinstance(result, dict) or "text" not in result:
            return {"reply": "⚠️ Hệ thống gặp lỗi khi xử lý câu hỏi.", "source": "error"}

        self.context_manager.update_context(user_id, message, result)
        return {"reply": result["text"], "source": result.get("source", "unknown")}
