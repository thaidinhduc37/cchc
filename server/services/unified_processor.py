# services/unified_processor.py - Enhanced với RAG Lightweight

import os
import json
import pandas as pd
import logging
import asyncio
from datetime import datetime
from utils.response_formatter import format_response

# ===== RAG INTEGRATION =====
try:
    from .vector_rag.lightweight_rag_engine import LightweightRAGEngine, create_rag_engine
    from .vector_rag.lightweight_config import SYSTEM_CONFIG
    RAG_AVAILABLE = True
    print("✅ RAG components loaded successfully")
except ImportError as e:
    RAG_AVAILABLE = False
    print(f"⚠️ RAG components not available: {e}")
except Exception as e:
    RAG_AVAILABLE = False
    print(f"⚠️ RAG initialization error: {e}")

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== GLOBAL RAG ENGINE =====
_global_rag_engine = None
_rag_initialization_attempted = False

def get_rag_engine():
    """Get global RAG engine instance"""
    global _global_rag_engine
    return _global_rag_engine

async def initialize_rag_engine(force_rebuild=False):
    """Initialize RAG engine globally"""
    global _global_rag_engine, _rag_initialization_attempted
    
    if not RAG_AVAILABLE:
        logger.warning("⚠️ RAG not available, skipping initialization")
        return False
    
    if _global_rag_engine and not force_rebuild:
        logger.info("✅ RAG engine already initialized")
        return True
    
    if _rag_initialization_attempted and not force_rebuild:
        logger.warning("⚠️ RAG initialization already attempted and failed")
        return False
    
    _rag_initialization_attempted = True
    
    try:
        logger.info("🚀 Initializing RAG engine...")
        
        # Create RAG engine
        gemini_key = os.getenv('GEMINI_API_KEY')
        _global_rag_engine = create_rag_engine(gemini_api_key=gemini_key)
        
        # Initialize system
        init_result = await _global_rag_engine.initialize_system(force_rebuild=force_rebuild)
        
        if init_result['success']:
            logger.info(f"✅ RAG engine initialized: {init_result['message']}")
            return True
        else:
            logger.error(f"❌ RAG initialization failed: {init_result['message']}")
            _global_rag_engine = None
            return False
            
    except Exception as e:
        logger.error(f"❌ RAG engine initialization error: {e}")
        _global_rag_engine = None
        return False

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

# ===== RAG QUERY PROCESSING =====
async def query_rag_engine(user_input: str, domain: str = "xuatnhapcanh") -> dict:
    """Query RAG engine với error handling"""
    rag_engine = get_rag_engine()
    
    if not rag_engine:
        return {
            'success': False,
            'answer': None,
            'error': 'RAG engine not available'
        }
    
    try:
        logger.info(f"🤖 Querying RAG engine for: {user_input[:50]}...")
        
        # Query với timeout
        result = await asyncio.wait_for(
            rag_engine.query_async(user_input, k=3, include_sources=True),
            timeout=15.0
        )
        
        if result['success']:
            logger.info(f"✅ RAG response generated (confidence: {result['metadata'].get('confidence', 'N/A')})")
            return {
                'success': True,
                'answer': result['answer'],
                'sources': result['sources'],
                'metadata': result['metadata']
            }
        else:
            logger.warning(f"⚠️ RAG query failed: {result.get('error', 'Unknown error')}")
            return {
                'success': False,
                'answer': None,
                'error': result.get('error', 'RAG query failed')
            }
            
    except asyncio.TimeoutError:
        logger.error("❌ RAG query timeout")
        return {
            'success': False,
            'answer': None,
            'error': 'RAG query timeout'
        }
    except Exception as e:
        logger.error(f"❌ RAG query error: {e}")
        return {
            'success': False,
            'answer': None,
            'error': str(e)
        }

def sync_query_rag_engine(user_input: str, domain: str = "xuatnhapcanh") -> dict:
    """Sync wrapper cho RAG query"""
    try:
        return asyncio.run(query_rag_engine(user_input, domain))
    except Exception as e:
        logger.error(f"❌ Sync RAG query error: {e}")
        return {
            'success': False,
            'answer': None,
            'error': str(e)
        }

# ===== GREETING & FILTERS =====
def handle_greeting(user_input: str) -> str:
    """Xử lý chào hỏi"""
    greeting_words = ["chào", "hi", "hello", "xin chào", "good morning"]
    if any(word in user_input.lower() for word in greeting_words):
        return (
            "Xin chào! Tôi là trợ lý hỗ trợ thông tin về thủ tục hành chính.\n\n"
            "Tôi có thể giúp bạn:\n"
            "• Trả lời thắc mắc về thủ tục DVC\n" 
            "• Hướng dẫn từng bước làm hồ sơ\n"
            "• Tìm kiếm trong cơ sở dữ liệu pháp lý\n\n"
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

# ===== MAIN PROCESSOR - ENHANCED =====
def process_user_query(user_input: str, user_id: str, domain: str = None) -> dict:
    """
    Xử lý câu hỏi người dùng - ENHANCED với RAG
    
    PRIORITY ORDER:
    1. Greeting handling
    2. Sensitive content filter  
    3. Excel search (highest priority)
    4. JSON responses search
    5. **RAG engine query (NEW - before fallback)**
    6. Fallback message
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

    # 3. Tìm kiếm trong Excel (ưu tiên cao nhất)
    excel_result = simple_excel_search(user_input, domain)
    if excel_result:
        logger.info(f"✅ Found answer in Excel for: {user_input[:30]}")
        return format_response(excel_result, source="excel", metadata={"domain": domain})

    # 4. Tìm kiếm trong JSON responses
    json_result = simple_json_search(user_input, domain)
    if json_result:
        logger.info(f"✅ Found answer in JSON for: {user_input[:30]}")
        return format_response(json_result, source="json", metadata={"domain": domain})

    # 5. **NEW: RAG Engine Query**
    if RAG_AVAILABLE and get_rag_engine():
        logger.info(f"🤖 Trying RAG engine for: {user_input[:30]}")
        
        rag_result = sync_query_rag_engine(user_input, domain)
        
        if rag_result['success'] and rag_result['answer']:
            logger.info(f"✅ Found answer via RAG for: {user_input[:30]}")
            
            # Format RAG response với metadata đầy đủ
            metadata = {
                "domain": domain,
                "source_type": "rag",
                "confidence": rag_result['metadata'].get('confidence', 0),
                "processing_time": rag_result['metadata'].get('total_time', 0),
                "provider": rag_result['metadata'].get('provider_used', 'unknown'),
                "sources_count": len(rag_result.get('sources', []))
            }
            
            # Enhance answer với source info
            enhanced_answer = rag_result['answer']
            if rag_result.get('sources'):
                enhanced_answer += f"\n\n💡 *Dựa trên {len(rag_result['sources'])} tài liệu pháp lý*"
            
            return format_response(
                enhanced_answer, 
                source="rag",
                metadata=metadata
            )
        else:
            logger.warning(f"⚠️ RAG engine failed: {rag_result.get('error', 'Unknown error')}")

    # 6. Fallback - không tìm thấy anywhere
    fallback_message = (
        f"Xin lỗi, tôi chưa tìm thấy thông tin về '{user_input}'. "
        "Bạn có thể:\n"
        "• Thử diễn đạt lại câu hỏi\n"
        "• Sử dụng 'Hướng dẫn quy trình' để được hướng dẫn từng bước\n"
        "• Liên hệ trực tiếp cơ quan có thẩm quyền"
    )
    
    logger.warning(f"❌ No answer found anywhere for: {user_input}")
    return format_response(fallback_message, source="fallback", metadata={"domain": domain})

# ===== DOMAIN DETECTION (giữ nguyên) =====
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

# ===== RAG MANAGEMENT FUNCTIONS =====
async def initialize_system(force_rebuild=False):
    """Initialize toàn bộ hệ thống including RAG"""
    logger.info("🔧 Initializing unified processor system...")
    
    success = await initialize_rag_engine(force_rebuild=force_rebuild)
    
    return {
        'success': True,  # Always success cho unified processor
        'rag_available': success,
        'message': f"System initialized. RAG: {'✅' if success else '❌'}"
    }

def get_system_status():
    """Lấy status tổng quan của hệ thống"""
    rag_engine = get_rag_engine()
    
    status = {
        'unified_processor': {
            'available': True,
            'data_sources': ['excel', 'json', 'rag', 'fallback'],
            'domains': ['xuatnhapcanh', 'cancuoc', 'dangkyxe', 'cutru']
        },
        'rag_engine': {
            'available': rag_engine is not None,
            'initialized': _rag_initialization_attempted
        }
    }
    
    if rag_engine:
        try:
            rag_stats = rag_engine.get_system_stats()
            status['rag_engine'].update({
                'stats': rag_stats,
                'vector_store_docs': rag_stats.get('vector_store', {}).get('total_documents', 0),
                'llm_providers': rag_stats.get('llm_providers', {}).get('providers', {}),
                'session_queries': rag_stats.get('session', {}).get('queries_processed', 0)
            })
        except Exception as e:
            status['rag_engine']['error'] = str(e)
    
    return status

async def refresh_rag_engine():
    """Refresh RAG engine"""
    rag_engine = get_rag_engine()
    if rag_engine:
        rag_engine.refresh_system()
        logger.info("🔄 RAG engine refreshed")
        return True
    return False

def clear_all_caches():
    """Clear tất cả caches"""
    rag_engine = get_rag_engine()
    if rag_engine:
        rag_engine.clear_caches()
        logger.info("🗑️ All caches cleared")

# ===== UTILITY FUNCTIONS (giữ nguyên) =====
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
        "data_sources": ["excel", "json", "rag", "greeting", "fallback"],
        "rag_enabled": RAG_AVAILABLE and get_rag_engine() is not None,
        "status": "enhanced_with_rag"
    }
    
    # Check data availability
    for domain in stats["available_domains"]:
        excel_exists = os.path.exists(f"dataset/{domain}/question.xlsx")
        json_exists = os.path.exists(f"dataset/{domain}/responses.json")
        stats[f"{domain}_data"] = {"excel": excel_exists, "json": json_exists}
    
    # RAG stats
    if stats["rag_enabled"]:
        try:
            rag_engine = get_rag_engine()
            rag_system_stats = rag_engine.get_system_stats()
            stats["rag_stats"] = {
                "vector_docs": rag_system_stats.get('vector_store', {}).get('total_documents', 0),
                "session_queries": rag_system_stats.get('session', {}).get('queries_processed', 0),
                "avg_response_time": rag_system_stats.get('session', {}).get('avg_response_time', 0)
            }
        except Exception as e:
            stats["rag_error"] = str(e)
    
    return stats

# ===== ASYNC WRAPPER FOR EXTERNAL USE =====
async def process_user_query_async(user_input: str, user_id: str, domain: str = None) -> dict:
    """Async wrapper cho process_user_query"""
    # Đối với queries thông thường, vẫn dùng sync version
    # Vì Excel/JSON searches là sync và nhanh
    return process_user_query(user_input, user_id, domain)

# ===== INITIALIZATION ON IMPORT =====
# Auto-initialize RAG engine khi module được import (optional)
# Uncomment nếu muốn auto-init
# import threading
# def _auto_init_rag():
#     asyncio.run(initialize_rag_engine())
# 
# threading.Thread(target=_auto_init_rag, daemon=True).start()