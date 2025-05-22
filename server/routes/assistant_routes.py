from flask import Blueprint, request, jsonify
from controllers.assistant_controller import AssistantController

assistant_routes = Blueprint("assistant_routes", __name__)
controller = AssistantController(domain="xuatnhapcanh")

@assistant_routes.route("/assistant/start", methods=["POST"])
def start_assistant():
    user_id = request.json.get("user_id", "anonymous")
    result = controller.start_assistant(user_id)
    return jsonify(result)

@assistant_routes.route("/assistant/next", methods=["POST"])
def next_step():
    data = request.json
    user_id = data.get("user_id", "anonymous")
    message = data.get("message", "")
    result = controller.next_step(user_id, message)
    return jsonify(result)
