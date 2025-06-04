# Copy toàn bộ nội dung này và REPLACE file services/flow_engine.py

# services/flow_engine.py - Complete version với global instance

import json
import logging
from pathlib import Path
from fuzzywuzzy import fuzz

logger = logging.getLogger(__name__)

class FlowEngine:
    def __init__(self, flow_path):
        self.flow_data = self._load_flow(flow_path)
        self.flows = self.flow_data.get("flows", {})
        self.user_progress = {}  # user_id -> { flow_id, step_index }

    def _load_flow(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading flow from {path}: {e}")
            return {"flows": {}}

    def is_in_flow(self, user_id):
        return user_id in self.user_progress

    def handle_user_input(self, user_id, message):
        """Xử lý input của user trong flow - ENHANCED"""
        message = message.lower().strip()

        # Commands xử lý cơ bản
        if message in ["kết thúc", "thoát", "dừng", "exit"]:
            return self.reset(user_id)
        elif message in ["xong", "tiếp", "tiếp tục", "next"]:
            return self.next_step(user_id)
        elif message in ["quay lại", "lùi lại", "back", "previous"]:
            return self.previous_step(user_id)
        elif message in ["bắt đầu lại", "reset", "restart"]:
            flow_id = self.user_progress.get(user_id, {}).get("flow_id")
            return self.start_flow(user_id, flow_id) if flow_id else {"error": "Chưa có flow để bắt đầu lại."}
        
        # Thử nhảy đến step bằng description matching (ENHANCED)
        jump_result = self.jump_to_step_by_description(user_id, message)
        if jump_result:
            return jump_result
        
        # Thử nhảy bằng số bước
        step_number_result = self.jump_to_step_by_number(user_id, message)
        if step_number_result:
            return step_number_result
            
        # Không hiểu lệnh - return để chat_controller xử lý
        return {
            "message": f"🤖 Tôi không hiểu '{message}'. Hãy dùng: 'tiếp tục', 'quay lại', hoặc mô tả bước muốn đến.",
            "step": self.get_current_step(user_id).get("step", {}),
            "current": self.get_current_step(user_id).get("current", "?"),
            "unknown_command": True
        }

    def jump_to_step_by_number(self, user_id, message):
        """Nhảy đến step theo số"""
        try:
            # Tìm số trong message
            import re
            numbers = re.findall(r'\d+', message)
            if not numbers:
                return None
            
            target_step = int(numbers[0])
            state = self.user_progress.get(user_id)
            if not state:
                return None
                
            flow_id = state.get("flow_id")
            steps = self.flows.get(flow_id, {}).get("steps", {})
            
            # Kiểm tra step có tồn tại không
            if str(target_step) in steps:
                old_step = self.user_progress[user_id]["step_index"]
                self.user_progress[user_id]["step_index"] = target_step
                
                logger.info(f"User {user_id} jumped from step {old_step} to step {target_step} by number")
                
                result = self.get_current_step(user_id)
                result["jumped"] = True
                result["jump_message"] = f"🎯 Đã chuyển đến bước {target_step}!"
                return result
                
        except Exception as e:
            logger.debug(f"Failed to parse step number: {e}")
            
        return None

    def jump_to_step_by_description(self, user_id, message):
        """
        ENHANCED: Nhảy đến step khi user nhắn gần giống description/name
        """
        state = self.user_progress.get(user_id)
        if not state:
            return None
            
        flow_id = state.get("flow_id")
        steps = self.flows.get(flow_id, {}).get("steps", {})
        
        if not steps:
            return None
            
        message_lower = message.lower()
        best_matches = []
        
        # Tìm tất cả step có score cao
        for step_index, step in steps.items():
            step_description = step.get("description", "").lower()
            step_name = step.get("name", "").lower()
            
            # Combine description + name for better matching
            combined_text = f"{step_description} {step_name}"
            
            if not combined_text.strip():
                continue
            
            # Multiple scoring methods
            scores = []
            
            # 1. Partial ratio với description
            if step_description:
                scores.append(fuzz.partial_ratio(message_lower, step_description))
            
            # 2. Partial ratio với name
            if step_name:
                scores.append(fuzz.partial_ratio(message_lower, step_name))
            
            # 3. Token set ratio với combined text
            scores.append(fuzz.token_set_ratio(message_lower, combined_text))
            
            # 4. Keyword matching boost
            keyword_bonus = 0
            message_words = [w for w in message_lower.split() if len(w) > 2]
            for word in message_words:
                if word in combined_text:
                    keyword_bonus += 15
            
            # 5. Specific keyword patterns cho flow xuất nhập cảnh
            flow_keywords = {
                "đăng nhập": ["đăng nhập", "login", "tài khoản"],
                "thủ tục": ["thủ tục", "hồ sơ", "giấy tờ"],
                "chọn": ["chọn", "lựa chọn", "bấm"],
                "cơ quan": ["cơ quan", "công an", "bộ"],
                "ảnh": ["ảnh", "chụp", "tải ảnh", "upload"],
                "nơi sinh": ["nơi sinh", "khai sinh", "sinh"]
            }
            
            for pattern, keywords in flow_keywords.items():
                if any(kw in message_lower for kw in keywords) and pattern in combined_text:
                    keyword_bonus += 25
            
            # Lấy score cao nhất + bonus
            max_score = max(scores) if scores else 0
            final_score = max_score + keyword_bonus
            
            if final_score >= 50:  # Threshold thấp hơn để dễ match
                best_matches.append({
                    'step_index': step_index,
                    'step': step,
                    'score': final_score,
                    'name': step.get('name', ''),
                    'description': step.get('description', '')
                })
        
        # Sort theo score và lấy match tốt nhất
        best_matches.sort(key=lambda x: x['score'], reverse=True)
        
        if best_matches and best_matches[0]['score'] >= 60:  # Chỉ accept score tốt
            best_match = best_matches[0]
            
            old_step = self.user_progress[user_id]["step_index"]
            new_step = int(best_match['step_index'])
            self.user_progress[user_id]["step_index"] = new_step
            
            logger.info(f"User {user_id} jumped from step {old_step} to step {new_step} (score: {best_match['score']})")
            
            result = self.get_current_step(user_id)
            result["jumped"] = True
            result["jump_message"] = f"🎯 Tôi hiểu bạn muốn đến bước {new_step}: {best_match['name'][:50]}..."
            return result
        
        return None

    def start_flow(self, user_id, flow_id):
        """Bắt đầu flow mới"""
        if flow_id not in self.flows:
            return {"error": f"Flow ID '{flow_id}' không tồn tại."}
        
        flow_steps = self.flows[flow_id].get("steps", {})
        if not flow_steps:
            return {"error": f"Flow '{flow_id}' không có steps để thực hiện."}
            
        self.user_progress[user_id] = {"flow_id": flow_id, "step_index": 1}
        logger.info(f"Started flow '{flow_id}' for user {user_id}")
        
        return self.get_current_step(user_id)

    def get_current_step(self, user_id):
        """Lấy step hiện tại"""
        state = self.user_progress.get(user_id)
        if not state:
            return {"error": "User chưa bắt đầu flow nào."}

        flow_id = state["flow_id"]
        step_index = str(state["step_index"])
        steps = self.flows[flow_id].get("steps", {})
        step = steps.get(step_index)

        if not step:
            return {"done": True, "message": "✅ Bạn đã hoàn tất tất cả các bước!"}

        return {
            "step": step,
            "current": step_index,
            "flow_id": flow_id,
            "wait_for_user": step.get("wait_for_user", True)
        }

    def next_step(self, user_id):
        """Chuyển sang bước tiếp theo"""
        if user_id not in self.user_progress:
            return {"error": "User chưa bắt đầu flow nào."}

        current_state = self.user_progress[user_id]
        flow_id = current_state["flow_id"]
        max_steps = len(self.flows[flow_id].get("steps", {}))
        
        if current_state["step_index"] >= max_steps:
            return {"done": True, "message": "✅ Bạn đã hoàn tất tất cả các bước!"}
            
        self.user_progress[user_id]["step_index"] += 1
        logger.info(f"User {user_id} moved to step {self.user_progress[user_id]['step_index']}")
        
        return self.get_current_step(user_id)

    def previous_step(self, user_id):
        """Quay lại bước trước"""
        if user_id not in self.user_progress:
            return {"error": "User chưa bắt đầu flow nào."}

        if self.user_progress[user_id]["step_index"] > 1:
            self.user_progress[user_id]["step_index"] -= 1
            logger.info(f"User {user_id} moved back to step {self.user_progress[user_id]['step_index']}")
        else:
            return {"message": "🔄 Bạn đang ở bước đầu tiên rồi."}
            
        return self.get_current_step(user_id)

    def reset(self, user_id):
        """Reset flow cho user"""
        if user_id in self.user_progress:
            flow_id = self.user_progress[user_id].get("flow_id", "unknown")
            del self.user_progress[user_id]
            logger.info(f"Reset flow '{flow_id}' for user {user_id}")
        
        return {
            "done": True, 
            "message": "🔄 Đã kết thúc hướng dẫn. Bạn có thể bắt đầu lại bất cứ lúc nào!"
        }

# ===== GLOBAL INSTANCE =====
# Tạo instance global để import
try:
    flow_engine = FlowEngine("dataset/xuatnhapcanh/flow.json")
    print("✅ Flow engine initialized successfully")
except Exception as e:
    print(f"⚠️ Flow engine initialization failed: {e}")
    # Tạo fallback instance
    flow_engine = FlowEngine("nonexistent.json")  # Will create empty flows