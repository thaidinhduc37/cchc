import json

class FlowEngine:
    def __init__(self, flow_file: str):
        self.flow_file = flow_file
        self.steps = self._load_flow()

    def _load_flow(self):
        try:
            with open(self.flow_file, "r", encoding="utf-8") as f:
                return json.load(f).get("steps", {})
        except Exception as e:
            print(f"Lỗi khi đọc flow.json: {e}")
            return {}

    def get_step(self, step_id: str):
        return self.steps.get(step_id, {})

    def get_next_step(self, current_step_id: str):
        current = self.get_step(current_step_id)
        if isinstance(current, dict):
            next_id = current.get("next")
            return self.get_step(next_id) if next_id else {}
        return {}
