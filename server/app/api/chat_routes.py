# server/routes/chat_routes.py

from flask import Blueprint, request, jsonify, send_from_directory
import logging
import os
from app.api.chat_controller import ChatController

# Initialize services
chat_routes = Blueprint("chat_routes", __name__)
controller = ChatController()

@chat_routes.route("/chat/ask", methods=["OPTIONS"]) 
def handle_options():
    response = jsonify({"status": "OK"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    return response

@chat_routes.route("/chat/ask", methods=["POST"]) 
# Bỏ @jwt_required decorator
def ask():
    try:
        data = request.json
        if not data:
            return jsonify({
                "error": "Không có dữ liệu gửi lên",
                "status": "error"
            }), 400

        # Dùng anonymous user_id 
        user_id = "anonymous"
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
        return jsonify(result)

    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        return jsonify({
            "error": "Có lỗi xảy ra",
            "status": "error"
        }), 500
    

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