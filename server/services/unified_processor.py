# services/unified_processor.py - CẬP NHẬT: Tương thích RAG mới

import os
import pandas as pd
import json
import logging
import asyncio
from datetime import datetime
from utils.response_formatter import format_response

# ===== VECTOR RAG INTEGRATION - CẬP NHẬT =====
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
    """CẬP NHẬT: Initialize RAG Engine với logic mới"""
    global _global_rag_engine, _rag_initialization_attempted
    
    if not RAG_AVAILABLE:
        logger.warning("⚠️ RAG Engine not available")
        return False
    
    if _global_rag_engine and _global_rag_engine.is_initialized:
        logger.info("✅ RAG Engine already initialized")
        return True
    
    # if _rag_initialization_attempted:
    #     logger.warning("⚠️ RAG initialization already attempted")
    #     return False
    
    _rag_initialization_attempted = True
    
    try:
        logger.info("🚀 Initializing RAG Engine với logic mới...")
        _global_rag_engine = RAGEngine()
        
        # CẬP NHẬT: Initialize với enhanced features
        result = await asyncio.wait_for(
            _global_rag_engine.initialize(force_rebuild=False),
            timeout=120.0
        )
        
        if result.get('success', False):
            stats = _global_rag_engine.get_stats()
            docs_count = stats.get('components', {}).get('vector_store', {}).get('total_documents', 0)
            logger.info(f"✅ RAG Engine initialized: {docs_count} docs")
            logger.info(f"   Chat history support: ✅")
            logger.info(f"   Entity reranking: ✅")
            logger.info(f"   Context separation: ✅")
            return True
        else:
            logger.error(f"❌ RAG initialization failed: {result.get('message', 'Unknown')}")
            _global_rag_engine = None
            return False
            
    except Exception as e:
        logger.error(f"❌ RAG initialization error: {e}")
        _global_rag_engine = None
        return False

# ===== CẬP NHẬT: ENHANCED JSON SEARCH =====
def smart_qa_search(user_input: str, domain: str = "xuatnhapcanh") -> str:
    """CẬP NHẬT: Smart Q&A search - JSON first với enhanced matching"""
    try:
        logger.info(f"📊 Smart search: '{user_input[:30]}...'")
        
        # Step 1: CẬP NHẬT - Try JSON first (better quality)
        json_result = _search_json_qa_enhanced(user_input, domain)
        if json_result:
            logger.info("✅ Found answer in JSON")
            return json_result
        
        # Step 2: Try Excel fallback
        excel_result = _search_excel_qa(user_input, domain)
        if excel_result:
            logger.info("✅ Found answer in Excel")
            return excel_result
        
        logger.info("❌ No answer in JSON/Excel")
        return None
        
    except Exception as e:
        logger.error(f"❌ Smart search error: {e}")
        return None

def _search_json_qa_enhanced(user_input: str, domain: str) -> str:
    """CẬP NHẬT: Enhanced JSON search với better matching"""
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
        
        # CẬP NHẬT: Enhanced matching với intent và law_ref
        best_match = _find_best_json_match_enhanced(user_input, qa_data)
        
        return best_match
        
    except Exception as e:
        logger.error(f"❌ JSON search error: {e}")
        return None

def _find_best_json_match_enhanced(user_input: str, qa_data: list) -> str:
    """CẬP NHẬT: Enhanced matching cho response.json"""
    user_lower = user_input.lower().strip()
    user_words = set(user_lower.split())
    
    # CẬP NHẬT: Enhanced stop words
    stop_words = {
        'là', 'của', 'và', 'có', 'được', 'cho', 'với', 'từ', 'về', 'như', 'khi', 'sẽ', 'đã', 
        'này', 'đó', 'một', 'các', 'những', 'để', 'trong', 'trên', 'dưới', 'theo', 'gì', 'thì', 
        'hay', 'hoặc', 'bao', 'nhiều', 'nào', 'ai', 'ở', 'đâu', 'mà', 'đang', 'do', 'vì', 'nếu'
    }
    user_keywords = user_words - stop_words
    
    # CẬP NHẬT: Extract user intent
    user_intent = _classify_question_intent(user_lower)
    user_entities = _extract_domain_entities(user_lower)
    
    best_score = 0
    best_answer = None
    best_match_info = None
    
    for item in qa_data:
        if not isinstance(item, dict) or 'question' not in item or 'answer' not in item:
            continue
        
        question = item['question']
        answer = item['answer']
        keywords = item.get('keywords', [])
        intent = item.get('intent', 'general')
        law_ref = item.get('law_ref', '')
        
        # CẬP NHẬT: Multi-level scoring
        score = 0
        match_details = []
        
        # 1. EXACT MATCH (highest priority)
        q_lower = question.lower()
        if user_lower == q_lower:
            score += 10.0
            match_details.append("exact_question")
        elif user_lower in q_lower:
            score += 8.0
            match_details.append("substring_in_question")
        elif q_lower in user_lower:
            score += 6.0
            match_details.append("question_in_user")
        
        # 2. KEYWORD MATCHING với keywords list
        if keywords and isinstance(keywords, list):
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if user_lower == keyword_lower:
                    score += 9.0
                    match_details.append("exact_keyword")
                    break
                elif user_lower in keyword_lower or keyword_lower in user_lower:
                    score += 7.0
                    match_details.append("substring_keyword")
                    break
        
        # 3. QUESTION CONTENT MATCHING
        q_words = set(q_lower.split())
        q_keywords = q_words - stop_words
        
        if user_keywords and q_keywords:
            overlap = len(user_keywords & q_keywords)
            total_user = len(user_keywords)
            
            if total_user <= 2:
                # Very short query - need exact match
                if overlap >= total_user:
                    score += 5.0
                    match_details.append("full_keyword_overlap")
                elif overlap >= 1:
                    score += 2.0
                    match_details.append("partial_keyword_overlap")
            elif total_user <= 4:
                # Short query - need high overlap
                if overlap >= int(total_user * 0.8):
                    score += 4.0
                    match_details.append("high_keyword_overlap")
                elif overlap >= int(total_user * 0.6):
                    score += 2.5
                    match_details.append("medium_keyword_overlap")
            else:
                # Longer query - more flexible
                if overlap >= int(total_user * 0.6):
                    score += 3.0
                    match_details.append("good_keyword_overlap")
                elif overlap >= int(total_user * 0.4):
                    score += 1.5
                    match_details.append("fair_keyword_overlap")
        
        # 4. CẬP NHẬT: INTENT MATCHING
        if user_intent == intent and intent != 'general':
            score += 2.0
            match_details.append("intent_match")
        elif user_intent != intent and user_intent != 'general' and intent != 'general':
            score -= 2.5  # Different intents = penalty
            match_details.append("intent_mismatch")
        
        # 5. CẬP NHẬT: ENTITY MATCHING
        q_entities = _extract_domain_entities(q_lower)
        if user_entities and q_entities:
            entity_overlap = len(user_entities & q_entities)
            if entity_overlap > 0:
                score += entity_overlap * 1.5
                match_details.append(f"entity_overlap_{entity_overlap}")
            else:
                # Different main entities = big penalty
                if len(user_entities) > 0 and len(q_entities) > 0:
                    score -= 3.0
                    match_details.append("entity_mismatch")
        
        # 6. CẬP NHẬT: LEGAL REFERENCE BONUS
        if law_ref and any(word in user_lower for word in ['điều', 'luật', 'quy định']):
            score += 1.0
            match_details.append("legal_reference")
        
        # 7. CẬP NHẬT: LENGTH SIMILARITY
        len_diff = abs(len(user_input) - len(question))
        if len_diff > 150:  # Very different lengths
            score -= 1.0
            match_details.append("length_mismatch")
        elif len_diff < 30:  # Similar lengths
            score += 0.5
            match_details.append("length_similar")
        
        # CẬP NHẬT: Track best match
        if score > best_score:
            best_score = score
            best_answer = answer
            best_match_info = {
                'question': question,
                'score': score,
                'match_details': match_details,
                'intent': intent,
                'law_ref': law_ref
            }
    
    # CẬP NHẬT: Higher threshold cho quality
    if best_answer and best_score >= 4.0:  # Raised threshold
        logger.info(f"📊 JSON match score: {best_score:.2f}")
        logger.info(f"📝 User: '{user_input[:50]}...'")
        logger.info(f"📝 Matched: '{best_match_info['question'][:50]}...'")
        logger.info(f"📋 Details: {best_match_info['match_details']}")
        logger.info(f"🎯 Intent: {best_match_info['intent']}")
        
        # CẬP NHẬT: Enhanced answer với law reference
        final_answer = best_answer
        if best_match_info.get('law_ref'):
            final_answer += f"\n\n📚 Căn cứ pháp lý: {best_match_info['law_ref']}"
        
        return final_answer
    
    if best_score > 0:
        logger.info(f"❌ Best JSON score {best_score:.2f} below threshold 3.0")
        if best_match_info:
            logger.info(f"   Best match: '{best_match_info['question'][:50]}...'")
            logger.info(f"   Details: {best_match_info['match_details']}")
    
    return None

def _classify_question_intent(text: str) -> str:
    """CẬP NHẬT: Enhanced intent classification"""
    # Legal/definition intent
    if any(word in text for word in ['quy định về', 'quy định', 'định nghĩa', 'là gì', 'nghĩa là', 'điều', 'luật', 'khoản']):
        return 'luật'
    
    # Procedure intent  
    elif any(word in text for word in ['thủ tục', 'cách làm', 'làm thế nào', 'hồ sơ', 'các bước', 'quy trình', 'trình tự']):
        return 'thủ tục'
    
    # Requirements
    elif any(word in text for word in ['điều kiện', 'yêu cầu', 'ai được', 'trường hợp nào', 'đối tượng']):
        return 'thủ tục'
    
    # Fee questions
    elif any(word in text for word in ['phí', 'lệ phí', 'chi phí', 'bao nhiêu tiền', 'mức phí']):
        return 'thủ tục'
    
    # Time questions
    elif any(word in text for word in ['thời gian', 'bao lâu', 'mất bao lâu', 'thời hạn']):
        return 'thủ tục'
    
    # Location questions
    elif any(word in text for word in ['ở đâu', 'nộp đâu', 'địa chỉ', 'cơ quan', 'nơi nào']):
        return 'thủ tục'
    
    else:
        return 'general'

def _extract_domain_entities(text: str) -> set:
    """CẬP NHẬT: Enhanced entity extraction"""
    entities = set()
    
    # Main document types
    if any(word in text for word in ['hộ chiếu', 'passport']):
        entities.add('hộ_chiếu')
    if any(word in text for word in ['thị thực', 'visa']):
        entities.add('thị_thực')
    if any(word in text for word in ['tạm trú', 'tam tru']):
        entities.add('tạm_trú')
    if any(word in text for word in ['thường trú', 'thuong tru']):
        entities.add('thường_trú')
    
    # Actions
    if any(word in text for word in ['xuất cảnh', 'xuat canh']):
        entities.add('xuất_cảnh')
    if any(word in text for word in ['nhập cảnh', 'nhap canh']):
        entities.add('nhập_cảnh')
    if any(word in text for word in ['mất', 'bị mất', 'thất lạc']):
        entities.add('mất')
    if any(word in text for word in ['hỏng', 'rách', 'hư']):
        entities.add('hỏng')
    
    # Special cases
    if any(word in text for word in ['trẻ em', 'dưới 14 tuổi', 'tre em']):
        entities.add('trẻ_em')
    if any(word in text for word in ['tạm hoãn', 'hoãn', 'tam hoan']):
        entities.add('tạm_hoãn')
    
    # Procedure elements
    if any(word in text for word in ['lệ phí', 'phí', 'chi phí', 'le phi']):
        entities.add('lệ_phí')
    if any(word in text for word in ['hồ sơ', 'giấy tờ', 'tài liệu', 'ho so']):
        entities.add('hồ_sơ')
    if any(word in text for word in ['thời gian', 'bao lâu', 'thời hạn', 'thoi gian']):
        entities.add('thời_gian')
    
    return entities

def _search_excel_qa(user_input: str, domain: str) -> str:
    """Excel search (unchanged)"""
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
        
        # Simple keyword matching
        best_match = _find_best_match_simple(user_input, questions, answers)
        
        return best_match
        
    except Exception as e:
        logger.error(f"❌ Excel search error: {e}")
        return None

def _find_best_match_simple(user_input: str, questions: list, answers: list) -> str:
    """Simple matching cho Excel fallback"""
    user_lower = user_input.lower().strip()
    user_words = set(user_lower.split())
    
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
        
        # Exact match
        if user_lower == q_lower:
            score += 5.0
        elif user_lower in q_lower:
            score += 3.0
        elif q_lower in user_lower:
            score += 2.5
        
        # Keyword overlap
        if user_keywords and q_keywords:
            overlap = len(user_keywords & q_keywords)
            if overlap >= len(user_keywords) * 0.7:
                score += 2.0
        
        if score > best_score:
            best_score = score
            best_answer = answers[i]
    
    if best_answer and best_score >= 2.0:
        logger.info(f"📊 Excel match score: {best_score:.2f}")
        return best_answer
    
    return None

# ===== CẬP NHẬT: RAG QUERY với session =====
async def query_rag_engine(user_input: str, user_id: str = None, domain: str = "xuatnhapcanh") -> dict:
    """CẬP NHẬT: Query RAG Engine với session support"""
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
        
        # CẬP NHẬT: Pass session_id for chat history
        result = await rag_engine.query(user_input, session_id=user_id)
        
        if result['success'] and result.get('answer'):
            metadata = result.get('metadata', {})
            
            # CẬP NHẬT: Enhanced metadata
            return {
                'success': True,
                'answer': result['answer'],
                'sources': result.get('sources', ''),
                'metadata': {
                    'response_time': metadata.get('response_time', 0),
                    'context_sources': metadata.get('context_sources', 0),
                    'context_type': metadata.get('context_type', 'unknown'),
                    'query_intent': metadata.get('query_intent', 'unknown'),
                    'query_normalized': metadata.get('query_normalized', False),
                    'original_query': metadata.get('original_query', user_input),
                    'normalized_query': metadata.get('normalized_query', user_input)
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

def sync_query_rag(user_input: str, user_id: str = None, domain: str = "xuatnhapcanh") -> dict:
    """CẬP NHẬT: Sync wrapper với user_id"""
    return asyncio.run(query_rag_engine(user_input, user_id, domain))

# ===== CONTEXT MANAGEMENT (unchanged) =====
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
    """CẬP NHẬT: Enhanced context aware query enhancement"""
    context = get_user_context(user_id)
    
    # Only enhance very short and incomplete queries
    if len(query.split()) <= 3 and context.get('last_topic'):
        context_words = ['chi phí', 'lệ phí', 'thời gian', 'bao lâu', 'hồ sơ', 'thủ tục', 'ở đâu', 'cần gì', 'như thế nào']
        
        if any(word in query.lower() for word in context_words):
            enhanced = f"{context['last_topic']} {query}"
            logger.info(f"Enhanced: '{query}' → '{enhanced}'")
            return enhanced
    
    return query

# ===== HELPER FUNCTIONS (unchanged) =====
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

# ===== CẬP NHẬT: MAIN PROCESSOR =====
def process_user_query(user_input: str, user_id: str, domain: str = None) -> dict:
    """CẬP NHẬT: Main query processor với enhanced logic"""
    
    user_input = user_input.strip()
    if not user_input:
        return format_response("❓ Vui lòng nhập câu hỏi.", source="system")

    domain = domain or "xuatnhapcanh"
    
    # CẬP NHẬT: Context enhancement (less aggressive)
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

    # ===== 4. CẬP NHẬT: Smart Q&A Search (JSON first) =====
    qa_result = smart_qa_search(enhanced_query, domain)
    if qa_result:
        logger.info("✅ Found answer in Q&A data")
        update_user_context(user_id, user_input, qa_result, "qa_data")
        return format_response(qa_result, source="qa_data", metadata={"domain": domain})

    # ===== 5. CẬP NHẬT: RAG Engine với session =====
    if RAG_AVAILABLE and get_rag_engine():
        logger.info("🤖 Trying RAG Engine...")
        
        # CẬP NHẬT: Pass user_id for session support
        rag_result = sync_query_rag(enhanced_query, user_id, domain)
        
        if rag_result['success'] and rag_result['answer']:
            logger.info("✅ RAG Engine found answer")
            
            # CẬP NHẬT: Enhanced metadata
            metadata = {
                "domain": domain,
                "source_type": "rag_engine",
                "response_time": rag_result['metadata'].get('response_time', 0),
                "context_sources": rag_result['metadata'].get('context_sources', 0),
                "context_type": rag_result['metadata'].get('context_type', 'unknown'),
                "query_intent": rag_result['metadata'].get('query_intent', 'unknown'),
                "query_normalized": rag_result['metadata'].get('query_normalized', False)
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
    """CẬP NHẬT: Initialize system với enhanced features"""
    logger.info("🔧 Initializing system với RAG mới...")
    
    rag_success = await initialize_rag_engine("xuatnhapcanh")
    
    if rag_success:
        # CẬP NHẬT: Log enhanced features
        rag_engine = get_rag_engine()
        if rag_engine:
            stats = rag_engine.get_stats()
            logger.info("✅ Enhanced RAG features available:")
            logger.info("   📝 Query normalization")
            logger.info("   🔄 Chat history support")
            logger.info("   🎯 Entity reranking")
            logger.info("   📊 Context separation")
            logger.info("   🧠 Smart prompt selection")
    
    return {
        'success': True,
        'rag_available': rag_success,
        'enhanced_features': rag_success,
        'message': f"System initialized. RAG: {'✅' if rag_success else '❌'}"
    }

def get_system_status():
    """CẬP NHẬT: Enhanced system status"""
    rag_engine = get_rag_engine()
    
    status = {
        'unified_processor': {
            'available': True,
            'data_sources': ['enhanced_json', 'excel_fallback', 'rag_engine', 'fallback'],
            'features': ['context_enhancement', 'intent_classification', 'entity_extraction']
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
                'documents': stats.get('components', {}).get('vector_store', {}).get('total_documents', 0),
                'chat_history_length': stats.get('chat_history_length', 0),
                'enhanced_features': [
                    'query_normalization',
                    'entity_reranking', 
                    'context_separation',
                    'smart_prompts',
                    'legal_chunking'
                ]
            })
        except Exception as e:
            status['rag_engine']['error'] = str(e)
    
    return status

def health_check() -> dict:
    """CẬP NHẬT: Enhanced health check"""
    health = {
        'timestamp': datetime.now().isoformat(),
        'overall_status': 'healthy',
        'components': {}
    }
    
    # Check Q&A data - CẬP NHẬT: Prioritize JSON
    qa_status = {'json_available': False, 'excel_available': False}
    
    for domain in ['xuatnhapcanh']:
        json_exists = os.path.exists(f"dataset/{domain}/response.json")
        excel_exists = os.path.exists(f"dataset/{domain}/question.xlsx")
        
        if json_exists:
            qa_status['json_available'] = True
            # CẬP NHẬT: Validate JSON structure
            try:
                with open(f"dataset/{domain}/response.json", 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    qa_status['json_entries'] = len(data) if isinstance(data, list) else 0
            except:
                qa_status['json_entries'] = 0
        
        if excel_exists:
            qa_status['excel_available'] = True
    
    health['components']['qa_data'] = {
        'available': qa_status['json_available'] or qa_status['excel_available'],
        'preferred_source': 'JSON' if qa_status['json_available'] else 'Excel',
        'json_entries': qa_status.get('json_entries', 0),
        **qa_status
    }
    
    # Check RAG Engine - CẬP NHẬT: Enhanced check
    rag_engine = get_rag_engine()
    if rag_engine and rag_engine.is_initialized:
        try:
            stats = rag_engine.get_stats()
            health['components']['rag_engine'] = {
                'available': True,
                'documents': stats.get('components', {}).get('vector_store', {}).get('total_documents', 0),
                'embedding_model': stats.get('components', {}).get('vector_store', {}).get('embedding_model', 'unknown'),
                'chat_history_support': True,
                'enhanced_features': True
            }
        except Exception as e:
            health['components']['rag_engine'] = {
                'available': False,
                'error': str(e)
            }
            health['overall_status'] = 'degraded'
    else:
        health['components']['rag_engine'] = {
            'available': False,
            'reason': 'Not initialized'
        }
        health['overall_status'] = 'degraded'
    
    # CẬP NHẬT: Overall assessment
    if health['components']['qa_data']['available'] and health['components']['rag_engine']['available']:
        health['overall_status'] = 'healthy'
        health['capabilities'] = [
            'enhanced_json_search',
            'rag_engine_with_normalization',
            'entity_reranking',
            'context_separation',
            'chat_history_support'
        ]
    elif health['components']['qa_data']['available']:
        health['overall_status'] = 'functional'
        health['capabilities'] = ['enhanced_json_search', 'excel_fallback']
    else:
        health['overall_status'] = 'limited'
        health['capabilities'] = ['basic_fallback']
    
    return health

# ===== CẬP NHẬT: TESTING UTILITIES =====
def test_json_search(test_queries: list = None) -> dict:
    """Test JSON search functionality"""
    if test_queries is None:
        test_queries = [
            "Thành phần hồ sơ yêu cầu cấp hộ chiếu phổ thông là gì?",
            "Lệ phí cấp hộ chiếu phổ thông là bao nhiêu?",  
            "Làm hộ chiếu ở đâu?",
            "Thời gian cấp hộ chiếu là bao lâu?",
            "Xuất cảnh là gì?"
        ]
    
    results = {}
    
    for query in test_queries:
        result = _search_json_qa_enhanced(query, "xuatnhapcanh")
        results[query] = {
            'found': result is not None,
            'answer_length': len(result) if result else 0,
            'answer_preview': result[:100] + "..." if result and len(result) > 100 else result
        }
    
    return {
        'total_queries': len(test_queries),
        'successful_matches': sum(1 for r in results.values() if r['found']),
        'success_rate': sum(1 for r in results.values() if r['found']) / len(test_queries),
        'results': results
    }

def debug_query_processing(query: str, user_id: str = "test_user") -> dict:
    """Debug query processing pipeline"""
    debug_info = {
        'original_query': query,
        'steps': [],
        'final_result': None
    }
    
    # Step 1: Context enhancement
    enhanced = enhance_query_with_context(user_id, query)
    debug_info['steps'].append({
        'step': 'context_enhancement',
        'input': query,
        'output': enhanced,
        'changed': enhanced != query
    })
    
    # Step 2: Intent classification
    intent = _classify_question_intent(enhanced.lower())
    debug_info['steps'].append({
        'step': 'intent_classification',
        'result': intent
    })
    
    # Step 3: Entity extraction
    entities = _extract_domain_entities(enhanced.lower())
    debug_info['steps'].append({
        'step': 'entity_extraction',
        'entities': list(entities)
    })
    
    # Step 4: JSON search
    json_result = _search_json_qa_enhanced(enhanced, "xuatnhapcanh")
    debug_info['steps'].append({
        'step': 'json_search',
        'found': json_result is not None,
        'result_preview': json_result[:100] if json_result else None
    })
    
    # Step 5: Process through main pipeline
    try:
        final_result = process_user_query(query, user_id)
        debug_info['final_result'] = {
            'source': final_result.get('source'),
            'success': 'answer' in final_result,
            'answer_preview': final_result.get('answer', '')[:100] if final_result.get('answer') else None
        }
    except Exception as e:
        debug_info['final_result'] = {'error': str(e)}
    
    return debug_info

# ===== EXPORTS =====
__all__ = [
    'process_user_query',
    'initialize_system', 
    'get_system_status',
    'health_check',
    'get_rag_engine',
    'initialize_rag_engine',
    'test_json_search',
    'debug_query_processing'
]