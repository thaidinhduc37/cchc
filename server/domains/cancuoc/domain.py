import json
import os
from common.utils import normalize_text

BASE_DIR = os.path.dirname(__file__)

# === Dữ liệu văn bản câu trả lời ===
file_path = os.path.join(BASE_DIR, "cancuoc.json")
with open(file_path, "r", encoding="utf-8") as f:
    DATA = json.load(f)["entries"]

# === Load flow chính ===
def get_interaction_flow():
    flow_path = os.path.join(BASE_DIR, "interaction_flow_cccd_steps.json")
    with open(flow_path, encoding="utf-8") as f:
        return json.load(f)["flow"]

# === Load flow scenarios (theo loại công dân) ===
def get_flow_scenarios():
    path = os.path.join(BASE_DIR, "flow_scenarios.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def get_flow_sequence_by_scenario(scenario_id):
    scenarios = get_flow_scenarios()
    return scenarios.get(scenario_id, {}).get("steps", [])

def start_flow_for(scenario_id):
    sequence = get_flow_sequence_by_scenario(scenario_id)
    if not sequence:
        return {"error": "Không tìm thấy luồng phù hợp"}
    return {"start": sequence[0], "sequence": sequence}

# === Truy xuất step cụ thể ===
def get_step_by_id(step_id):
    flow = get_interaction_flow()
    return next((step for step in flow if step["id"] == step_id), None)

# === Lấy bước tiếp theo ===
def get_next_step(current_id, user_input=None):
    step = get_step_by_id(current_id)
    if not step:
        return {"error": "Không tìm thấy bước hiện tại."}

    if step["type"] == "end":
        return {"done": True, "message": step["question"]}

    if step["type"] in ["confirmation", "info"]:
        return {"next": step["next"], "message": step["question"]}

    if step["type"] == "choice":
        options = step.get("options", [])
        normalized_input = normalize_text(user_input or "")
        matched = next(
            (opt for opt in options if normalized_input in normalize_text(opt["label"]) or normalize_text(opt["label"]) in normalized_input),
            None
        )
        if matched:
            return {"next": matched["next"], "message": step["question"]}
        else:
            return {
                "next": current_id,
                "message": step["question"],
                "options": [opt["label"] for opt in options]
            }

    return {"error": "Loại bước không hỗ trợ."}

# === Tạo context tổng hợp cho AI hoặc chatbot ===
def get_domain_context():
    flow_data = get_interaction_flow()
    flow_context = "\n".join(f"[{step['id']}] {step['question']}" for step in flow_data)

    context_lines = []
    for entry in DATA:
        context_lines.append(f"Thủ tục: {entry['procedure']}")
        for res in entry["responses"]:
            context_lines.append(f"- {res}")

    return (
        "Bạn là trợ lý ảo hỗ trợ công dân làm thủ tục cấp Căn cước công dân.\n\n"
        "Thông tin các bước theo hướng dẫn:\n" + flow_context + "\n\n"
        "Thông tin từ tài liệu chính thức:\n" + "\n".join(context_lines)
    )