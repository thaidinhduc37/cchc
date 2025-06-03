# services/flow_engine.py - Fixed version với jump by description

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
        """Xử lý input của user trong flow"""
        message = message.lower().strip()

        # Commands xử lý
        if message in ["kết thúc", "thoát", "dừng", "exit"]:
            return self.reset(user_id)
        elif message in ["xong", "tiếp", "tiếp tục", "next"]:
            return self.next_step(user_id)
        elif message in ["quay lại", "lùi lại", "back", "previous"]:
            return self.previous_step(user_id)
        elif message in ["bắt đầu lại", "reset", "restart"]:
            flow_id = self.user_progress.get(user_id, {}).get("flow_id")
            return self.start_flow(user_id, flow_id) if flow_id else {"error": "Chưa có flow để bắt đầu lại."}
        
        # Thử nhảy đến step bằng description matching
        jump_result = self.jump_to_step_by_description(user_id, message)
        if jump_result:
            return jump_result
            
        # Không hiểu lệnh
        return {
            "message": f"🤖 Tôi không hiểu '{message}'. Hãy dùng: 'tiếp tục', 'quay lại', hoặc 'kết thúc'",
            "step": self.get_current_step(user_id).get("step", {}),
            "current": self.get_current_step(user_id).get("current", "?")
        }

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

    def jump_to_step_by_description(self, user_id, message):
        """
        QUAN TRỌNG: Nhảy đến step khi user nhắn gần giống description
        """
        state = self.user_progress.get(user_id)
        if not state:
            return None
            
        flow_id = state.get("flow_id")
        steps = self.flows.get(flow_id, {}).get("steps", {})
        
        if not steps:
            return None
            
        message_lower = message.lower()
        best_match = None
        best_score = 0
        best_step_index = None
        
        # Tìm step có description gần nhất
        for step_index, step in steps.items():
            step_description = step.get("description", "").lower()
            step_name = step.get("name", "").lower()
            
            # Combine description + name for better matching
            combined_text = f"{step_description} {step_name}"
            
            if not combined_text.strip():
                continue
                
            # Fuzzy matching với description
            desc_score = fuzz.partial_ratio(message_lower, step_description)
            name_score = fuzz.partial_ratio(message_lower, step_name)
            combined_score = fuzz.partial_ratio(message_lower, combined_text)
            
            # Lấy score cao nhất
            max_score = max(desc_score, name_score, combined_score)
            
            # Bonus nếu có keyword match chính xác
            if any(word in combined_text for word in message_lower.split() if len(word) > 3):
                max_score += 20
                
            if max_score > best_score and max_score >= 60:  # Threshold 60%
                best_score = max_score
                best_match = step
                best_step_index = step_index
        
        # Nếu tìm thấy match tốt
        if best_match and best_step_index:
            old_step = self.user_progress[user_id]["step_index"]
            self.user_progress[user_id]["step_index"] = int(best_step_index)
            
            logger.info(f"User {user_id} jumped from step {old_step} to step {best_step_index} (score: {best_score})")
            
            result = self.get_current_step(user_id)
            result["jumped"] = True
            result["jump_message"] = f"🎯 Tôi hiểu bạn muốn đến bước {best_step_index}!"
            return result
        
        return None

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