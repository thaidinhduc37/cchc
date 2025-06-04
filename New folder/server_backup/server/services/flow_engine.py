import json
from pathlib import Path

FLOW_PATH = Path(__file__).parent.parent / "dataset" / "xuatnhapcanh" / "flow.json"

class FlowEngine:
    def __init__(self):
        with open(FLOW_PATH, encoding="utf-8") as f:
            self.flow = json.load(f)
        self.questions = {q["id"]: q for q in self.flow["questions"]}
        self.flows = self.flow["flows"]
        self.steps = self.flow.get("steps", {})
        self.user_flows = {}  # Thêm dòng này nếu cần lưu flow theo user

    def get_question(self, qid):
        return self.questions.get(qid)

    def get_flow_steps(self, flow_id):
        flow = self.flows.get(flow_id)
        if not flow:
            return []
        step_ids = flow.get("steps", [])
        return [self.steps.get(sid, f"Bước {sid}") for sid in step_ids]

    def navigate(self, answers):
        current_id = "start"
        for ans in answers:
            q = self.get_question(current_id)
            if not q:
                return []
            next_id = None
            for opt in q.get("options", []):
                if opt["label"] == ans["option"]:
                    next_id = opt.get("next") or opt.get("flow")
                    break
            if not next_id:
                return []
            if next_id in self.flows:
                return self.get_flow_steps(next_id)
            current_id = next_id
        return self.get_question(current_id)

