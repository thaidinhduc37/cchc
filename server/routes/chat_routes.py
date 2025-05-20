from flask import Blueprint, request, jsonify
from controllers.chat_controller import ChatController

chat_routes = Blueprint("chat_routes", __name__)
chat_controller = ChatController()

@chat_routes.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_id = data.get("user_id")
    message = data.get("message")

    if not user_id or not message:
        return jsonify({"error": "Thiếu user_id hoặc message"}), 400

    reply = chat_controller.handle_chat(user_id, message)
    return jsonify({"reply": reply})
