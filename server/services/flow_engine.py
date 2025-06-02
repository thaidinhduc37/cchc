# ✅ flow_engine chuẩn, giữ nguyên logic gốc và chỉ bổ sung đúng hàm jump_to_step_by_description

import json
from pathlib import Path

class FlowEngine:
    def __init__(self, flow_path):
        self.flow_data = self._load_flow(flow_path)
        self.flows = self.flow_data.get("flows", {})
        self.user_progress = {}  # user_id -> { flow_id, step_index }

    def _load_flow(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def is_in_flow(self, user_id):
        return user_id in self.user_progress

    def handle_user_input(self, user_id, message):
        message = message.lower().strip()

        if message in ["kết thúc", "thoát", "dừng"]:
            return self.reset(user_id)
        if message in ["xong", "tiếp", "tiếp tục"]:
            return self.next_step(user_id)
        elif message in ["quay lại", "lùi lại"]:
            return self.previous_step(user_id)
        elif message in ["bắt đầu lại", "reset"]:
            flow_id = self.user_progress.get(user_id, {}).get("flow_id")
            return self.start_flow(user_id, flow_id) if flow_id else {"error": "Chưa có flow để bắt đầu lại."}
        else:
            jump_result = self.jump_to_step_by_description(user_id, message)
            if jump_result:
                return jump_result
            return {"message": f"🤖 Không rõ yêu cầu: '{message}'"}

    def start_flow(self, user_id, flow_id):
        if flow_id not in self.flows:
            return {"error": "Flow ID không tồn tại."}
        self.user_progress[user_id] = {"flow_id": flow_id, "step_index": 1}
        return self.get_current_step(user_id)

    def get_current_step(self, user_id):
        state = self.user_progress.get(user_id)
        if not state:
            return {"error": "User chưa bắt đầu flow nào."}

        flow_id = state["flow_id"]
        step_index = str(state["step_index"])
        steps = self.flows[flow_id].get("steps", {})
        step = steps.get(step_index)

        if not step:
            return {"done": True, "message": "✅ Bạn đã hoàn tất tất cả các bước."}

        return {
            "step": step,
            "current": step_index,
            "flow_id": flow_id,
            "wait_for_user": step.get("wait_for_user", True)
        }

    def next_step(self, user_id):
        if user_id not in self.user_progress:
            return {"error": "User chưa bắt đầu flow nào."}

        self.user_progress[user_id]["step_index"] += 1
        return self.get_current_step(user_id)

    def previous_step(self, user_id):
        if user_id not in self.user_progress:
            return {"error": "User chưa bắt đầu flow nào."}

        if self.user_progress[user_id]["step_index"] > 1:
            self.user_progress[user_id]["step_index"] -= 1
        return self.get_current_step(user_id)

    def reset(self, user_id):
        if user_id in self.user_progress:
            del self.user_progress[user_id]
        return {"message": "🔄 Đã reset trạng thái flow cho user."}

    def jump_to_step_by_description(self, user_id, message):
        state = self.user_progress.get(user_id)
        if not state:
            return None
        flow_id = state.get("flow_id")
        steps = self.flows.get(flow_id, {}).get("steps", {})
        lowered = message.lower()
        for step_index, step in steps.items():
            if step.get("description") and step["description"].lower() in lowered:
                self.user_progress[user_id]["step_index"] = int(step_index)
                return self.get_current_step(user_id)
        return None


# Khởi tạo engine dùng file flow mẫu
flow_engine = FlowEngine("dataset/xuatnhapcanh/flow.json")
