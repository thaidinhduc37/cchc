# controllers/chat_controller.py - Tối ưu tập trung Flow

from services.flow_engine import flow_engine
from services.unified_processor import process_user_query
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class ChatController:
    def __init__(self):
        self.flow_engine = flow_engine
        self.user_sessions = {}
        self._load_question_tree()

    def _load_question_tree(self):
        """Load question tree từ flow.json"""
        try:
            with open("dataset/xuatnhapcanh/flow.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.questions = {q["id"]: q for q in data.get("questions", [])}
                self.flows_info = data.get("flows", {})
            logger.info("✅ Loaded flow.json successfully")
        except Exception as e:
            logger.error(f"❌ Error loading flow.json: {e}")
            self.questions = {}
            self.flows_info = {}

    def handle_chat(self, user_id: str, message: str, domain: str = None) -> dict:
        """Xử lý chat - ưu tiên Flow trước"""
        
        # Khởi tạo session
        session = self.user_sessions.setdefault(user_id, {
            "mode": "normal",
            "current_answers": [],
            "current_question_id": None,
            "history": []
        })

        message_cleaned = message.strip()
        message_lower = message_cleaned.lower()
        
        # Lưu lịch sử
        session["history"].append({
            "user": message_cleaned, 
            "timestamp": datetime.now().isoformat()
        })

        # === PRIORITY 1: XỬ LÝ FLOW ĐANG CHẠY ===
        if self.flow_engine.is_in_flow(user_id):
            return self._handle_active_flow(user_id, message_lower)

        # === PRIORITY 2: XỬ LÝ QUESTION FLOW ===
        if session["mode"] == "question_flow":
            return self._handle_question_flow(user_id, message_cleaned, session)

        # === PRIORITY 3: KHỞI ĐỘNG FLOW ===
        if message_lower == "hướng dẫn quy trình":
            return self._start_question_flow(user_id, session)

        # Detect flow intent
        if self._is_flow_request(message_lower):
            return {
                "reply": "📌 Bạn muốn được hướng dẫn từng bước thực hiện thủ tục không?",
                "source": "chatbot",
                "show_flow_button": True,
                "button_label": "Hướng dẫn quy trình",
                "type": "guide_prompt"
            }

        # === PRIORITY 4: XỬ LÝ THÔNG THƯỜNG (RAG) ===
        domain = domain or "xuatnhapcanh"
        result = process_user_query(message_cleaned, user_id, domain)
        
        return {
            "reply": result.get('reply') or result.get('text', ''),
            "source": result.get("source", "unknown"),
            "type": "answer",
            "metadata": result.get("metadata", {}),
            "domain": domain
        }

    def _handle_active_flow(self, user_id: str, message_lower: str) -> dict:
        """Xử lý khi đang trong step flow"""
        flow_result = self.flow_engine.handle_user_input(user_id, message_lower)
        
        if flow_result.get("done"):
            self.flow_engine.reset(user_id)
            self.user_sessions[user_id]["mode"] = "normal"
            return {
                "reply": "✅ Bạn đã hoàn tất hướng dẫn!",
                "source": "flow",
                "type": "completed"
            }
        
        if "error" in flow_result:
            return {
                "reply": f"❌ {flow_result['error']}",
                "source": "flow",
                "type": "error"
            }
        
        # Format step response
        if "step" in flow_result:
            flow_id = self.flow_engine.user_progress[user_id].get("flow_id")
            flow_info = self.flows_info.get(flow_id, {})
            total_steps = len(flow_info.get("steps", {}))
            
            step = flow_result["step"]
            current = flow_result.get("current", "?")
            
            return {
                "reply": f"📋 **{flow_info.get('name', 'Hướng dẫn')}** – Bước {current}/{total_steps}\n\n{step.get('name', '')}",
                "source": "flow",
                "type": "step",
                "buttons": ["Tiếp tục", "Quay lại", "Kết thúc"],
                "step_mode": True,
                "flow_id": flow_id,
                "step_index": current,
                "total_steps": total_steps,
                "tts": step.get("tts"),
                "image": step.get("image"),
                "link": step.get("link")
            }
        
        return flow_result

    def _handle_question_flow(self, user_id: str, message: str, session: dict) -> dict:
        """Xử lý question flow"""
        # Lưu câu trả lời
        session["current_answers"].append({
            "question_id": session["current_question_id"],
            "option": message
        })
        
        # Tìm câu hỏi tiếp theo hoặc flow
        next_item = self._get_next_question_or_flow(session["current_answers"])
        
        if not next_item:
            session["mode"] = "normal"
            return {
                "reply": "❌ Không tìm thấy hướng dẫn phù hợp.",
                "source": "chatbot",
                "type": "error"
            }
        
        # Nếu là câu hỏi tiếp theo
        if isinstance(next_item, dict) and "question" in next_item:
            session["current_question_id"] = next_item["id"]
            return {
                "reply": next_item["question"],
                "source": "chatbot",
                "options": [opt["label"] for opt in next_item.get("options", [])],
                "type": "question"
            }
        
        # Nếu là flow - chuyển sang step flow
        elif isinstance(next_item, dict) and next_item.get("type") == "flow":
            session["mode"] = "normal"  # Reset question mode
            return self._start_step_flow(user_id, next_item["flow_id"])

    def _start_question_flow(self, user_id: str, session: dict) -> dict:
        """Bắt đầu question flow"""
        session["mode"] = "question_flow"
        session["current_answers"] = []
        session["current_question_id"] = "start"
        
        start_question = self.questions.get("start")
        if start_question:
            return {
                "reply": start_question["question"],
                "source": "chatbot",
                "options": [opt["label"] for opt in start_question.get("options", [])],
                "type": "question"
            }
        
        return {
            "reply": "❌ Không tìm thấy câu hỏi bắt đầu.",
            "source": "chatbot",
            "type": "error"
        }

    def _start_step_flow(self, user_id: str, flow_id: str) -> dict:
        """Bắt đầu step flow"""
        flow_info = self.flows_info.get(flow_id, {})
        steps = flow_info.get("steps", {})
        
        # Nếu flow không có steps
        if not steps:
            description = flow_info.get("description", "Tính năng này đang được phát triển.")
            return {
                "reply": f"ℹ️ **{flow_info.get('name', 'Thông báo')}**\n\n{description}",
                "source": "chatbot",
                "type": "info"
            }
        
        # Bắt đầu step flow
        result = self.flow_engine.start_flow(user_id, flow_id)
        if "error" in result:
            return {
                "reply": f"❌ {result['error']}",
                "source": "chatbot",
                "type": "error"
            }
        
        # Format step response
        total_steps = len(steps)
        step = result.get("step", {})
        current = result.get("current", "1")
        
        return {
            "reply": f"📋 **{flow_info.get('name', 'Hướng dẫn')}** – Bước {current}/{total_steps}\n\n{step.get('name', '')}",
            "source": "flow",
            "type": "step",
            "buttons": ["Tiếp tục", "Quay lại", "Kết thúc"],
            "step_mode": True,
            "flow_id": flow_id,
            "step_index": current,
            "total_steps": total_steps,
            "tts": step.get("tts"),
            "image": step.get("image"),
            "link": step.get("link")
        }

    def _get_next_question_or_flow(self, current_answers: list):
        """Tìm câu hỏi tiếp theo hoặc flow dựa trên answers"""
        if not current_answers:
            return self.questions.get("start")
        
        last_answer = current_answers[-1]
        current_question_id = last_answer.get("question_id")
        selected_option = last_answer.get("option")
        
        current_question = self.questions.get(current_question_id)
        if not current_question:
            return None
        
        # Tìm option được chọn
        for option in current_question.get("options", []):
            if option["label"] == selected_option:
                if "next" in option:
                    return self.questions.get(option["next"])
                elif "flow" in option:
                    return {"type": "flow", "flow_id": option["flow"]}
        
        return None

    def _is_flow_request(self, message: str) -> bool:
        """Kiểm tra có phải yêu cầu hướng dẫn không"""
        flow_keywords = [
            "hướng dẫn", "quy trình", "trình tự", "các bước", "thủ tục",
            "hướng dẫn làm", "hướng dẫn thủ tục"
        ]
        return any(kw in message for kw in flow_keywords)