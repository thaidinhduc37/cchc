# server/routes/chat_routes.py

from flask import Blueprint, request, jsonify , send_from_directory
from controllers.chat_controller import ChatController
from utils.response_formatter import format_response  # ✅ Import thiếu
import os
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
                    # ✅ THÊM TTS FIELDS
                    "tts_text": result.get('tts_text'),
                    "should_speak": result.get('should_speak', False),
                    # Giữ lại các trường đặc biệt cho flow
                    **{k: v for k, v in result.items() if k in [
                        'buttons', 'options', 'show_flow_button', 'button_label',
                        'step_mode', 'flow_id', 'step_index', 'total_steps',
                        'wait_for_user', 'done', 'tts', 'image', 'link',
                        'current_step', 'guide_image', 'step_info',
                        'flow_data', 'navigation', 'progress_percent',
                        'tts_text', 'should_speak'  # ✅ THÊM 2 FIELD TTS
                    ]}
                })

        # Fallback response
        return jsonify(format_response(
            text="Xin lỗi, tôi không tìm thấy thông tin phù hợp.",
            source="error"
        ))

    except Exception as e:
        logging.error(f"Lỗi xử lý chat: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Có lỗi xảy ra, vui lòng thử lại sau",
            "status": "error",
            "details": str(e)
        }), 500

# Các route khác giữ nguyên...

# THAY ĐỔI ROUTE PATTERN
@chat_routes.route("/static/dataset/<path:filepath>")
def serve_static(filepath):
      
    try:
        # Build path từ dataset folder
        full_path = os.path.join(os.getcwd(), "dataset", filepath)
        
        
        if os.path.exists(full_path):
            directory = os.path.dirname(full_path)
            filename = os.path.basename(full_path)
            return send_from_directory(directory, filename)
        else:
            return "File not found", 404
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return f"Error: {e}", 500