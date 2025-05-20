# app/assistant/flow_manager.py
import json

class FlowManager:
    def __init__(self, flow_path):
        with open(flow_path, "r", encoding="utf-8") as f:
            self.flow = json.load(f)

    def get_step(self, step_id):
        for step in self.flow.get("steps", []):
            if step.get("id") == step_id:
                return step
        return None

    def get_next_step(self, current_id):
        current_step = self.get_step(current_id)
        if current_step:
            return self.get_step(current_step.get("next"))
        return None
