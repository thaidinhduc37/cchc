from flask import Blueprint, request, jsonify
from common.conversation import (
    add_to_history,
    clear_history,
    get_history,
    get_step_id,
    set_step_id
)
from common.ai import query_ollama_with_context
from common.domain_router import get_domain_context, get_flow_handler
import tempfile
import os

bp = Blueprint('chatbot', __name__, url_prefix='/chat')

# Lưu session tạm thời
temp_dir = tempfile.gettempdir()
def temp_session_path(session_id):
    return os.path.join(temp_dir, f"chat_session_{session_id}.txt")

def save_session_to_temp(session_id, user_msg, bot_msg):
    path = temp_session_path(session_id)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"User: {user_msg}\nBot: {bot_msg}\n---\n")

def clear_temp_session(session_id):
    path = temp_session_path(session_id)
    if os.path.exists(path):
        os.remove(path)

# Nhận diện câu chào đơn giản
def is_greeting(msg):
    msg = msg.lower().strip()
    return any(greet in msg for greet in ["chào", "hello", "hi", "alo", "xin chào", "hey"])

@bp.route('/massage', methods=['POST'])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id", "default")

    if is_greeting(message):
        step_id = get_step_id(session_id) or "start"
        set_step_id(session_id, step_id)
        answer = "Chào bạn! Tôi là trợ lý ảo giúp bạn thực hiện các thủ tục hành chính. Bạn cần tôi hỗ trợ gì nào?"
        add_to_history(session_id, message, answer)
        save_session_to_temp(session_id, message, answer)
        return jsonify({"response": answer, "session_id": session_id})

    # Dò domain tương ứng để tìm flow handler (nếu có)
    flow_handler = get_flow_handler(message)
    if flow_handler:
        step_id = get_step_id(session_id) or "start"
        result = flow_handler(step_id, message)

        if "next" in result:
            set_step_id(session_id, result["next"])
        else:
            set_step_id(session_id, step_id)  # Giữ nguyên nếu chưa chọn đúng

        if result.get("done"):
            clear_history(session_id)

        answer = result.get("message", "Tôi chưa rõ ý bạn, bạn có thể nói lại không?")
        if "options" in result:
            answer += "\nLựa chọn:\n" + "\n".join(f"- {opt}" for opt in result["options"])

        add_to_history(session_id, message, answer)
        save_session_to_temp(session_id, message, answer)
        return jsonify({"response": answer, "session_id": session_id})

    # Nếu không có flow, fallback AI trả lời tự do
    context = get_domain_context(message)
    answer = query_ollama_with_context(message, context, session_id)

    add_to_history(session_id, message, answer)
    save_session_to_temp(session_id, message, answer)

    return jsonify({"response": answer, "session_id": session_id})

@bp.route('/end-session', methods=['POST'])
def end_session():
    data = request.get_json()
    session_id = data.get("session_id", "default")
    clear_history(session_id)
    clear_temp_session(session_id)
    return jsonify({"message": "Đã kết thúc phiên làm việc và xóa dữ liệu tạm", "session_id": session_id})
