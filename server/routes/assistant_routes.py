from flask import Blueprint, request, jsonify
from controllers.assistant_controller import AssistantController
import logging

# Khởi tạo logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AssistantRoutes")

# Tạo Blueprint
assistant_routes = Blueprint("assistant_routes", __name__)

# Khởi tạo controller
controller = AssistantController(domain="xuatnhapcanh")

@assistant_routes.route("/assistant/start", methods=["POST"])
def start_assistant():
    """Khởi động trợ lý ảo"""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id", "anonymous")
        enable_tts = data.get("enable_tts", True)
        
        logger.info(f"Starting assistant for user: {user_id}")
        result = controller.start_assistant(user_id, enable_tts)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in start_assistant: {str(e)}")
        return jsonify({
            "text": "❌ Lỗi khởi động trợ lý",
            "source": "assistant",
            "success": False,
            "error": str(e)
        }), 500

@assistant_routes.route("/assistant/next", methods=["POST"])
def next_step():
    """Xử lý bước tiếp theo trong cuộc hội thoại"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "text": "❌ Dữ liệu đầu vào không hợp lệ",
                "source": "assistant",
                "success": False
            }), 400
        
        user_id = data.get("user_id", "anonymous")
        message = data.get("message", "")
        
        if not message.strip():
            return jsonify({
                "text": "⚠️ Vui lòng nhập tin nhắn",
                "source": "assistant",
                "success": False
            }), 400
        
        logger.info(f"Processing message from user {user_id}: {message[:50]}...")
        result = controller.next_step(user_id, message)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in next_step: {str(e)}")
        return jsonify({
            "text": "❌ Lỗi xử lý tin nhắn",
            "source": "assistant",
            "success": False,
            "error": str(e)
        }), 500

@assistant_routes.route("/assistant/toggle-tts", methods=["POST"])
def toggle_tts():
    """Bật/tắt chức năng Text-to-Speech"""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id", "anonymous")
        enabled = data.get("enabled", True)
        
        result = controller.toggle_tts(user_id, enabled)
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in toggle_tts: {str(e)}")
        return jsonify({
            "text": "❌ Lỗi điều khiển giọng nói",
            "source": "assistant",
            "success": False,
            "error": str(e)
        }), 500

@assistant_routes.route("/assistant/session/<user_id>", methods=["GET"])
def get_session_info(user_id):
    """Lấy thông tin session của user"""
    try:
        result = controller.get_session_info(user_id)
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_session_info: {str(e)}")
        return jsonify({
            "exists": False,
            "error": str(e)
        }), 500

@assistant_routes.route("/assistant/stop-speech", methods=["POST"])
def stop_speech():
    """Dừng tất cả phát âm"""
    try:
        controller.stop_all_speech()
        return jsonify({
            "message": "🛑 Đã dừng phát âm",
            "success": True
        }), 200
        
    except Exception as e:
        logger.error(f"Error in stop_speech: {str(e)}")
        return jsonify({
            "message": "❌ Lỗi dừng phát âm",
            "success": False,
            "error": str(e)
        }), 500

@assistant_routes.route("/assistant/cleanup", methods=["POST"])
def cleanup_sessions():
    """Dọn dẹp các session cũ"""
    try:
        data = request.get_json() or {}
        max_age_hours = data.get("max_age_hours", 24)
        
        cleaned_count = controller.cleanup_old_sessions(max_age_hours)
        
        return jsonify({
            "message": f"🧹 Đã dọn dẹp {cleaned_count} session cũ",
            "cleaned_sessions": cleaned_count,
            "success": True
        }), 200
        
    except Exception as e:
        logger.error(f"Error in cleanup_sessions: {str(e)}")
        return jsonify({
            "message": "❌ Lỗi dọn dẹp session",
            "success": False,
            "error": str(e)
        }), 500

@assistant_routes.route("/assistant/health", methods=["GET"])
def health_check():
    """Kiểm tra tình trạng hoạt động của assistant"""
    try:
        return jsonify({
            "status": "healthy",
            "message": "🤖 Trợ lý ảo hoạt động bình thường",
            "domain": controller.domain,
            "tts_available": controller.tts.is_available(),
            "success": True
        }), 200
        
    except Exception as e:
        logger.error(f"Error in health_check: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "message": "❌ Trợ lý gặp sự cố",
            "success": False,
            "error": str(e)
        }), 500

# Error handlers
@assistant_routes.errorhandler(404)
def not_found(error):
    return jsonify({
        "message": "❌ Endpoint không tồn tại",
        "success": False
    }), 404

@assistant_routes.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "message": "❌ Phương thức HTTP không được hỗ trợ",
        "success": False
    }), 405

@assistant_routes.errorhandler(500)
def internal_error(error):
    return jsonify({
        "message": "❌ Lỗi server nội bộ",
        "success": False
    }), 500