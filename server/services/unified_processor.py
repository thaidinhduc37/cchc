# services/unified_processor.py - SỬA LẠI HOÀN CHỈNH
"""
🎯 UNIFIED PROCESSOR - SỬA LẠI LOGIC
📋 Flow: Phân tích ý định → Tìm JSON → Match chính xác → RAG fallback
🔧 Giữ nguyên structure, sửa logic cho đúng
"""
import os
import json
import logging
import asyncio
import re
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
    """Initialize RAG Engine"""
    global _global_rag_engine, _rag_initialization_attempted
    
    if not RAG_AVAILABLE:
        logger.warning("⚠️ RAG Engine not available")
        return False
    
    if _global_rag_engine and _global_rag_engine.is_initialized:
        logger.info("✅ RAG Engine already initialized")
        return True
    
    _rag_initialization_attempted = True
    
    try:
        logger.info("🚀 Initializing RAG Engine...")
        _global_rag_engine = RAGEngine()
        
        result = await asyncio.wait_for(
            _global_rag_engine.initialize(force_rebuild=False),
            timeout=120.0
        )

        if result.get('success', False):
            stats = _global_rag_engine.get_stats()
            docs_count = stats.get('system_info', {}).get('total_documents', 0)
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

# ===== 1. CONTEXT MANAGER =====
class ContextManager:
    """Manage conversation context for all users"""
    
    def __init__(self):
        self.contexts = {}
    
    def get(self, user_id: str) -> dict:
        """Get user context"""
        if user_id not in self.contexts:
            self.contexts[user_id] = {
                'recent_queries': [],
                'current_topic': None,
                'topic_confidence': 0.0
            }
        return self.contexts[user_id]
    
    def update(self, user_id: str, query: str, response: str, source: str):
        """Update context after processing"""
        context = self.get(user_id)
        
        # Simple topic detection
        detected_topic = self._detect_topic(query, response)
        
        # Add to recent queries
        context['recent_queries'].append({
            'query': query,
            'response': response[:100],
            'source': source,
            'topic': detected_topic,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only last 4 queries
        if len(context['recent_queries']) > 4:
            context['recent_queries'].pop(0)
        
        # Update current topic
        if detected_topic:
            if detected_topic == context['current_topic']:
                context['topic_confidence'] = min(context['topic_confidence'] + 0.3, 1.0)
            else:
                context['current_topic'] = detected_topic
                context['topic_confidence'] = 0.8
        else:
            context['topic_confidence'] *= 0.7
            if context['topic_confidence'] < 0.3:
                context['current_topic'] = None
                context['topic_confidence'] = 0.0
    
    def _detect_topic(self, query: str, response: str) -> str:
        """Simple topic detection from query/response"""
        text = f"{query} {response}".lower()
        
        if any(word in text for word in ['hộ chiếu', 'passport']):
            return 'hộ chiếu'
        elif any(word in text for word in ['visa', 'thị thực']):
            return 'visa'
        elif any(word in text for word in ['xuất cảnh', 'đi nước ngoài']):
            return 'xuất cảnh'
        elif any(word in text for word in ['nhập cảnh']):
            return 'nhập cảnh'
        
        return None
    
    def resolve_vague_query(self, query: str, user_id: str) -> dict:
        """Resolve vague queries using context"""
        context = self.get(user_id)
        
        # Check if query is vague
        vague_patterns = [
            r'^(?:lệ\s+phí|chi\s+phí|phí).*(?:ra\s+sao|bao\s+nhiêu|là\s+gì)$',
            r'^(?:thời\s+gian|bao\s+lâu).*(?:ra\s+sao)$',
            r'^(?:ở\s+đâu|tại\s+đâu).*(?:làm|nộp)$',
            r'^(?:cần|phải)\s+(?:gì|những\s+gì)$',
            r'^(?:có|được)\s+(?:không|hay\s+không)$',
        ]
        
        is_vague = any(re.search(pattern, query.lower()) for pattern in vague_patterns)
        
        resolution = {
            'original_query': query,
            'resolved_query': query,
            'is_vague': is_vague,
            'context_used': False,
            'current_topic': context['current_topic'],
            'topic_confidence': context['topic_confidence']
        }
        
        # Apply context resolution if vague and have topic
        if is_vague and context['current_topic'] and context['topic_confidence'] > 0.5:
            resolved_query = f"{context['current_topic']} {query}"
            resolution.update({
                'resolved_query': resolved_query,
                'context_used': True
            })
            logger.info(f"🔗 Context resolution: '{query}' → '{resolved_query}' (topic: {context['current_topic']})")
        
        return resolution

# ===== 2. INTENT ANALYZER - SỬA LẠI =====
class IntentAnalyzer:
    """SỬA LẠI: Phân tích ý định người dùng đúng đắn"""
    
    def __init__(self):
        # Simple patterns - không hardcode quá nhiều
        pass
    
    def analyze_intent(self, resolved_query: str, context_info: dict) -> dict:
        """SỬA LẠI: Phân tích ý định đơn giản và chính xác"""
        query_lower = resolved_query.lower().strip()
        
        # 1. Phát hiện loại câu hỏi cơ bản
        intent_type = self._detect_intent_type(query_lower)
        
        # 2. Phát hiện yêu cầu đặc biệt
        needs_conclusion = self._needs_conclusion(query_lower)
        is_procedure = self._is_procedure(query_lower)
        
        # 3. Tính confidence
        confidence = self._calculate_confidence(intent_type, query_lower)
        
        # 4. Luôn route JSON trước
        route_to = 'JSON'
        
        return {
            'resolved_query': resolved_query,
            'intent_type': intent_type,
            'needs_conclusion': needs_conclusion,
            'is_procedure': is_procedure,
            'route_to': route_to,
            'confidence': confidence,
            'context_info': context_info,
            'intent_summary': {
                'type': intent_type,
                'has_constraints': self._has_constraints(query_lower),
                'confidence_level': 'high' if confidence > 0.8 else 'medium' if confidence > 0.6 else 'low'
            }
        }
    
    def _detect_intent_type(self, query: str) -> str:
        """Phát hiện loại ý định cơ bản"""
        # Direct article
        if re.search(r'(?:điều|khoản)\s+\d+', query):
            return 'direct_article'
        
        # Procedure
        if any(word in query for word in ['thủ tục', 'làm', 'cần', 'như thế nào']):
            return 'procedure'
        
        # Legal question
        if any(phrase in query for phrase in ['có được', 'được không', 'có thể']):
            return 'legal'
        
        return 'general'
    
    def _needs_conclusion(self, query: str) -> bool:
        """Cần kết luận ĐƯỢC/KHÔNG"""
        return any(phrase in query for phrase in ['có được', 'được không', 'có thể không'])
    
    def _is_procedure(self, query: str) -> bool:
        """Là câu hỏi thủ tục"""
        return any(word in query for word in ['thủ tục', 'làm', 'cần gì', 'như thế nào'])
    
    def _has_constraints(self, query: str) -> bool:
        """Có ràng buộc đặc biệt"""
        return any(word in query for word in ['bị', 'không', 'hết hạn', 'trẻ em'])
    
    def _calculate_confidence(self, intent_type: str, query: str) -> float:
        """Tính độ tin cậy"""
        if intent_type == 'direct_article':
            return 0.9
        elif intent_type in ['procedure', 'legal']:
            return 0.8
        else:
            return 0.6

# ===== 3. SITUATION MATCHER - SỬA LẠI =====
class SituationMatcher:
    """SAFE JSON matching với RAG fallback khi query phức tạp"""
    
    def __init__(self):
        self.json_cache = {}
    
    def match(self, resolved_query: str, intent_analysis: dict, domain: str = "xuatnhapcanh") -> str:
        """SAFE matching với RAG fallback"""
        try:
            json_path = f"dataset/{domain}/response.json"
            
            if not os.path.exists(json_path):
                logger.debug(f"📄 JSON not found: {json_path}")
                return None

            # Load JSON data
            if json_path not in self.json_cache:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.json_cache[json_path] = json.load(f)
            
            data = self.json_cache[json_path]
            query_lower = resolved_query.lower().strip()
            all_matches = []
            
            # 1. Try procedures với SAFE matching
            if 'procedures' in data:
                match = self._safe_match_procedures(query_lower, data['procedures'], intent_analysis)
                if match:
                    all_matches.append({
                        'content': match,
                        'score': 10,
                        'type': 'safe_procedure'
                    })
            
            # 2. Try legal situations với STRICT matching
            if 'legal_situations' in data:
                match = self._safe_match_legal(query_lower, data['legal_situations'], intent_analysis)
                if match:
                    all_matches.append({
                        'content': match,
                        'score': 12,
                        'type': 'safe_legal'
                    })
            
            # 3. Try combined situations
            if 'combined_situations' in data:
                match = self._safe_match_combined(query_lower, data['combined_situations'], intent_analysis)
                if match:
                    all_matches.append({
                        'content': match,
                        'score': 8,
                        'type': 'safe_combined'
                    })
            
            # Return best match nếu có
            if all_matches:
                best_match = max(all_matches, key=lambda x: x['score'])
                logger.info(f"✅ Safe JSON match: {best_match['type']} (score: {best_match['score']})")
                return best_match['content']
            
            # 4. No safe match found → RAG
            logger.info(f"❌ No safe JSON match → routing to RAG: {resolved_query}")
            return None
            
        except Exception as e:
            logger.error(f"❌ JSON matching error: {e}")
            return None
    
    def _safe_match_procedures(self, query: str, procedures: list, intent_analysis: dict) -> str:
        """SAFE procedure matching with question patterns priority"""
        best_match = None
        best_score = 0
        exact_pattern_match = False
        
        for procedure in procedures:
            # 1. PRIORITY: Check question patterns first (EXACT match)
            question_patterns = procedure.get('question_patterns', [])
            for pattern in question_patterns:
                if pattern.lower() in query.lower():
                    logger.info(f"🎯 EXACT pattern match: '{pattern}' → JSON (ignoring complexity)")
                    return procedure['base_response']['content']
            
            # 2. Base keywords matching
            base_keywords = procedure.get('base_keywords', [])
            base_score = self._calculate_match_score(query, base_keywords)
            
            if base_score > 0:
                # Check situations
                if 'situations' in procedure:
                    for situation in procedure['situations']:
                        sit_keywords = situation.get('keywords', [])
                        sit_score = self._calculate_match_score(query, sit_keywords)
                        
                        total_score = base_score + sit_score
                        
                        if total_score > best_score and total_score >= 8:  # High threshold
                            # Only check complexity for keyword-based matching
                            if not self._is_query_too_complex(query, base_keywords + sit_keywords):
                                best_match = situation['response']['content']
                                best_score = total_score
                
                # Base procedure (keyword-based)
                if base_score > best_score and base_score >= 6:  # High threshold
                    # Only check complexity for keyword-based matching
                    if not self._is_query_too_complex(query, base_keywords):
                        best_match = procedure['base_response']['content']
                        best_score = base_score
        
        if best_match and best_score >= 6:  # Final safety check
            logger.info(f"✅ Safe procedure match (score: {best_score})")
            return best_match
        
        return None
    
    def _safe_match_legal(self, query: str, legal_situations: list, intent_analysis: dict) -> str:
        """ULTRA STRICT legal matching"""
        for legal_case in legal_situations:
            core_keywords = legal_case.get('core_keywords', [])
            context_keywords = legal_case.get('context_keywords', [])
            
            # MUST have both core AND context AND question pattern
            has_core = any(kw in query for kw in core_keywords)
            has_context = any(kw in query for kw in context_keywords)
            has_question = any(pattern in query for pattern in ['được không', 'có được', 'có thể'])
            
            if has_core and has_context and has_question:
                # Extra safety: check not too complex
                all_keywords = core_keywords + context_keywords
                if not self._is_query_too_complex(query, all_keywords):
                    logger.info(f"✅ Safe legal match: {legal_case.get('situation_id')}")
                    return legal_case['response']['content']
        
        return None
    
    def _safe_match_combined(self, query: str, combined_situations: list, intent_analysis: dict) -> str:
        """Safe combined situations matching"""
        best_match = None
        best_score = 0
        
        for combo in combined_situations:
            keywords = combo.get('keywords', [])
            score = self._calculate_match_score(query, keywords)
            
            if score > 0 and not self._is_query_too_complex(query, keywords):
                if score > best_score and score >= 6:  # High threshold
                    best_match = combo['response']['content']
                    best_score = score
        
        if best_match:
            logger.info(f"✅ Safe combined match (score: {best_score})")
            return best_match
        
        return None
    
    def _calculate_match_score(self, query: str, keywords: list) -> int:
        """CONSERVATIVE matching - chỉ match khi rất chắc"""
        if not keywords:
            return 0
        
        query_lower = query.lower().strip()
        exact_matches = 0
        
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            
            # CHỈ EXACT substring match - không fuzzy
            if keyword_lower in query_lower:
                exact_matches += 1
        
        # YÊU CẦU match ít nhất 70% keywords
        match_ratio = exact_matches / len(keywords)
        if match_ratio >= 0.7:  # Strict threshold
            return exact_matches * 2
        
        return 0
    
    def _is_query_too_complex(self, query: str, matched_keywords: list) -> bool:
        """Check nếu query quá phức tạp → route RAG"""
        query_words = query.lower().split()
        
        # 1. Nếu query dài quá
        if len(query_words) > 15:  # Quá dài
            return True
        
        # 2. Nếu có quá nhiều từ thừa
        matched_word_count = sum(len(kw.split()) for kw in matched_keywords)
        extra_words = len(query_words) - matched_word_count
        
        if extra_words > 8:  # Quá nhiều từ thừa
            return True
        
        # 3. Detect complex grammar patterns
        complex_patterns = [
            "nhưng", "tuy nhiên", "mặc dù", "bởi vì", 
            "trước khi", "sau khi", "trong khi", "để mà",
            "trong trường hợp", "nếu như", "giả sử",
            "một mặt", "mặt khác", "không những"
        ]
        
        if any(pattern in query.lower() for pattern in complex_patterns):
            return True
        
        # 4. Multiple questions in one query
        question_markers = query.lower().count('?') + query.lower().count('không') + query.lower().count('được')
        if question_markers > 3:  # Too many question elements
            return True
        
        return False
    
    def _has_sufficient_context(self, query: str, core_keywords: list, context_keywords: list) -> bool:
        """Check if query has sufficient context for legal matching"""
        query_lower = query.lower()
        
        # Must have at least 1 core + 1 context
        has_core = any(kw in query_lower for kw in core_keywords)
        has_context = any(kw in query_lower for kw in context_keywords)
        
        return has_core and has_context
    
    def get_matching_stats(self) -> dict:
        """Get matching statistics for debugging"""
        return {
            'cached_files': len(self.json_cache),
            'matching_approach': 'conservative_safe_matching',
            'thresholds': {
                'procedure_base': 6,
                'procedure_situation': 8,
                'legal_strict': 'core+context+question',
                'combined': 6,
                'complexity_max_words': 15,
                'complexity_max_extra': 8
            },
            'safety_features': [
                'complexity_detection',
                'exact_match_only',
                'high_thresholds',
                'rag_fallback'
            ]
        }
# ===== 4. RAG COORDINATOR =====
class RAGCoordinator:
    """Coordinate with RAG engine"""
    
    async def query(self, rag_data: dict) -> dict:
        """Query RAG engine"""
        rag_engine = get_rag_engine()
        
        if not rag_engine:
            logger.error("❌ RAG Engine not available")
            return {'success': False, 'answer': self._create_fallback_response(rag_data)}
        
        try:
            if not hasattr(rag_engine, 'is_initialized') or not rag_engine.is_initialized:
                logger.error("❌ RAG Engine not initialized")
                return {'success': False, 'answer': self._create_fallback_response(rag_data)}
        except:
            logger.error("❌ RAG Engine status unknown")
            return {'success': False, 'answer': self._create_fallback_response(rag_data)}
        
        try:
            logger.info(f"🤖 Querying RAG engine...")
            
            result = await rag_engine.query(
                rag_data['resolved_query'], 
                session_id=rag_data.get('user_id'),
                unified_data=rag_data.get('intent_analysis', {})
            )
            
            if result.get('success') and result.get('answer'):
                return {
                    'success': True,
                    'answer': result['answer'],
                    'metadata': result.get('pipeline_info', {})
                }
            else:
                logger.warning("⚠️ RAG Engine no results")
                return {'success': False, 'answer': self._create_fallback_response(rag_data)}
                
        except Exception as e:
            logger.error(f"❌ RAG query error: {e}")
            return {'success': False, 'answer': self._create_fallback_response(rag_data)}
    
    def _create_fallback_response(self, rag_data: dict) -> str:
        """Create fallback response when RAG fails"""
        query = rag_data.get('original_query', 'câu hỏi của bạn')
        
        return (
            f"Xin lỗi, tôi chưa tìm thấy thông tin về '{query}'. "
            "Bạn có thể:\n"
            "• Thử diễn đạt lại câu hỏi\n"
            "• Hỏi về thủ tục cụ thể\n"
            "• Liên hệ cơ quan có thẩm quyền: 069.1000.000\n\n"
            "Website: https://dichvucong.bocongan.gov.vn"
        )

# ===== 5. UNIFIED PROCESSOR - SỬA LẠI LOGIC =====
class UnifiedProcessor:
    """SỬA LẠI: Main processor với logic đúng"""
    
    def __init__(self):
        self.context = ContextManager()
        self.intent = IntentAnalyzer()
        self.situation = SituationMatcher()
        self.rag = RAGCoordinator()
    
    def process(self, user_input: str, user_id: str, domain: str = None, context: str = "") -> dict:
        """SỬA LẠI: Main processing với flow đúng"""
        user_input = user_input.strip()
        if not user_input:
            return format_response("❓ Vui lòng nhập câu hỏi.", source="system")

        # Handle greetings
        greeting_response = handle_greeting(user_input)
        if greeting_response:
            self.context.update(user_id, user_input, greeting_response, "greeting")
            return format_response(greeting_response, source="greeting")

        # Block sensitive content
        sensitive_response = handle_sensitive_content(user_input)
        if sensitive_response:
            return format_response(sensitive_response, source="filter")

        # 1. Context Resolution
        resolution = self.context.resolve_vague_query(user_input, user_id)
        resolved_query = resolution['resolved_query']
        
        logger.info(f"🔍 Processing: '{user_input}' → '{resolved_query}'")

        # 2. PHÂN TÍCH Ý ĐỊNH - SỬA LẠI
        intent_analysis = self.intent.analyze_intent(resolved_query, resolution)
        logger.info(f"🎯 Intent: {intent_analysis['intent_type']} (confidence: {intent_analysis['confidence']:.2f})")
        
        # 3. Domain Detection
        detected_domain = domain or _detect_domain_from_query(resolved_query)
        
        # 4. TÌM KIẾM JSON TRƯỚC - SỬA LẠI
        logger.info("📋 Trying JSON search first...")
        json_result = self.situation.match(resolved_query, intent_analysis, detected_domain)
        
        if json_result:
            logger.info("✅ JSON match found - returning result")
            self.context.update(user_id, user_input, json_result, "json_data")
            return format_response(json_result, source="json_data", metadata={
                "domain": detected_domain,
                "intent_analysis": intent_analysis,
                "resolution": resolution
            })
        
        # 5. KHÔNG CÓ JSON → CHUYỂN RAG
        logger.info("❌ No JSON match - routing to RAG...")
        
        rag_data = {
            'original_query': user_input,
            'resolved_query': resolved_query,
            'user_id': user_id,
            'intent_analysis': intent_analysis,
            'resolution': resolution,
            'domain': detected_domain
        }
        
        def sync_rag_query():
            return asyncio.run(self.rag.query(rag_data))
        
        rag_result = sync_rag_query()
        
        if rag_result['success']:
            logger.info("✅ RAG processing successful")
            self.context.update(user_id, user_input, rag_result['answer'], "rag_engine")
            return format_response(
                rag_result['answer'], 
                source="rag_engine",
                metadata={
                    "intent_analysis": intent_analysis,
                    "rag_metadata": rag_result.get('metadata', {})
                }
            )
        else:
            logger.warning("⚠️ RAG processing failed, using fallback")
            self.context.update(user_id, user_input, rag_result['answer'], "fallback")
            return format_response(rag_result['answer'], source="fallback")

# ===== GLOBAL PROCESSOR INSTANCE =====
_unified_processor = UnifiedProcessor()

# ===== PUBLIC INTERFACE =====
def get_user_context(user_id: str) -> dict:
    """Get user context"""
    return _unified_processor.context.get(user_id)

def update_user_context(user_id: str, query: str, response: str, source: str):
    """Update user context"""
    _unified_processor.context.update(user_id, query, response, source)

def process_user_query(user_input: str, user_id: str, domain: str = None, context: str = "") -> dict:
    """Main entry point - SỬA LẠI"""
    return _unified_processor.process(user_input, user_id, domain, context)

async def query_rag_engine(user_input: str, user_id: str = None, intent_analysis: dict = None) -> dict:
    """Query RAG engine"""
    rag_data = {
        'resolved_query': user_input,
        'original_query': user_input,
        'user_id': user_id,
        'intent_analysis': intent_analysis or {}
    }
    return await _unified_processor.rag.query(rag_data)

# ===== HELPER FUNCTIONS =====
def _detect_domain_from_query(query: str, context: str = "") -> str:
    """Detect domain from keywords"""
    combined = f"{context} {query}".lower()
    
    # Simple domain detection
    if any(word in combined for word in ['hộ chiếu', 'xuất cảnh', 'nhập cảnh', 'visa']):
        return "xuatnhapcanh"
    elif any(word in combined for word in ['căn cước', 'cccd', 'cmnd']):
        return "cancuoc"
    elif any(word in combined for word in ['cư trú', 'tạm trú']):
        return "cutru"
    
    return "xuatnhapcanh"  # Default

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
    """Block sensitive content"""
    user_lower = user_input.lower()
    
    # Block political content
    political_keywords = ["chính trị", "bầu cử", "chính quyền", "lãnh đạo"]
    if any(kw in user_lower for kw in political_keywords):
        return "❌ Tôi chỉ hỗ trợ thông tin về thủ tục hành chính, không trả lời nội dung chính trị."
    
    # Block personal information patterns
    personal_patterns = [
        r'\b\d{9,12}\b',  # ID numbers
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',  # Dates
        r'\b0\d{9,10}\b',  # Phone numbers
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',  # Email
    ]
    
    for pattern in personal_patterns:
        if re.search(pattern, user_input):
            return (
                "⚠️ Tôi là trợ lý ảo chỉ hỗ trợ hướng dẫn thủ tục hành chính, bạn không nên nhập thông tin cá nhân vào đây để tránh nguy cơ mất an toàn thông tin.\n\n"
                "Tôi có thể giúp bạn:\n"
                "**• Thủ tục cấp hộ chiếu**\n" 
                "**• Thông tin pháp lý xuất nhập cảnh**\n"
                "**• Hướng dẫn làm hồ sơ.**\n"
            )
    
    return None

# ===== SYSTEM MANAGEMENT =====
async def initialize_system(force_rebuild=False):
    """Initialize system"""
    logger.info("🔧 Initializing Unified System...")
    
    rag_success = await initialize_rag_engine("xuatnhapcanh")
    
    return {
        'success': True,
        'rag_available': rag_success,
        'features': ['intent_analysis', 'json_search_first', 'rag_fallback'],
        'message': f"Unified System ready. RAG: {'✅' if rag_success else '❌'}"
    }

def get_system_status():
    """Get system status"""
    rag_engine = get_rag_engine()
    
    status = {
        'unified_processor': {
            'available': True,
            'features': ['intent_analysis', 'json_search_first', 'rag_fallback'],
            'components': ['ContextManager', 'IntentAnalyzer', 'SituationMatcher', 'RAGCoordinator']
        },
        'rag_engine': {
            'available': False,
            'initialized': _rag_initialization_attempted
        }
    }
    
    if rag_engine:
        try:
            is_initialized = hasattr(rag_engine, 'is_initialized') and rag_engine.is_initialized
            status['rag_engine']['available'] = is_initialized
            
            if is_initialized:
                stats = rag_engine.get_stats()
                status['rag_engine']['stats'] = stats
            
        except Exception as e:
            status['rag_engine']['error'] = str(e)
    
    return status

# ===== EXPORTS =====
__all__ = [
    'process_user_query',
    'initialize_system', 
    'get_system_status',
    'get_rag_engine',
    'initialize_rag_engine',
    'get_user_context',
    'update_user_context',
    'query_rag_engine',
    'UnifiedProcessor',
    'ContextManager',
    'IntentAnalyzer', 
    'SituationMatcher',
    'RAGCoordinator'
]