# services/unified_processor.py - OPTIMIZED with RAG Integration

import os
import pandas as pd
import json
import logging
import asyncio
from datetime import datetime
from utils.response_formatter import format_response

# ===== VECTOR RAG INTEGRATION =====
try:
    from services.vector_rag.rag_engine import RAGEngine
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

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

async def initialize_rag_engine(domain: str = "xuatnhapcanh"):
    """Initialize RAG Engine - Simplified"""
    global _global_rag_engine, _rag_initialization_attempted
    
    if not RAG_AVAILABLE:
        logger.warning("⚠️ RAG Engine not available")
        return False
    
    if _global_rag_engine and _global_rag_engine.is_initialized:
        logger.info("✅ RAG Engine already initialized")
        return True
    
    if _rag_initialization_attempted:
        logger.warning("⚠️ RAG initialization already attempted")
        return False
    
    _rag_initialization_attempted = True
    
    try:
        logger.info("🚀 Initializing RAG Engine...")
        _global_rag_engine = RAGEngine()
        
        # Initialize with timeout
        result = await asyncio.wait_for(
            _global_rag_engine.initialize(force_rebuild=False),
            timeout=120.0
        )
        
        if result.get('success', False):
            stats = _global_rag_engine.get_stats()
            docs_count = stats.get('components', {}).get('vector_store', {}).get('total_documents', 0)
            logger.info(f"✅ RAG Engine initialized: {docs_count} docs")
            return True
        else:
            logger.error(f"❌ RAG initialization failed: {result.get('message', 'Unknown')}")
            _global_rag_engine = None
            return False
            
    except Exception as e:
        logger.error(f"❌ RAG initialization error: {e}")
        _global_rag_engine = None
        return False

# ===== OPTIMIZED EXCEL + JSON SEARCH =====
def smart_qa_search(user_input: str, domain: str = "xuatnhapcanh") -> str:
    """Smart Q&A search - Excel first, then JSON fallback"""
    try:
        logger.info(f"📊 Smart search: '{user_input[:30]}...'")
        
        # Step 1: Try Excel first
        excel_result = _search_excel_qa(user_input, domain)
        if excel_result:
            logger.info("✅ Found answer in Excel")
            return excel_result
        
        # Step 2: Try JSON fallback
        json_result = _search_json_qa(user_input, domain)
        if json_result:
            logger.info("✅ Found answer in JSON")
            return json_result
        
        logger.info("❌ No answer in Excel/JSON")
        return None
        
    except Exception as e:
        logger.error(f"❌ Smart search error: {e}")
        return None

def _search_excel_qa(user_input: str, domain: str) -> str:
    """Search in Excel Q&A"""
    try:
        excel_path = f"dataset/{domain}/question.xlsx"
        
        if not os.path.exists(excel_path):
            logger.debug(f"📊 Excel not found: {excel_path}")
            return None

        df = pd.read_excel(excel_path)
        df.columns = df.columns.str.lower().str.strip()
        
        if 'question' not in df.columns or 'answer' not in df.columns:
            logger.warning(f"❌ Excel missing columns: {list(df.columns)}")
            return None

        questions = df["question"].fillna("").astype(str).tolist()
        answers = df["answer"].fillna("").astype(str).tolist()
        
        # Simple keyword matching with synonyms
        best_match = _find_best_match(user_input, questions, answers)
        
        return best_match
        
    except Exception as e:
        logger.error(f"❌ Excel search error: {e}")
        return None

def _search_json_qa(user_input: str, domain: str) -> str:
    """Search in JSON Q&A fallback"""
    try:
        json_path = f"dataset/{domain}/response.json"
        
        if not os.path.exists(json_path):
            logger.debug(f"📄 JSON not found: {json_path}")
            return None

        with open(json_path, 'r', encoding='utf-8') as f:
            qa_data = json.load(f)
        
        if not isinstance(qa_data, list):
            logger.warning("❌ JSON format invalid")
            return None
        
        # Extract questions and answers
        questions = []
        answers = []
        
        for item in qa_data:
            if isinstance(item, dict) and 'question' in item and 'answer' in item:
                questions.append(item['question'])
                answers.append(item['answer'])
                
                # Add keywords as additional questions
                if 'keywords' in item and isinstance(item['keywords'], list):
                    for keyword in item['keywords']:
                        questions.append(keyword)
                        answers.append(item['answer'])
        
        # Simple keyword matching
        best_match = _find_best_match(user_input, questions, answers)
        
        return best_match
        
    except Exception as e:
        logger.error(f"❌ JSON search error: {e}")
        return None

def _find_best_match(user_input: str, questions: list, answers: list) -> str:
    """Find best matching Q&A - FIXED logic"""
    user_lower = user_input.lower().strip()
    user_words = set(user_lower.split())
    
    # Remove stop words
    stop_words = {'là', 'của', 'và', 'có', 'được', 'cho', 'với', 'từ', 'về', 'như', 'khi', 'sẽ', 'đã', 'này', 'đó', 'một', 'các', 'những', 'để', 'trong', 'trên', 'dưới', 'theo', 'gì', 'thì', 'hay', 'hoặc', 'bao', 'nhiều', 'nào', 'ai', 'ở', 'đâu'}
    user_keywords = user_words - stop_words
    
    best_score = 0
    best_answer = None
    
    for i, question in enumerate(questions):
        if i >= len(answers):
            continue
            
        q_lower = question.lower()
        q_words = set(q_lower.split())
        q_keywords = q_words - stop_words
        
        score = 0
        
        # 1. Exact substring match (high priority)
        if user_lower in q_lower:
            score += 3.0
        elif q_lower in user_lower:
            score += 2.5
        
        # 2. Keyword overlap (must have meaningful overlap)
        if user_keywords and q_keywords:
            overlap = len(user_keywords & q_keywords)
            total_user_keywords = len(user_keywords)
            
            # Require significant overlap for shorter queries
            if total_user_keywords <= 3:
                # Short query: need 80% keyword match
                required_overlap = max(2, int(total_user_keywords * 0.8))
            else:
                # Longer query: need 60% keyword match  
                required_overlap = max(2, int(total_user_keywords * 0.6))
            
            if overlap >= required_overlap:
                overlap_ratio = overlap / total_user_keywords
                score += overlap_ratio * 2.0
            else:
                # Penalty for insufficient overlap
                score -= 1.0
        
        # 3. Key entity matching (domain-specific)
        user_entities = _extract_entities(user_lower)
        q_entities = _extract_entities(q_lower)
        
        if user_entities and q_entities:
            entity_overlap = len(user_entities & q_entities)
            if entity_overlap > 0:
                score += entity_overlap * 0.8
            else:
                # Different entities = probably different topic
                score -= 0.5
        
        # 4. Question type matching
        user_type = _classify_question_type(user_lower)
        q_type = _classify_question_type(q_lower)
        
        if user_type == q_type and user_type != 'general':
            score += 0.5
        elif user_type != q_type and user_type != 'general' and q_type != 'general':
            # Different question types = penalty
            score -= 0.8
        
        # 5. Length similarity (avoid matching very different length questions)
        len_diff = abs(len(user_input) - len(question))
        if len_diff > 100:  # Very different lengths
            score -= 0.3
        
        if score > best_score:
            best_score = score
            best_answer = answers[i]
    
    # Higher threshold to ensure quality matches
    if best_answer and best_score >= 2.0:  # Raised threshold
        logger.info(f"📊 Q&A match score: {best_score:.2f}")
        logger.info(f"📝 User: '{user_input[:50]}...'")
        logger.info(f"📝 Matched: '{questions[answers.index(best_answer)][:50]}...'")
        return best_answer
    
    if best_score > 0:
        logger.info(f"❌ Best score {best_score:.2f} below threshold 2.0")
    
    return None

def _extract_entities(text: str) -> set:
    """Extract domain entities from text"""
    entities = set()
    
    entity_patterns = {
        'hộ_chiếu': ['hộ chiếu', 'passport'],
        'thị_thực': ['thị thực', 'visa'],
        'xuất_cảnh': ['xuất cảnh'],
        'nhập_cảnh': ['nhập cảnh'],
        'tạm_trú': ['tạm trú'],
        'thường_trú': ['thường trú'],
        'tạm_hoãn': ['tạm hoãn', 'hoãn'],
        'cấm': ['cấm', 'không được'],
        'mất': ['mất', 'bị mất', 'thất lạc'],
        'hỏng': ['hỏng', 'rách', 'hư'],
        'hết_hạn': ['hết hạn', 'quá hạn'],
        'trẻ_em': ['trẻ em', 'dưới 14 tuổi'],
        'lệ_phí': ['lệ phí', 'phí', 'chi phí'],
        'thời_gian': ['thời gian', 'bao lâu', 'thời hạn'],
        'hồ_sơ': ['hồ sơ', 'giấy tờ', 'tài liệu'],
        'thủ_tục': ['thủ tục', 'quy trình', 'cách làm']
    }
    
    for entity, patterns in entity_patterns.items():
        if any(pattern in text for pattern in patterns):
            entities.add(entity)
    
    return entities

def _classify_question_type(text: str) -> str:
    """Classify question type"""
    if any(word in text for word in ['quy định về', 'quy định', 'định nghĩa', 'là gì', 'nghĩa là']):
        return 'definition'
    elif any(word in text for word in ['thủ tục', 'cách làm', 'làm thế nào', 'hồ sơ', 'các bước']):
        return 'procedure'  
    elif any(word in text for word in ['điều kiện', 'yêu cầu', 'ai được', 'trường hợp nào']):
        return 'requirements'
    elif any(word in text for word in ['phí', 'lệ phí', 'chi phí', 'bao nhiêu tiền']):
        return 'fee'
    elif any(word in text for word in ['thời gian', 'bao lâu', 'mất bao lâu', 'thời hạn']):
        return 'time'
    elif any(word in text for word in ['ở đâu', 'nộp đâu', 'địa chỉ', 'cơ quan']):
        return 'location'
    else:
        return 'general'

# ===== RAG QUERY =====
async def query_rag_engine(user_input: str, domain: str = "xuatnhapcanh") -> dict:
    """Query RAG Engine - Simplified"""
    rag_engine = get_rag_engine()
    
    if not rag_engine or not rag_engine.is_initialized:
        logger.error("❌ RAG Engine not available")
        return {
            'success': False,
            'answer': None,
            'error': 'RAG Engine not available'
        }
    
    try:
        logger.info(f"🤖 Querying RAG Engine...")
        
        result = await rag_engine.query(user_input)
        
        if result['success'] and result.get('answer'):
            metadata = result.get('metadata', {})
            
            return {
                'success': True,
                'answer': result['answer'],
                'sources': result.get('sources', ''),
                'metadata': {
                    'response_time': metadata.get('response_time', 0),
                    'context_sources': metadata.get('context_sources', 0),
                    'context_type': metadata.get('context_type', 'unknown'),
                    'query_intent': metadata.get('query_intent', 'unknown')
                }
            }
        else:
            logger.warning("⚠️ RAG Engine no results")
            return {
                'success': False,
                'answer': None,
                'error': result.get('error', 'No results found')
            }
            
    except Exception as e:
        logger.error(f"❌ RAG query error: {e}")
        return {
            'success': False,
            'answer': None,
            'error': str(e)
        }

def sync_query_rag(user_input: str, domain: str = "xuatnhapcanh") -> dict:
    """Sync wrapper for RAG query"""
    return asyncio.run(query_rag_engine(user_input, domain))

# ===== CONTEXT MANAGEMENT =====
_user_contexts = {}

def get_user_context(user_id: str) -> dict:
    return _user_contexts.get(user_id, {})

def update_user_context(user_id: str, query: str, response: str, source: str):
    if user_id not in _user_contexts:
        _user_contexts[user_id] = {'last_queries': [], 'last_topic': None}
    
    context = _user_contexts[user_id]
    context['last_queries'].append({
        'query': query,
        'response': response[:100],
        'source': source,
        'timestamp': datetime.now().isoformat()
    })
    
    # Keep last 3 queries only
    if len(context['last_queries']) > 3:
        context['last_queries'] = context['last_queries'][-3:]
    
    # Extract topic from query
    if any(word in query.lower() for word in ['hộ chiếu', 'passport']):
        context['last_topic'] = 'hộ chiếu'
    elif any(word in query.lower() for word in ['thị thực', 'visa']):
        context['last_topic'] = 'thị thực'

def enhance_query_with_context(user_id: str, query: str) -> str:
    """Enhance short queries with context"""
    context = get_user_context(user_id)
    
    # Only enhance very short queries
    if len(query.split()) <= 3 and context.get('last_topic'):
        context_words = ['chi phí', 'lệ phí', 'thời gian', 'bao lâu', 'hồ sơ', 'thủ tục', 'ở đâu']
        
        if any(word in query.lower() for word in context_words):
            enhanced = f"{context['last_topic']} {query}"
            logger.info(f"Enhanced: '{query}' → '{enhanced}'")
            return enhanced
    
    return query

# ===== HELPER FUNCTIONS =====
def handle_greeting(user_input: str) -> str:
    """Handle greetings"""
    greeting_words = ["chào", "hi", "hello", "xin chào"]
    msg = user_input.strip().lower()
    
    if any(word in msg for word in greeting_words) and len(msg.split()) <= 3:
        return (
            "Xin chào! Tôi là trợ lý hỗ trợ thông tin xuất nhập cảnh.\n\n"
            "Tôi có thể giúp bạn:\n"
            "• Thủ tục cấp hộ chiếu, visa\n" 
            "• Thông tin pháp lý xuất nhập cảnh\n"
            "• Hướng dẫn làm hồ sơ\n\n"
            "Bạn cần hỗ trợ gì ạ?"
        )
    return None

def handle_sensitive_content(user_input: str) -> str:
    """Block sensitive political content"""
    sensitive_keywords = ["chính trị", "bầu cử", "chính quyền", "lãnh đạo"]
    if any(kw in user_input.lower() for kw in sensitive_keywords):
        return "❌ Tôi chỉ hỗ trợ thông tin về thủ tục hành chính, không trả lời nội dung chính trị."
    return None

# ===== MAIN PROCESSOR =====
def process_user_query(user_input: str, user_id: str, domain: str = None) -> dict:
    """Main query processor - Streamlined"""
    
    user_input = user_input.strip()
    if not user_input:
        return format_response("❓ Vui lòng nhập câu hỏi.", source="system")

    domain = domain or "xuatnhapcanh"
    
    # Enhance query with context
    enhanced_query = enhance_query_with_context(user_id, user_input)
    
    logger.info(f"🔍 Processing: '{enhanced_query[:40]}...'")

    # ===== 1. Check flow state =====
    try:
        from services.flow_engine import flow_engine
        if flow_engine.is_in_flow(user_id):
            return format_response(
                "🤖 Bạn đang trong hướng dẫn. Vui lòng sử dụng các nút hoặc nhắn 'Thoát' để kết thúc.",
                source="flow_redirect"
            )
    except:
        pass

    # ===== 2. Handle greetings =====
    greeting_response = handle_greeting(enhanced_query)
    if greeting_response:
        update_user_context(user_id, user_input, greeting_response, "greeting")
        return format_response(greeting_response, source="greeting")

    # ===== 3. Block sensitive content =====
    sensitive_response = handle_sensitive_content(enhanced_query)
    if sensitive_response:
        return format_response(sensitive_response, source="filter")

    # ===== 4. Smart Q&A Search (Excel + JSON) =====
    qa_result = smart_qa_search(enhanced_query, domain)
    if qa_result:
        logger.info("✅ Found answer in Q&A data")
        update_user_context(user_id, user_input, qa_result, "qa_data")
        return format_response(qa_result, source="qa_data", metadata={"domain": domain})

    # ===== 5. RAG Engine =====
    if RAG_AVAILABLE and get_rag_engine():
        logger.info("🤖 Trying RAG Engine...")
        
        rag_result = sync_query_rag(enhanced_query, domain)
        
        if rag_result['success'] and rag_result['answer']:
            logger.info("✅ RAG Engine found answer")
            
            metadata = {
                "domain": domain,
                "source_type": "rag_engine",
                "response_time": rag_result['metadata'].get('response_time', 0),
                "context_sources": rag_result['metadata'].get('context_sources', 0),
                "context_type": rag_result['metadata'].get('context_type', 'unknown')
            }
            
            update_user_context(user_id, user_input, rag_result['answer'], "rag_engine")
            
            return format_response(
                rag_result['answer'], 
                source="rag_engine",
                metadata=metadata
            )
        else:
            logger.warning(f"⚠️ RAG failed: {rag_result.get('error', 'Unknown')}")
    else:
        logger.warning("⚠️ RAG Engine not available")

    # ===== 6. Fallback =====
    fallback_message = (
        f"Xin lỗi, tôi chưa tìm thấy thông tin về '{user_input}'. "
        "Bạn có thể:\n"
        "• Thử diễn đạt lại câu hỏi\n"
        "• Hỏi về thủ tục cụ thể (ví dụ: 'làm hộ chiếu')\n"
        "• Liên hệ cơ quan có thẩm quyền"
    )
    
    logger.warning(f"❌ No answer found for: {enhanced_query}")
    return format_response(fallback_message, source="fallback", metadata={"domain": domain})

# ===== SYSTEM MANAGEMENT =====
async def initialize_system(force_rebuild=False):
    """Initialize system"""
    logger.info("🔧 Initializing system...")
    
    rag_success = await initialize_rag_engine("xuatnhapcanh")
    
    return {
        'success': True,
        'rag_available': rag_success,
        'message': f"System initialized. RAG: {'✅' if rag_success else '❌'}"
    }

def get_system_status():
    """Get system status"""
    rag_engine = get_rag_engine()
    
    status = {
        'unified_processor': {
            'available': True,
            'data_sources': ['qa_data', 'rag_engine', 'fallback']
        },
        'rag_engine': {
            'available': rag_engine is not None and rag_engine.is_initialized if rag_engine else False,
            'initialized': _rag_initialization_attempted
        }
    }
    
    if rag_engine and rag_engine.is_initialized:
        try:
            stats = rag_engine.get_stats()
            status['rag_engine'].update({
                'stats': stats,
                'documents': stats.get('components', {}).get('vector_store', {}).get('total_documents', 0)
            })
        except Exception as e:
            status['rag_engine']['error'] = str(e)
    
    return status

def health_check() -> dict:
    """System health check"""
    health = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': 'healthy',
        'components': {}
    }
    
    # Check Q&A data
    qa_files = 0
    for domain in ['xuatnhapcanh']:
        excel_exists = os.path.exists(f"dataset/{domain}/question.xlsx")
        json_exists = os.path.exists(f"dataset/{domain}/response.json")
        if excel_exists or json_exists:
            qa_files += 1
    
    health['components']['qa_data'] = {
        'available': qa_files > 0,
        'domains_with_data': qa_files
    }
    
    # Check RAG Engine
    rag_engine = get_rag_engine()
    if rag_engine and rag_engine.is_initialized:
        stats = rag_engine.get_stats()
        health['components']['rag_engine'] = {
            'available': True,
            'documents': stats.get('components', {}).get('vector_store', {}).get('total_documents', 0)
        }
    else:
        health['components']['rag_engine'] = {
            'available': False,
            'reason': 'Not initialized'
        }
        health['overall_status'] = 'degraded'
    
    return health

# ===== EXPORTS =====
__all__ = [
    'process_user_query',
    'initialize_system', 
    'get_system_status',
    'health_check',
    'get_rag_engine',
    'initialize_rag_engine'
]