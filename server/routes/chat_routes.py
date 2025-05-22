# server/routes/chat_routes.py

from flask import Blueprint, request, jsonify
from controllers.chat_controller import ChatController

chat_routes = Blueprint("chat_routes", __name__)
controller = ChatController()

@chat_routes.route("/chat/ask", methods=["POST"])
def ask():
    data = request.json
    user_id = data.get("user_id", "anonymous")
    message = data.get("message", "")
    domain = data.get("domain", "xuatnhapcanh")

    # Kiểm tra nếu user hỏi về quy trình/các bước/hướng dẫn
    keywords = ["quy trình", "các bước", "hướng dẫn", "thủ tục"]
    show_flow_button = any(kw in message.lower() for kw in keywords)

    result = controller.handle_chat(user_id, message, domain)

    if show_flow_button:
        result["show_flow_button"] = True

    return jsonify(result)
