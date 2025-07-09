# controllers/chat_controller.py - FIXED: Add Context Support Only

from services.flow_engine import FlowEngine
from services.unified_processor import process_user_query
from datetime import datetime
import json
import logging
import os
import pickle

logger = logging.getLogger(__name__)
from services.speech_services.text_to_speech import TextToSpeech

class ChatController:
    def __init__(self):
        self.tts = TextToSpeech()
        # Tạo instance FlowEngine trong constructor - UNCHANGED
        try:
            self.flow_engine = FlowEngine("dataset/xuatnhapcanh/flow.json")
            logger.info("✅ Flow engine initialized in ChatController")
        except Exception as e:
            logger.error(f"❌ Flow engine init failed: {e}")
            self.flow_engine = FlowEngine("nonexistent.json")  # Fallback
            
        self.user_sessions = {}
        self.session_file = "data/user_sessions.pkl"
        self._load_question_tree()
        self._load_sessions()

    def _load_question_tree(self):
        """Load question tree từ flow.json - UNCHANGED"""
        try:
            with open("dataset/xuatnhapcanh/flow.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                self.questions = {q["id"]: q for q in data.get("questions", [])}
                self.flows_info = data.get("flows", {})
            
            logger.info("✅ Loaded flow.json successfully")
            logger.info(f"📋 Questions loaded: {list(self.questions.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Error loading flow.json: {e}")
            self.questions = {}
            self.flows_info = {}

    def _load_sessions(self):
        """Load user sessions từ file - UNCHANGED"""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'rb') as f:
                    self.user_sessions = pickle.load(f)
                logger.info(f"✅ Loaded {len(self.user_sessions)} user sessions")
            else:
                self.user_sessions = {}
                logger.info("📝 Created new session storage")
        except Exception as e:
            logger.error(f"❌ Error loading sessions: {e}")
            self.user_sessions = {}

    def _save_sessions(self):
        """Save user sessions to file - UNCHANGED"""
        try:
            os.makedirs("data", exist_ok=True)
            with open(self.session_file, 'wb') as f:
                pickle.dump(self.user_sessions, f)
            logger.debug("💾 Sessions saved")
        except Exception as e:
            logger.error(f"❌ Error saving sessions: {e}")

    def _normalize_user_id(self, user_id: str) -> str:
        """Normalize user ID - UNCHANGED"""
        if user_id.startswith("user_") and len(user_id) > 10:
            timestamp_part = user_id[5:]
            if timestamp_part.isdigit() and len(timestamp_part) >= 10:
                base_id = timestamp_part[:10]
                normalized = f"user_{base_id}"
                logger.debug(f"🔧 Normalized {user_id} -> {normalized}")
                return normalized
        
        return user_id

    # ===== NEW: CONTEXT MANAGEMENT =====
    def _get_recent_context(self, user_id: str) -> str:
        """Get recent context from last 2-3 messages"""
        session = self.user_sessions.get(user_id, {})
        history = session.get("history", [])
        
        if len(history) >= 2:
            # Get last 2 messages for context
            recent = [h["user"] for h in history[-2:]]
            context = " ".join(recent)
            logger.debug(f"📝 Context for {user_id}: '{context[:50]}...'")
            return context
        
        return ""

    def _save_to_history(self, user_id: str, message: str):
        """Save message to user history"""
        if user_id not in self.user_sessions:
            return
            
        session = self.user_sessions[user_id]
        
        # Ensure history exists
        if "history" not in session:
            session["history"] = []
        
        # Add current message
        session["history"].append({
            "user": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 5 messages to avoid memory bloat
        if len(session["history"]) > 5:
            session["history"] = session["history"][-5:]
        
        logger.debug(f"💾 Saved to history for {user_id}: '{message[:30]}...'")

    def handle_chat(self, user_id: str, message: str, domain: str = None) -> dict:
        """Xử lý chat - ENHANCED: Show Unified + Flow prompt"""
        
        # UNCHANGED: Normalize user ID
        normalized_user_id = self._normalize_user_id(user_id)
        logger.info(f"🔍 Original user_id: {user_id} -> Normalized: {normalized_user_id}")
        
        # UNCHANGED: Initialize session if needed
        if normalized_user_id not in self.user_sessions:
            self.user_sessions[normalized_user_id] = {
                "mode": "normal",
                "current_answers": [],
                "current_question_id": None,
                "history": [],
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
            logger.info(f"📝 Created new session for user {normalized_user_id}")
        else:
            logger.info(f"♻️ Using existing session for user {normalized_user_id}")
        
        session = self.user_sessions[normalized_user_id]
        session["last_active"] = datetime.now().isoformat()
        
        message_cleaned = message.strip()
        message_lower = message_cleaned.lower()
        
        # NEW: Get context BEFORE saving current message
        recent_context = self._get_recent_context(normalized_user_id)
        
        # NEW: Save current message to history
        self._save_to_history(normalized_user_id, message_cleaned)

        # UNCHANGED: Detailed state logging
        logger.info(f"🔍 DETAILED STATE CHECK for user {normalized_user_id}:")
        logger.info(f"   📋 Session mode: {session['mode']}")
        logger.info(f"   ❓ Current question ID: {session.get('current_question_id')}")
        logger.info(f"   📝 Answers count: {len(session.get('current_answers', []))}")
        logger.info(f"   🔄 Flow engine state: {self.flow_engine.is_in_flow(normalized_user_id)}")
        logger.info(f"   💬 Message: '{message_cleaned}'")
        logger.info(f"   📄 Context: '{recent_context[:50]}...'")

        # UNCHANGED: Handle active flow
        if self.flow_engine.is_in_flow(normalized_user_id):
            logger.info(f"🔄 User {normalized_user_id} in active step flow")
            result = self._handle_active_flow_strict(normalized_user_id, message_cleaned, message_lower)
            self._save_sessions()
            return result

        # UNCHANGED: Handle question flow
        if session["mode"] == "question_flow":
            logger.info(f"❓ ENTERING question flow handler for user {normalized_user_id}")
            result = self._handle_question_flow_strict(normalized_user_id, message_cleaned, session)
            self._save_sessions()
            return result

        # UNCHANGED: Start flow
        if message_lower == "hướng dẫn quy trình":
            logger.info(f"🚀 Starting question flow for user {normalized_user_id}")
            result = self._start_question_flow(normalized_user_id, session)
            self._save_sessions()
            return result

        # ENHANCED: Flow request with Unified content
        if self._is_flow_request(message_lower):
            logger.info(f"🔍 Enhanced flow request detected for: '{message_cleaned}'")
            result = self._handle_enhanced_flow_request(normalized_user_id, message_cleaned, recent_context, domain)
            self._save_sessions()
            return result

        # UNCHANGED: Check for flow options error
        flow_options = ["tôi đã rõ", "cấp hộ chiếu lần đầu", "cấp lại hộ chiếu"]
        if any(opt in message_lower for opt in flow_options):
            logger.error(f"🚨 CRITICAL: Flow option '{message_cleaned}' reached normal processing!")
            return {
                "reply": f"❌ Có lỗi hệ thống với option '{message_cleaned}'. Vui lòng thử lại 'Hướng dẫn quy trình'.",
                "source": "error",
                "type": "system_error",
                "debug_info": {
                    "session_mode": session["mode"],
                    "question_id": session.get("current_question_id"),
                    "user_id": normalized_user_id
                }
            }

        # MODIFIED: Call UnifiedProcessor with context
        logger.info(f"💬 Normal processing for user {normalized_user_id}: {message_cleaned}")
        domain = domain or "xuatnhapcanh"
        
        # NEW: Pass context to UnifiedProcessor
        result = process_user_query(message_cleaned, normalized_user_id, domain, recent_context)
        
        self._save_sessions()
        
        return {
            "reply": result.get('reply') or result.get('text', ''),
            "source": result.get("source", "unknown"),
            "type": "answer",
            "metadata": result.get("metadata", {}),
            "domain": domain
        }

    def _handle_enhanced_flow_request(self, user_id: str, message: str, context: str, domain: str) -> dict:
        """ENHANCED: Handle flow request with Unified content"""
        try:
            # 1. Extract procedure and detect domain
            procedure_name = self._extract_procedure_from_message(message, context)
            detected_domain = domain or self._detect_domain_from_procedure(procedure_name)
            
            logger.info(f"🔍 Enhanced flow request:")
            logger.info(f"   Message: '{message}'")
            logger.info(f"   Procedure: '{procedure_name}'")
            logger.info(f"   Domain: '{detected_domain}'")
            
            # 2. Check if domain has flow
            flow_path = f"dataset/{detected_domain}/flow.json"
            has_flow = os.path.exists(flow_path)
            logger.info(f"   Flow exists: {has_flow} (path: {flow_path})")
            
            # 3. Get Unified content first
            logger.info("📋 Getting Unified content...")
            unified_result = process_user_query(message, user_id, detected_domain, context)
            unified_content = unified_result.get('reply') or unified_result.get('text', '')
            
            # 4. Build response based on flow availability
            if has_flow and detected_domain != "unknown":
                # Has flow: Show Unified + Flow prompt + Button
                logger.info("✅ Has flow - showing Unified + Flow prompt")
                
                if unified_content and len(unified_content.strip()) > 10:
                    # Has meaningful Unified content
                    combined_reply = f"{unified_content}\n\n📌 Bạn muốn được hướng dẫn từng bước thực hiện {procedure_name} không?"
                else:
                    # No meaningful Unified content - use default
                    combined_reply = f"📌 Bạn muốn được hướng dẫn từng bước thực hiện {procedure_name} không?"
                
                return {
                    "reply": combined_reply,
                    "source": "enhanced_flow_request",
                    "show_flow_button": True,
                    "button_label": "Hướng dẫn quy trình",
                    "type": "guide_prompt",
                    "metadata": {
                        "procedure": procedure_name,
                        "domain": detected_domain,
                        "has_unified_content": bool(unified_content and len(unified_content.strip()) > 10),
                        "unified_source": unified_result.get("source", "unknown")
                    }
                }
            
            else:
                # No flow: Just show Unified content
                logger.info("❌ No flow - showing only Unified content")
                
                if unified_content and len(unified_content.strip()) > 10:
                    # Has Unified content - return it
                    return {
                        "reply": unified_content,
                        "source": unified_result.get("source", "unified"),
                        "type": "answer",
                        "metadata": {
                            **unified_result.get("metadata", {}),
                            "procedure": procedure_name,
                            "domain": detected_domain,
                            "flow_available": False
                        }
                    }
                else:
                    # No Unified content either - fallback
                    return {
                        "reply": f"Hiện tại hệ thống đang cập nhật thông tin hướng dẫn về {procedure_name}. Bạn vui lòng liên hệ cán bộ tiếp nhận để được hỗ trợ.",
                        "source": "no_data_available",
                        "type": "fallback",
                        "metadata": {
                            "procedure": procedure_name,
                            "domain": detected_domain,
                            "flow_available": False,
                            "unified_available": False
                        }
                    }
        
        except Exception as e:
            logger.error(f"❌ Enhanced flow request failed: {e}")
            # Fallback to old behavior
            procedure_name = self._extract_procedure_from_message(message, context)
            return {
                "reply": f"📌 Bạn muốn được hướng dẫn từng bước thực hiện {procedure_name} không?",
                "source": "fallback_flow_request",
                "show_flow_button": True,
                "button_label": "Hướng dẫn quy trình",
                "type": "guide_prompt"
            }


    # ===== ALL OTHER METHODS UNCHANGED =====
    def _handle_question_flow_strict(self, user_id: str, message: str, session: dict) -> dict:
        """Xử lý STRICT question flow - UNCHANGED"""
        
        logger.info(f"🔄 Question flow handler for user {user_id}")
        logger.info(f"📋 Current question: {session.get('current_question_id')}")
        logger.info(f"📝 User message: '{message}'")
        
        # CHỈ CHO PHÉP THOÁT KHI NHẮN ĐÚNG LỆNH
        exit_commands = ["thoát hướng dẫn", "thoát quy trình", "kết thúc hướng dẫn"]
        if any(cmd in message.lower() for cmd in exit_commands):
            logger.info(f"🚪 User {user_id} exiting question flow")
            session["mode"] = "normal"
            session["current_answers"] = []
            session["current_question_id"] = None
            return {
                "reply": "✅ Đã thoát hướng dẫn. Bây giờ tôi có thể giải đáp thắc mắc khác của bạn.",
                "source": "chatbot",
                "type": "exit_flow"
            }
        
        # KIỂM TRA QUESTION HIỆN TẠI
        current_question = self.questions.get(session["current_question_id"])
        if not current_question:
            logger.error(f"❌ Question not found: {session['current_question_id']}")
            session["mode"] = "normal"
            return {
                "reply": "❌ Có lỗi xảy ra. Vui lòng thử lại.",
                "source": "chatbot", 
                "type": "error"
            }
        
        # KIỂM TRA OPTIONS HỢP LỆ
        valid_options = [opt["label"] for opt in current_question.get("options", [])]
        logger.info(f"📋 Valid options: {valid_options}")
        
        # EXACT MATCH
        if message not in valid_options:
            logger.warning(f"❌ Invalid option '{message}'")
            logger.warning(f"📋 Expected one of: {valid_options}")
            return {
                "reply": f"🤖 Để giải đáp thắc mắc khác, bạn vui lòng bấm nút **'Thoát hướng dẫn'** trước.\n\nVui lòng chọn một trong các tùy chọn:",
                "source": "chatbot",
                "options": valid_options + ["Thoát hướng dẫn"],
                "type": "question_locked"
            }
        
        # LƯU CÂU TRẢ LỜI HỢP LỆ
        logger.info(f"✅ Valid option selected: {message}")
        session["current_answers"].append({
            "question_id": session["current_question_id"],
            "option": message
        })
        
        logger.info(f"📝 Current answers: {session['current_answers']}")
        
        # TÌM NEXT ITEM
        next_item = self._get_next_question_or_flow(session["current_answers"])
        logger.info(f"🔍 Next item found: {next_item}")
        
        if not next_item:
            logger.error("❌ No next item found")
            session["mode"] = "normal"
            return {
                "reply": "❌ Không tìm thấy hướng dẫn phù hợp.",
                "source": "chatbot",
                "type": "error"
            }
        
        # XỬ LÝ NEXT ITEM
        if isinstance(next_item, dict) and "question" in next_item:
            # Câu hỏi tiếp theo
            logger.info(f"➡️ Moving to next question: {next_item['id']}")
            session["current_question_id"] = next_item["id"]
            options = [opt["label"] for opt in next_item.get("options", [])]
            
            # NEW: Support image in questions
            response = {
                "reply": next_item["question"],
                "source": "chatbot",
                "options": options + ["Thoát hướng dẫn"],
                "type": "question"
            }
            
            # Add image if exists
            if "image" in next_item and next_item["image"]:
                if next_item["image"].startswith("dataset/"):
                    base_url = "http://localhost:8000"
                    response["guide_image"] = f"{base_url}/static/{next_item['image']}"
                else:
                    response["guide_image"] = next_item["image"]
            
            return response
        
        elif isinstance(next_item, dict) and next_item.get("type") == "flow":
            # Chuyển sang step flow
            logger.info(f"🔄 Starting step flow: {next_item['flow_id']}")
            session["mode"] = "normal"  # Reset question mode
            return self._start_step_flow(user_id, next_item["flow_id"])
        
        else:
            logger.error(f"❌ Unknown next item type: {next_item}")
            session["mode"] = "normal"
            return {
                "reply": "❌ Có lỗi xảy ra trong quá trình xử lý.",
                "source": "chatbot",
                "type": "error"
            }

    def _get_next_question_or_flow(self, current_answers: list):
        """Tìm câu hỏi tiếp theo hoặc flow - UNCHANGED"""
        if not current_answers:
            return self.questions.get("start")
        
        last_answer = current_answers[-1]
        current_question_id = last_answer.get("question_id")
        selected_option = last_answer.get("option")
        
        logger.info(f"🔍 Looking for next from question '{current_question_id}' with option '{selected_option}'")
        
        current_question = self.questions.get(current_question_id)
        if not current_question:
            logger.error(f"❌ Question not found: {current_question_id}")
            return None
        
        # LOG CHI TIẾT TỪNG OPTION
        options = current_question.get("options", [])
        logger.info(f"📋 Question has {len(options)} options:")
        for i, opt in enumerate(options):
            logger.info(f"   {i+1}. '{opt.get('label')}' -> next: {opt.get('next')}, flow: {opt.get('flow')}")
        
        # Tìm option được chọn - EXACT MATCH với STRIP
        for option in options:
            option_label = option.get("label", "").strip()
            if option_label == selected_option.strip():
                logger.info(f"✅ Found matching option: {option}")
                
                if "next" in option and option["next"]:
                    next_question = self.questions.get(option["next"])
                    if next_question:
                        logger.info(f"➡️ Next question: {option['next']}")
                        return next_question
                    else:
                        logger.error(f"❌ Next question not found: {option['next']}")
                
                elif "flow" in option and option["flow"]:
                    logger.info(f"🔄 Starting flow: {option['flow']}")
                    return {"type": "flow", "flow_id": option["flow"]}
                
                else:
                    logger.warning(f"⚠️ Option has no 'next' or 'flow': {option}")
        
        logger.error(f"❌ No matching option found for '{selected_option}'")
        return None

    def _start_question_flow(self, user_id: str, session: dict) -> dict:
        """Bắt đầu question flow - UNCHANGED"""
        logger.info(f"🚀 Starting question flow for user {user_id}")
        
        session["mode"] = "question_flow"
        session["current_answers"] = []
        session["current_question_id"] = "start"
        
        start_question = self.questions.get("start")
        if start_question:
            options = [opt["label"] for opt in start_question.get("options", [])]
            logger.info(f"✅ Returning start question with options: {options}")
            
            # NEW: Support image in start question
            response = {
                "reply": start_question["question"],
                "source": "chatbot",
                "options": options + ["Thoát hướng dẫn"],
                "type": "question"
            }
            
            # Add image if exists
            if "image" in start_question and start_question["image"]:
                if start_question["image"].startswith("dataset/"):
                    base_url = "http://localhost:8000"
                    response["guide_image"] = f"{base_url}/static/{start_question['image']}"
                else:
                    response["guide_image"] = start_question["image"]
            
            return response
        
        logger.error("❌ Start question not found!")
        return {
            "reply": "❌ Không tìm thấy câu hỏi bắt đầu.",
            "source": "chatbot",
            "type": "error"
        }

    def _handle_active_flow_strict(self, user_id: str, message: str, message_lower: str) -> dict:
        """Xử lý STRICT khi đang trong step flow - UNCHANGED"""
        
        # CHỈ CHO PHÉP THOÁT KHI NHẮN ĐÚNG LỆNH
        exit_commands = ["thoát hướng dẫn", "thoát quy trình", "kết thúc hướng dẫn", "exit flow"]
        if any(cmd in message_lower for cmd in exit_commands):
            self.flow_engine.reset(user_id)
            if user_id in self.user_sessions:
                self.user_sessions[user_id]["mode"] = "normal"
                self.user_sessions[user_id]["current_question_id"] = None
                self.user_sessions[user_id]["current_answers"] = []
            return {
                "reply": "✅ Đã thoát hướng dẫn. Bây giờ tôi có thể giải đáp thắc mắc khác của bạn.",
                "source": "flow",
                "type": "exit_flow"
            }
        
        # XỬ LÝ CÁC LỆNH FLOW
        flow_result = self.flow_engine.handle_user_input(user_id, message_lower)
        
        # Xử lý kết quả flow
        return self._format_flow_response(user_id, flow_result)

    def _format_flow_response(self, user_id: str, flow_result: dict) -> dict:
        """Format flow response với TTS support"""
        
        # GET FLOW INFO
        flow_id = self.flow_engine.user_progress.get(user_id, {}).get("flow_id")
        flow_info = self.flows_info.get(flow_id, {})
        total_steps = len(flow_info.get("steps", {}))
        current_step_num = flow_result.get("current")
        
        # GET CURRENT STEP DATA
        step_data = flow_result.get("step", {})
        
        # ===== BUILD COMPREHENSIVE GUIDE DATA =====
        guide_data = {}
        
        if flow_id and current_step_num:
            # Basic flow information
            guide_data["current_step"] = int(current_step_num)
            guide_data["total_steps"] = total_steps
            guide_data["flow_id"] = flow_id
            
            # Flow metadata
            guide_data["flow_data"] = {
                "name": flow_info.get("name", "Hướng dẫn"),
                "steps": total_steps,
                "description": flow_info.get("description", "")
            }
            
            # Step-specific information
            guide_data["step_info"] = {
                "step_number": int(current_step_num),
                "step_name": step_data.get("name", ""),
                "step_description": step_data.get("description", ""),
                "step_type": step_data.get("type", "say"),
                "wait_for_user": step_data.get("wait_for_user", True)
            }
            
            # ===== TTS PROCESSING =====
            step_type = step_data.get("type", "say")
            step_tts = step_data.get("tts")
            
            if step_type == "say" and step_tts:
                if self.tts.is_available():
                    self.tts.speak_async(step_tts)
                guide_data["tts_text"] = step_tts
                guide_data["should_speak"] = True
            else:
                guide_data["should_speak"] = False
            
            # Media and resources
            step_image = step_data.get("image")
            if step_image:
                if step_image.startswith("dataset/"):
                    base_url = "http://localhost:8000"
                    guide_data["guide_image"] = f"{base_url}/static/{step_image}"
                else:
                    guide_data["guide_image"] = step_image
            
            # External links
            step_link = step_data.get("link")
            if step_link:
                guide_data["external_link"] = step_link
            
            # Navigation info
            guide_data["navigation"] = {
                "can_go_back": int(current_step_num) > 1,
                "can_go_forward": int(current_step_num) < total_steps,
                "is_first_step": int(current_step_num) == 1,
                "is_last_step": int(current_step_num) == total_steps
            }
            
            # Progress percentage
            guide_data["progress_percent"] = round((int(current_step_num) / total_steps) * 100, 1)
        
        # Handle different flow states
        
        # Nếu jump thành công
        if flow_result.get("jumped"):
            return {
                "reply": f"{flow_result.get('jump_message', '')}\n\n📋 **{flow_info.get('name', 'Hướng dẫn')}** – Bước {current_step_num}/{total_steps}\n\n{step_data.get('name', '')}",
                "source": "flow", 
                "type": "step",
                "buttons": ["Tiếp tục", "Quay lại", "Thoát hướng dẫn"],
                "step_mode": True,
                "current_step": int(current_step_num) if current_step_num else None,
                "tts_text": guide_data.get("tts_text"),
                "should_speak": guide_data.get("should_speak", False),
                **guide_data
            }
        
        # Nếu flow hoàn thành
        if flow_result.get("done"):
            self.flow_engine.reset(user_id)
            if user_id in self.user_sessions:
                self.user_sessions[user_id]["mode"] = "normal"
                self.user_sessions[user_id]["current_question_id"] = None
                self.user_sessions[user_id]["current_answers"] = []
            return {
                "reply": flow_result.get("message", "✅ Bạn đã hoàn tất hướng dẫn!"),
                "source": "flow",
                "type": "completed",
                "flow_completed": True,
                "should_speak": False
            }
        
        # Nếu có lỗi flow
        if "error" in flow_result:
            return {
                "reply": f"❌ {flow_result['error']}",
                "source": "flow",
                "type": "error",
                "should_speak": False
            }
        
        # Hiển thị step thông thường
        if "step" in flow_result:
            return {
                "reply": f"📋 **{flow_info.get('name', 'Hướng dẫn')}** – Bước {current_step_num}/{total_steps}\n\n{step_data.get('name', '')}",
                "source": "flow",
                "type": "step",
                "buttons": ["Tiếp tục", "Quay lại", "Thoát hướng dẫn"],
                "step_mode": True,
                "current_step": int(current_step_num) if current_step_num else None,
                "tts_text": guide_data.get("tts_text"),
                "should_speak": guide_data.get("should_speak", False),
                **guide_data
            }
        
        # Nếu không hiểu lệnh - CHẶN HỎI KHÁC
        return {
            "reply": flow_result.get("message", "🤖 Để giải đáp thắc mắc khác, bạn vui lòng bấm nút **'Thoát hướng dẫn'** trước.\n\nTrong hướng dẫn, bạn có thể dùng: 'Tiếp tục', 'Quay lại' hoặc nhắn mô tả bước muốn đến."),
            "source": "flow",
            "type": "flow_locked",
            "buttons": ["Tiếp tục", "Quay lại", "Thoát hướng dẫn"],
            "should_speak": False,
            **guide_data
        }

    def _start_step_flow(self, user_id: str, flow_id: str) -> dict:
        """Bắt đầu step flow - UNCHANGED"""
        flow_info = self.flows_info.get(flow_id, {})
        steps = flow_info.get("steps", {})
        
        # Nếu flow không có steps - chỉ hiển thị thông tin
        if not steps:
            description = flow_info.get("description", "Tính năng này đang được phát triển.")
            return {
                "reply": f"ℹ️ **{flow_info.get('name', 'Thông báo')}**\n\n{description}",
                "source": "chatbot",
                "type": "info",
                "buttons": ["Thoát hướng dẫn"]
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
        return self._format_flow_response(user_id, result)

    def _detect_domain_from_procedure(self, procedure_name: str) -> str:
        """Detect domain from procedure name"""
        p = procedure_name.lower()
        if any(kw in p for kw in ["hộ chiếu", "xuất cảnh", "nhập cảnh", "visa"]): return "xuatnhapcanh"
        elif any(kw in p for kw in ["căn cước", "cccd", "cmnd"]): return "cancuoc"
        elif any(kw in p for kw in ["thường trú", "tạm trú", "cư trú"]): return "cutru"
        else: return "unknown"

    def _extract_procedure_from_message(self, message: str, context: str = "") -> str:
        """Extract procedure name from message"""
        combined = f"{context} {message}".lower()
        
        if "hộ chiếu" in combined: return "cấp hộ chiếu"
        elif "căn cước" in combined: return "cấp căn cước"  
        elif "thường trú" in combined: return "đăng ký thường trú"
        elif "tạm trú" in combined: return "đăng ký tạm trú"
        else: return "thủ tục"

    def _is_flow_request(self, message: str) -> bool:
        """Detect flow requests - ENHANCED"""
        flow_keywords = [
            "hướng dẫn", "quy trình", "trình tự", "các bước", 
            "hướng dẫn làm", "hướng dẫn thủ tục", "cách làm", "làm như thế nào",
            "thủ tục như thế nào", "quy trình như thế nào"
        ]
        
        # Must have flow keyword + procedure context
        has_flow_keyword = any(kw in message for kw in flow_keywords)
        has_procedure_context = any(proc in message for proc in [
            "hộ chiếu", "visa", "căn cước", "cccd", "thường trú", "tạm trú", 
            "xuất cảnh", "nhập cảnh", "cấp", "làm", "đăng ký"
        ])
        
        result = has_flow_keyword and has_procedure_context
        logger.debug(f"🔍 Flow request check: '{message}' → {result} (keyword: {has_flow_keyword}, context: {has_procedure_context})")
        return result

    def get_user_session_info(self, user_id: str) -> dict:
        """Lấy thông tin session của user - DEBUG METHOD - UNCHANGED"""
        normalized_id = self._normalize_user_id(user_id)
        session = self.user_sessions.get(normalized_id, {})
        flow_state = self.flow_engine.user_progress.get(normalized_id, {})
        
        return {
            "original_user_id": user_id,
            "normalized_user_id": normalized_id,
            "session_mode": session.get("mode", "unknown"),
            "current_question_id": session.get("current_question_id"),
            "answers_count": len(session.get("current_answers", [])),
            "in_flow_engine": self.flow_engine.is_in_flow(normalized_id),
            "flow_state": flow_state,
            "history_count": len(session.get("history", [])),
            "last_active": session.get("last_active"),
            "current_answers": session.get("current_answers", [])
        }

    def cleanup_old_sessions(self, hours=24):
        """Cleanup old sessions - UNCHANGED"""
        cutoff = datetime.now().timestamp() - (hours * 3600)
        to_remove = []
        
        for user_id, session in self.user_sessions.items():
            last_active = session.get("last_active")
            if last_active:
                try:
                    last_time = datetime.fromisoformat(last_active).timestamp()
                    if last_time < cutoff:
                        to_remove.append(user_id)
                except:
                    to_remove.append(user_id)
        
        for user_id in to_remove:
            del self.user_sessions[user_id]
            if user_id in self.flow_engine.user_progress:
                del self.flow_engine.user_progress[user_id]
        
        if to_remove:
            self._save_sessions()
            logger.info(f"🗑️ Cleaned up {len(to_remove)} old sessions")
        
        return len(to_remove)