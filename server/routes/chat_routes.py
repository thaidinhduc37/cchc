# server/routes/chat_routes.py

from flask import Blueprint, request, jsonify
from controllers.chat_controller import ChatController
from utils.response_formatter import format_response  # ✅ Import thiếu
import logging
from datetime import datetime

chat_routes = Blueprint("chat_routes", __name__)
controller = ChatController()

@chat_routes.route("/chat/ask", methods=["POST"])
def ask():
    try:
        data = request.json
        if not data:
            return jsonify({
                "error": "Không có dữ liệu gửi lên",
                "status": "error"
            }), 400

        # Validate input
        user_id = data.get("user_id", "anonymous")
        message = data.get("message", "").strip()
        domain = data.get("domain", "xuatnhapcanh")

        if not message:
            return jsonify({
                "error": "Vui lòng nhập nội dung tin nhắn",
                "status": "error"
            }), 400

        # Log request
        logging.info(f"Nhận câu hỏi từ user {user_id}: {message}")

        # Xử lý câu hỏi và lấy kết quả
        result = controller.handle_chat(user_id, message, domain)
        
        # Debug logging
        logging.debug(f"Controller result: {result}")

        # ✅ Xử lý response từ controller
        if result and isinstance(result, dict):
            # Controller đã trả về format đúng, chỉ cần trả về trực tiếp
            if 'reply' in result:
                return jsonify({
                    "reply": result['reply'],
                    "source": result.get('source', 'unknown'),
                    "type": result.get('type', 'answer'),
                    "timestamp": datetime.now().isoformat(),
                    "metadata": result.get('metadata', {}),
                    "domain": result.get('domain', domain),
                    # Giữ lại các trường đặc biệt cho flow
                    **{k: v for k, v in result.items() if k in [
                        'buttons', 'options', 'show_flow_button', 'button_label',
                        'step_mode', 'flow_id', 'step_index', 'total_steps',
                        'wait_for_user', 'done', 'tts', 'image', 'link'
                    ]}
                })

        # Fallback response
        return jsonify(format_response(
            text="Xin lỗi, tôi không tìm thấy thông tin phù hợp.",
            source="error"
        ))

    except Exception as e:
        logging.error(f"Lỗi xử lý chat: {str(e)}", exc_info=True)  # ✅ Thêm stack trace
        return jsonify({
            "error": "Có lỗi xảy ra, vui lòng thử lại sau",
            "status": "error",
            "details": str(e)
        }), 500