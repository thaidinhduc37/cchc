# services/unified_processor.py - Phiên bản tối ưu, tập trung hiệu suất

import os
import json
import pandas as pd
import logging
import asyncio
from datetime import datetime
from utils.response_formatter import format_response
from .vector_rag.lightweight_rag_engine import LightweightRAGEngine, create_rag_engine
from .vector_rag.lightweight_config import SYSTEM_CONFIG

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== SIMPLE RAG FALLBACK =====
def simple_excel_search(user_input: str, domain: str = "xuatnhapcanh") -> str:
    """Tìm kiếm đơn giản trong file Excel question.xlsx"""
    try:
        excel_path = f"dataset/{domain}/question.xlsx"
        if not os.path.exists(excel_path):
            return None
            
        df = pd.read_excel(excel_path)
        df.columns = df.columns.str.lower()
        
        if 'question' not in df.columns or 'answer' not in df.columns:
            return None
            
        questions = df["question"].fillna("").astype(str).tolist()
        answers = df["answer"].fillna("").astype(str).tolist()
        
        # Simple keyword matching
        user_lower = user_input.lower()
        for i, question in enumerate(questions):
            if any(word in question.lower() for word in user_lower.split() if len(word) > 2):
                if i < len(answers) and answers[i].strip():
                    return answers[i]
        
        return None
    except Exception as e:
        logger.error(f"Error in simple_excel_search: {e}")
        return None

def simple_json_search(user_input: str, domain: str = "xuatnhapcanh") -> str:
    """Tìm kiếm đơn giản trong responses.json"""
    try:
        json_path = f"dataset/{domain}/responses.json"
        if not os.path.exists(json_path):
            return None
            
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        entries = data.get("entries", [])
        user_lower = user_input.lower()
        
        for entry in entries:
            keywords = entry.get("keywords", [])
            if any(kw.lower() in user_lower for kw in keywords):
                responses = entry.get("responses", [])
                if responses:
                    return "\n".join(responses)
        
        return None
    except Exception as e:
        logger.error(f"Error in simple_json_search: {e}")
        return None

# ===== GREETING & FALLBACK =====
def handle_greeting(user_input: str) -> str:
    """Xử lý chào hỏi"""
    greeting_words = ["chào", "hi", "hello", "xin chào", "good morning"]
    if any(word in user_input.lower() for word in greeting_words):
        return (
            "Xin chào! Tôi là trợ lý hỗ trợ thông tin về thủ tục hành chính.\n\n"
            "Tôi có thể giúp bạn:\n"
            "• Trả lời thắc mắc về thủ tục DVC\n" 
            "• Hướng dẫn từng bước làm hồ sơ\n\n"
            "Bạn cần hỗ trợ gì ạ?"
        )
    return None

def handle_sensitive_content(user_input: str) -> str:
    """Chặn nội dung nhạy cảm"""
    sensitive_keywords = [
        "vương đình huệ", "nguyễn phú trọng", "chủ tịch", "tổng bí thư",
        "chính trị", "bầu cử", "chính quyền"
    ]
    if any(kw in user_input.lower() for kw in sensitive_keywords):
        return "❌ Tôi chỉ hỗ trợ các vấn đề thủ tục hành chính, không trả lời về nội dung chính trị."
    return None

# ===== MAIN PROCESSOR =====
def process_user_query(user_input: str, user_id: str, domain: str = None) -> dict:
    """
    Xử lý câu hỏi người dùng - TÁCH BIỆT HOÀN TOÀN VỚI FLOW
    Flow được xử lý ở ChatController, đây chỉ xử lý Q&A thông thường
    """
    
    user_input = user_input.strip()
    if not user_input:
        return format_response("❓ Vui lòng nhập câu hỏi.", source="system")

    domain = domain or "xuatnhapcanh"
    
    logger.info(f"Processing query: '{user_input[:50]}...' for domain: {domain}")

    # 1. Xử lý chào hỏi
    greeting_response = handle_greeting(user_input)
    if greeting_response:
        return format_response(greeting_response, source="greeting")

    # 2. Chặn nội dung nhạy cảm  
    sensitive_response = handle_sensitive_content(user_input)
    if sensitive_response:
        return format_response(sensitive_response, source="filter")

    # 3. Tìm kiếm trong Excel (ưu tiên cao)
    excel_result = simple_excel_search(user_input, domain)
    if excel_result:
        logger.info(f"✅ Found answer in Excel for: {user_input[:30]}")
        return format_response(excel_result, source="excel", metadata={"domain": domain})

    # 4. Tìm kiếm trong JSON responses
    json_result = simple_json_search(user_input, domain)
    if json_result:
        logger.info(f"✅ Found answer in JSON for: {user_input[:30]}")
        return format_response(json_result, source="json", metadata={"domain": domain})

    # 5. Fallback - không tìm thấy
    fallback_message = (
        f"Xin lỗi, tôi chưa tìm thấy thông tin về '{user_input}'. "
        "Bạn có thể:\n"
        "• Thử diễn đạt lại câu hỏi\n"
        "• Sử dụng 'Hướng dẫn quy trình' để được hướng dẫn từng bước"
    )
    
    logger.warning(f"❌ No answer found for: {user_input}")
    return format_response(fallback_message, source="fallback", metadata={"domain": domain})

# ===== DOMAIN DETECTION (đơn giản) =====
def detect_domain(user_input: str) -> str:
    """Phát hiện domain đơn giản"""
    lowered = user_input.lower()
    
    if any(k in lowered for k in ["hộ chiếu", "xuất nhập cảnh", "passport", "visa"]):
        return "xuatnhapcanh"
    elif any(k in lowered for k in ["căn cước", "cccd", "chứng minh"]):
        return "cancuoc" 
    elif any(k in lowered for k in ["đăng ký xe", "biển số", "xe máy"]):
        return "dangkyxe"
    elif any(k in lowered for k in ["thường trú", "tạm trú", "cư trú"]):
        return "cutru"
    
    return "xuatnhapcanh"  # default

# ===== UTILITY FUNCTIONS =====
def log_unanswered_question(user_input: str, domain: str):
    """Log câu hỏi chưa có đáp án để admin review"""
    try:
        log_file = f"logs/unanswered_{domain}.txt"
        os.makedirs("logs", exist_ok=True)
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} - {user_input}\n")
    except Exception as e:
        logger.error(f"Error logging unanswered question: {e}")

def get_quick_stats() -> dict:
    """Thống kê nhanh hệ thống"""
    stats = {
        "available_domains": ["xuatnhapcanh", "cancuoc", "dangkyxe", "cutru"],
        "data_sources": ["excel", "json", "greeting", "fallback"],
        "status": "optimized_for_flow"
    }
    
    # Check data availability
    for domain in stats["available_domains"]:
        excel_exists = os.path.exists(f"dataset/{domain}/question.xlsx")
        json_exists = os.path.exists(f"dataset/{domain}/responses.json")
        stats[f"{domain}_data"] = {"excel": excel_exists, "json": json_exists}
    
    return stats