from flask import Blueprint, request, jsonify
from controllers.assistant_controller import AssistantController

assistant_routes = Blueprint("assistant_routes", __name__)

# Định nghĩa controller theo flow mỗi lĩnh vực
controllers = {}

@assistant_routes.route("/api/assistant/start", methods=["POST"])
def start_assistant():
    data = request.get_json()
    user_id = data.get("user_id")
    domain = data.get("domain")

    if not user_id or not domain:
        return jsonify({"error": "Thiếu user_id hoặc domain"}), 400

    flow_path = f"dataset/{domain}/flow.json"
    controller = AssistantController(flow_path)
    controllers[user_id] = controller  # lưu để dùng tiếp

    step = controller.start_assistant(user_id)
    return jsonify({"step": step})

@assistant_routes.route("/api/assistant/next", methods=["POST"])
def next_step():
    data = request.get_json()
    user_id = data.get("user_id")
    answer = data.get("answer")

    if not user_id or not answer:
        return jsonify({"error": "Thiếu user_id hoặc answer"}), 400

    controller = controllers.get(user_id)
    if not controller:
        return jsonify({"error": "Chưa khởi động trợ lý ảo"}), 400

    result = controller.next_step(user_id, answer)
    return jsonify(result)
