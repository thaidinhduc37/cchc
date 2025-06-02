# chat_controller.py - Phiên bản cải tiến với luồng hướng dẫn hoàn chỉnh

from services.flow_engine import flow_engine
from services.unified_processor import process_user_query, detect_flow_intent
from utils.context_manager import ContextManager
from datetime import datetime
import json

class ChatController:
    def __init__(self):
        self.context_manager = ContextManager()
        self.flow_engine = flow_engine
        self.user_sessions = {}
        # Load question tree từ flow.json
        self._load_question_tree()

        self.domain_mapping = {
            "xuatnhapcanh": ["hộ chiếu", "passport", "xuất nhập cảnh", "visa"],
            "cancuoc": ["căn cước", "cccd", "chứng minh thư", "định danh"],
            "dangkyxe": ["đăng ký xe", "biển số", "xe máy", "ô tô", "phương tiện"],
            "cutru": ["thường trú", "tạm trú", "cư trú", "hộ khẩu", "lưu trú"]
        }

    def _load_question_tree(self):
        """Load question tree từ flow.json"""
        try:
            with open("dataset/xuatnhapcanh/flow.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.questions = {q["id"]: q for q in data.get("questions", [])}
                self.flows_info = data.get("flows", {})
        except Exception as e:
            print(f"⚠️ Lỗi load question tree: {e}")
            self.questions = {}
            self.flows_info = {}

    def _extract_keyword_from_message(self, message: str) -> str:
        """Trích xuất từ khóa chính từ tin nhắn của người dùng"""
        lowered = message.lower()
        
        # Danh sách từ khóa ưu tiên
        keywords_map = {
            "hộ chiếu": ["hộ chiếu", "passport"],
            "căn cước": ["căn cước", "cccd", "chứng minh thư"],
            "đăng ký xe": ["đăng ký xe", "biển số xe"],
            "thường trú": ["thường trú", "tạm trú", "cư trú"]
        }
        
        for main_keyword, variations in keywords_map.items():
            if any(var in lowered for var in variations):
                return main_keyword
        
        # Mặc định trả về hộ chiếu
        return "hộ chiếu"

    def _detect_guide_intent(self, message: str) -> bool:
        lowered = message.lower().strip()
        # Chỉ hướng dẫn khi thực sự rõ ý định, đừng dùng mấy từ như "làm", "cấp", "xin"
        guide_phrases = [
            "hướng dẫn", "quy trình", "trình tự", "các bước", "thủ tục", "bước thực hiện"
        ]
        # True nếu câu bắt đầu bằng hoặc có nguyên cụm này (tách biệt)
        return (
            any(lowered.startswith(kw) for kw in guide_phrases)
            or any(phrase in lowered for phrase in [
                "hướng dẫn làm", "hướng dẫn thủ tục", "hướng dẫn quy trình", "các bước thực hiện"
            ])
        )

    def _format_step_response(self, flow_result):
        """Format response cho step trong flow"""
        step = flow_result.get("step", {})
        current = flow_result.get("current", "?")
        total = flow_result.get("total", "?")
        flow_name = flow_result.get("flow_name", "Hướng dẫn")

        header = f"📋 **{flow_name}** – Bước {current}/{total}\n\n"
        content = step.get("name", step.get("description", ""))

        return {
            "reply": header + content,
            "tts": step.get("tts", content),
            "image": step.get("image"),
            "link": step.get("link"),
            "flow_id": flow_result.get("flow_id"),
            "step_index": current,
            "total_steps": total,
            "wait_for_user": flow_result.get("wait_for_user", True),
            "step_mode": True,
            "source": "chatbot",
            "type": "step",
            "buttons": ["Tiếp tục", "Quay lại", "Kết thúc"]
        }

    def _get_question_by_id(self, question_id: str):
        """Lấy câu hỏi theo ID"""
        return self.questions.get(question_id)

    def _get_next_question_or_flow(self, current_answers: list):
        """Dựa trên các câu trả lời để tìm câu hỏi tiếp theo hoặc flow"""
        if not current_answers:
            return self._get_question_by_id("start")
        
        # Lấy câu trả lời cuối cùng
        last_answer = current_answers[-1]
        current_question_id = last_answer.get("question_id")
        selected_option = last_answer.get("option")
        
        # Tìm question hiện tại
        current_question = self._get_question_by_id(current_question_id)
        if not current_question:
            return None
        
        # Tìm option được chọn
        for option in current_question.get("options", []):
            if option["label"] == selected_option:
                if "next" in option:
                    # Chuyển đến câu hỏi tiếp theo
                    return self._get_question_by_id(option["next"])
                elif "flow" in option:
                    # Chuyển đến flow
                    return {"type": "flow", "flow_id": option["flow"]}
        
        return None

    def _start_flow_from_id(self, user_id: str, flow_id: str):
        """Bắt đầu flow từ flow_id"""
        flow_info = self.flows_info.get(flow_id, {})
        steps = flow_info.get("steps", {})
        
        # Nếu flow không có steps hoặc steps rỗng, trả về description
        if not steps or len(steps) == 0:
            description = flow_info.get("description", "Tính năng này đang được phát triển.")
            return {
                "reply": f"ℹ️ **{flow_info.get('name', 'Thông báo')}**\n\n{description}",
                "tts": description,
                "source": "chatbot",
                "type": "info"
            }
        
        # Bắt đầu flow bình thường
        result = self.flow_engine.start_flow(user_id, flow_id)
        if "error" in result:
            return {
                "reply": f"❌ {result['error']}",
                "tts": result['error'],
                "source": "chatbot",
                "type": "error"
            }
        
        # Thêm thông tin tổng số bước
        total_steps = len(steps)
        result["total"] = total_steps
        result["flow_name"] = flow_info.get("name", "Hướng dẫn")
        
        return self._format_step_response(result)

    def handle_chat(self, user_id: str, message: str, domain: str = None) -> dict:
        # Khởi tạo context cho user
        context = self.user_sessions.setdefault(user_id, {
            "mode": "normal",  # normal, question_flow, step_flow
            "current_answers": [],
            "current_question_id": None,
            "history": []
        })

        message_cleaned = message.strip()
        message_lower = message_cleaned.lower()
        
        # Lưu lịch sử
        context["history"].append({
            "user": message_cleaned, 
            "timestamp": self._get_timestamp()
        })

        # Xử lý khi đang trong step flow (hướng dẫn từng bước)
        if self.flow_engine.is_in_flow(user_id):
            flow_result = self.flow_engine.handle_user_input(user_id, message_lower)
            
            if flow_result.get("done"):
                self.flow_engine.reset(user_id)
                context["mode"] = "normal"
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
            
            # Thêm thông tin tổng số bước cho flow đang chạy
            if "step" in flow_result:
                flow_id = self.flow_engine.user_progress[user_id].get("flow_id")
                flow_info = self.flows_info.get(flow_id, {})
                total_steps = len(flow_info.get("steps", {}))
                flow_result["total"] = total_steps
                flow_result["flow_name"] = flow_info.get("name", "Hướng dẫn")
            
            return self._format_step_response(flow_result)

        # Xử lý khi bấm nút "Hướng dẫn quy trình"
        if message_lower == "hướng dẫn quy trình":
            context["mode"] = "question_flow"
            context["current_answers"] = []
            context["current_question_id"] = "start"
            
            start_question = self._get_question_by_id("start")
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

        # Xử lý khi đang trong question flow
        if context["mode"] == "question_flow":
            # Lưu câu trả lời
            context["current_answers"].append({
                "question_id": context["current_question_id"],
                "option": message_cleaned
            })
            
            # Tìm câu hỏi tiếp theo hoặc flow
            next_item = self._get_next_question_or_flow(context["current_answers"])
            
            if not next_item:
                context["mode"] = "normal"
                return {
                    "reply": "❌ Không tìm thấy hướng dẫn phù hợp.",
                    "source": "chatbot",
                    "type": "error"
                }
            
            # Nếu là câu hỏi tiếp theo
            if isinstance(next_item, dict) and "question" in next_item:
                context["current_question_id"] = next_item["id"]
                return {
                    "reply": next_item["question"],
                    "source": "chatbot",
                    "options": [opt["label"] for opt in next_item.get("options", [])],
                    "type": "question"
                }
            
            # Nếu là flow
            elif isinstance(next_item, dict) and next_item.get("type") == "flow":
                context["mode"] = "step_flow"
                flow_id = next_item["flow_id"]
                return self._start_flow_from_id(user_id, flow_id)

        # Phát hiện ý định hướng dẫn từ tin nhắn thường
        if self._detect_guide_intent(message_cleaned):
            keyword = self._extract_keyword_from_message(message_cleaned)
            
            return {
                "reply": f"📌 Tôi sẽ hướng dẫn cho bạn các quy trình thực hiện {keyword} nhé",
                "source": "chatbot",
                "show_flow_button": True,
                "button_label": "Hướng dẫn quy trình",
                "type": "guide_prompt"
            }

        # Tự động phát hiện domain nếu không được chỉ định
        if not domain:
            domain = self._detect_domain(message_cleaned)

        # ✅ Xử lý câu hỏi thông thường với RAG
        result = process_user_query(message_cleaned, user_id, domain)
        
        # ✅ Xử lý kết quả từ unified_processor
        if isinstance(result, dict):
            # Lấy text từ 'reply' hoặc 'text'
            reply_text = result.get('reply') or result.get('text', '')
            
            if result.get('source') == 'rag' and result.get('metadata'):
                # Xử lý kết quả RAG với metadata
                metadata = result.get('metadata', {})
                
               

                # Thêm confidence score
                if metadata.get('confidence'):
                    confidence = metadata['confidence']
                    try:
                        confidence = float(confidence)
                        if confidence >= 0.8:
                            reply_text += "\n\n✅ *Độ tin cậy: Cao*"
                        elif confidence >= 0.5:
                            reply_text += "\n\n⚠️ *Độ tin cậy: Trung bình*"
                        else:
                            reply_text += "\n\n❗ *Độ tin cậy: Thấp*"
                    except (ValueError, TypeError):
                        pass
            return {
                "reply": reply_text,
                "tts": result.get("tts", reply_text),
                "source": result.get("source", "unknown"),
                "type": "answer",
                "metadata": result.get("metadata", {}),
                "domain": domain,
                # Giữ lại các trường đặc biệt nếu có
                **{k: v for k, v in result.items() if k in [
                    'show_flow_button', 'button_label', 'buttons'
                ]}
            }

        # Fallback nếu không có kết quả
        return {
            "reply": "Xin lỗi, tôi không tìm thấy thông tin phù hợp.",
            "source": "error",
            "type": "answer",
            "domain": domain
        }

    def _get_timestamp(self):
        """Lấy timestamp hiện tại"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _detect_domain(self, message: str) -> str:
        """Phát hiện domain từ nội dung tin nhắn"""
        lowered = message.lower()
        
        # Tìm domain phù hợp nhất
        max_matches = 0
        detected_domain = "xuatnhapcanh"  # default domain
        
        for domain, keywords in self.domain_mapping.items():
            matches = sum(1 for k in keywords if k in lowered)
            if matches > max_matches:
                max_matches = matches
                detected_domain = domain
                
        return detected_domain

    def _update_chat_history(self, user_id: str, message: str, response: dict):
        """Cập nhật lịch sử chat cho RAG"""
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {"history": []}
            
        history = self.user_sessions[user_id]["history"]
        history.append({
            "user": message,
            "bot": response.get("reply", ""),
            "timestamp": self._get_timestamp(),
            "domain": response.get("domain"),
            "source": response.get("source")
        })
        
        # Giới hạn lịch sử
        if len(history) > 10:
            history.pop(0)