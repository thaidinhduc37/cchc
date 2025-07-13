# services/unified_processor.py - ENHANCED: Conversation memory + smart resolution
"""
🎯 UNIFIED PROCESSOR - ENHANCED
📋 Role: Conversation tracking + sơ bộ analysis + vague resolution
🔧 NO breaking changes - enhance existing structure
"""
import os
import json
import logging
import asyncio
import re
from datetime import datetime
from utils.response_formatter import format_response

# Vector RAG integration 
try:
    from services.vector_rag.rag_engine import RAGEngine
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

logger = logging.getLogger(__name__)

# Global RAG engine
_global_rag_engine = None
_rag_initialization_attempted = False

def get_rag_engine():
    global _global_rag_engine
    return _global_rag_engine

async def initialize_rag_engine(domain: str = "xuatnhapcanh"):
    """Initialize RAG Engine - keep existing logic"""
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

# ===== ENHANCED CONVERSATION MANAGER =====
class ConversationManager:
    """ENHANCED: Track conversation + smart vague resolution"""
    
    def __init__(self):
        self.sessions = {}  # user_id -> session data
        
        # Simple patterns for vague detection - NO hardcode
        self.vague_indicators = [
            'ở đâu', 'tại đâu', 'bao nhiêu', 'thế nào', 'ra sao', 
            'được không', 'có được', 'cần gì', 'thì sao'
        ]
        
    def get_conversation_context(self, user_id: str) -> dict:
        """Get conversation context - enhanced"""
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                'has_history': False,
                'entities': {},
                'topic_thread': None,
                'recent_queries': [],
                'conversation_summary': "",
                'query_count': 0,
                'session_info': {
                    'created_at': datetime.now().isoformat(),
                    'last_activity': datetime.now().isoformat(),
                    'total_interactions': 0
                }
            }
        
        return self.sessions[user_id]
    
    def add_interaction(self, user_id: str, query: str, response: str, source: str):
        """Add interaction to conversation - enhanced tracking"""
        context = self.get_conversation_context(user_id)
        
        # Extract entities from query
        entities = self._extract_entities(query)
        
        # Update accumulated entities
        for key, value in entities.items():
            context['entities'][key] = value
        
        # Detect topic thread
        new_topic = self._detect_topic_thread(query, response)
        if new_topic:
            context['topic_thread'] = new_topic
        
        # Add to recent queries (keep last 5)
        context['recent_queries'].append(query)
        if len(context['recent_queries']) > 5:
            context['recent_queries'].pop(0)
        
        # Update conversation summary (last 2 queries for context)
        if len(context['recent_queries']) >= 2:
            context['conversation_summary'] = " | ".join(context['recent_queries'][-2:]) + "..."
        else:
            context['conversation_summary'] = query + "..."
        
        # Update counters
        context['query_count'] += 1
        context['has_history'] = True
        context['session_info']['last_activity'] = datetime.now().isoformat()
        context['session_info']['total_interactions'] += 1
    
    def resolve_vague_query(self, user_id: str, query: str) -> str:
        """SMART vague query resolution using conversation context"""
        context = self.get_conversation_context(user_id)
        
        # Check if query is vague
        is_vague = any(indicator in query.lower() for indicator in self.vague_indicators)
        
        if not is_vague or not context['topic_thread']:
            return query
        
        # Smart resolution based on context
        topic = context['topic_thread']
        entities = context['entities']
        
        # Build enhanced query
        enhanced_parts = [topic]
        
        # Add location if detected and query asks location
        if ('ở đâu' in query.lower() or 'tại đâu' in query.lower()) and entities.get('location'):
            # Extract location mention from query itself
            location_in_query = self._extract_location_from_query(query)
            if location_in_query:
                enhanced_parts.append(f"tại {location_in_query}")
        
        # Add age context if relevant
        if entities.get('age') and any(word in query.lower() for word in ['lệ phí', 'thủ tục', 'điều kiện']):
            if int(entities['age']) < 14:
                enhanced_parts.append("cho trẻ em")
        
        # Combine with original query
        enhanced_query = " ".join(enhanced_parts) + " " + query
        
        if enhanced_query != query:
            logger.info(f"🔗 Vague resolution: '{query}' → '{enhanced_query}'")
        
        return enhanced_query
    
    def _extract_entities(self, query: str) -> dict:
        """Extract entities from query - simple patterns"""
        entities = {}
        query_lower = query.lower()
        
        # Age extraction
        age_patterns = [
            r'(\d{1,2})\s*tuổi',
            r'con\s+(?:tôi|mình|em)\s+(\d{1,2})',
            r'cháu\s+(\d{1,2})'
        ]
        
        for pattern in age_patterns:
            match = re.search(pattern, query_lower)
            if match:
                entities['age'] = int(match.group(1))
                break
        
        # Location extraction - simple detection
        location_patterns = [
            r'ở\s+([a-záàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ\s]+?)(?:\s+(?:làm|thì|thế))',
            r'tại\s+([a-záàảãạăắằẳẵặâấầẩẫậđéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵ\s]+?)(?:\s+(?:làm|thì|thế))'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, query_lower)
            if match:
                location = match.group(1).strip()
                # Normalize common variations
                location = location.replace('đà nẵng', 'Đà Nẵng').replace('hà nội', 'Hà Nội')
                entities['location'] = location
                break
        
        return entities
    
    def _detect_topic_thread(self, query: str, response: str) -> str:
        """Detect main topic from query/response"""
        text = f"{query} {response}".lower()
        
        # Topic detection with priority
        topics = [
            ('hộ chiếu', ['hộ chiếu', 'passport']),
            ('visa', ['visa', 'thị thực']),
            ('xuất cảnh', ['xuất cảnh', 'đi nước ngoài', 'ra nước ngoài']),
            ('nhập cảnh', ['nhập cảnh', 'về nước'])
        ]
        
        for topic, keywords in topics:
            if any(keyword in text for keyword in keywords):
                return topic
        
        return None
    
    def _extract_location_from_query(self, query: str) -> str:
        """Extract location mentioned in query"""
        query_lower = query.lower()
        
        # Common locations
        locations = {
            'đà nẵng': ['đà nẵng', 'da nang'],
            'hà nội': ['hà nội', 'ha noi', 'thủ đô'],
            'hồ chí minh': ['hồ chí minh', 'hcm', 'sài gòn', 'tp hcm'],
            'cần thơ': ['cần thơ', 'can tho'],
            'hải phòng': ['hải phòng', 'hai phong'],
            'đắk lắk': ['đắk lắk', 'dak lak', 'daklak']
        }
        
        for standard_name, variants in locations.items():
            if any(variant in query_lower for variant in variants):
                return standard_name
        
        return None

# ===== ENHANCED INTENT ANALYZER =====
class IntentAnalyzer:
    """Enhanced intent analysis for better routing"""
    
    def analyze_intent(self, query: str, context_info: dict) -> dict:
        """Enhanced intent analysis"""
        query_lower = query.lower().strip()
        
        # Detect intent type
        intent_type = self._detect_intent_type(query_lower)
        
        # Check for special requirements
        needs_conclusion = self._needs_conclusion(query_lower)
        is_procedure = self._is_procedure(query_lower)
        
        # Calculate confidence
        confidence = self._calculate_confidence(intent_type, query_lower, context_info)
        
        # Always try JSON first, then RAG
        route_to = 'JSON'
        
        return {
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
        """Detect intent type"""
        # Direct legal reference
        if re.search(r'(?:điều|khoản|điểm)\s+\d+', query):
            return 'legal_reference'
        
        # Procedure question
        if any(word in query for word in ['thủ tục', 'làm', 'cần', 'như thế nào', 'quy trình']):
            return 'procedure'
        
        # Legal/eligibility question
        if any(phrase in query for phrase in ['có được', 'được không', 'có thể']):
            return 'eligibility'
        
        # Cost question
        if any(word in query for word in ['lệ phí', 'phí', 'bao nhiêu', 'giá']):
            return 'cost'
        
        return 'general'
    
    def _needs_conclusion(self, query: str) -> bool:
        """Check if needs ĐƯỢC/KHÔNG conclusion"""
        return any(phrase in query for phrase in ['có được', 'được không', 'có thể không'])
    
    def _is_procedure(self, query: str) -> bool:
        """Check if procedure question"""
        return any(word in query for word in ['thủ tục', 'làm', 'cần gì', 'như thế nào', 'quy trình'])
    
    def _has_constraints(self, query: str) -> bool:
        """Check for constraints"""
        return any(word in query for word in ['bị', 'không', 'hết hạn', 'trẻ em', 'tuổi'])
    
    def _calculate_confidence(self, intent_type: str, query: str, context_info: dict) -> float:
        """Calculate confidence score"""
        base_confidence = {
            'legal_reference': 0.9,
            'procedure': 0.8, 
            'eligibility': 0.8,
            'cost': 0.7,
            'general': 0.6
        }.get(intent_type, 0.5)
        
        # Boost if has context
        if context_info.get('has_history'):
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)

# ===== KEEP EXISTING CLASSES =====
class SituationMatcher:
    """Keep existing JSON matching logic"""
    
    def __init__(self):
        self.json_cache = {}
    
    def match(self, resolved_query: str, intent_analysis: dict, domain: str = "xuatnhapcanh") -> str:
        """JSON matching - keep existing logic but enhance input"""
        try:
            json_path = f"dataset/{domain}/response.json"
            
            if not os.path.exists(json_path):
                return None

            # Load JSON data
            if json_path not in self.json_cache:
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.json_cache[json_path] = json.load(f)
            
            data = self.json_cache[json_path]
            query_lower = resolved_query.lower().strip()
            
            # Try exact pattern matches first
            for section_name, items in data.items():
                if not isinstance(items, list):
                    continue
                    
                for item in items:
                    # Check question patterns (highest priority)
                    patterns = item.get('question_patterns', [])
                    for pattern in patterns:
                        if pattern.lower() in query_lower:
                            if section_name == 'procedures':
                                return item.get('base_response', {}).get('content', '')
                            elif section_name == 'legal_situations':
                                return item.get('response', {}).get('content', '')
            
            # Fallback to keyword matching (keep existing logic)
            return None
            
        except Exception as e:
            logger.error(f"JSON matching error: {e}")
            return None

class RAGCoordinator:
    """Keep existing RAG coordination"""
    
    async def query(self, rag_data: dict) -> dict:
        """Enhanced RAG query with better context"""
        rag_engine = get_rag_engine()
        
        if not rag_engine:
            logger.error("❌ RAG Engine not available")
            return {'success': False, 'answer': self._create_fallback_response(rag_data)}
        
        try:
            logger.info(f"🤖 Querying RAG engine with enhanced context...")
            
            # Enhanced data for RAG
            enhanced_data = {
                'resolved_query': rag_data['resolved_query'],
                'original_query': rag_data['original_query'], 
                'user_id': rag_data.get('user_id'),
                'conversation_context': rag_data.get('conversation_context', {}),
                'intent_analysis': rag_data.get('intent_analysis', {}),
                'entities': rag_data.get('entities', {}),
                'topic_thread': rag_data.get('topic_thread')
            }
            
            result = await rag_engine.query(
                rag_data['resolved_query'], 
                session_id=rag_data.get('user_id'),
                unified_data=enhanced_data
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
        """Create fallback response"""
        query = rag_data.get('original_query', 'câu hỏi của bạn')
        
        return (
            f"Xin lỗi, tôi chưa tìm thấy thông tin về '{query}'. "
            "Bạn có thể:\n"
            "• Thử diễn đạt lại câu hỏi\n"
            "• Hỏi về thủ tục cụ thể\n"
            "• Liên hệ cơ quan có thẩm quyền: 069.1000.000\n\n"
            "Website: https://dichvucong.bocongan.gov.vn"
        )

# ===== MAIN UNIFIED PROCESSOR =====
class UnifiedProcessor:
    """ENHANCED: Main processor with conversation memory"""
    
    def __init__(self):
        self.conversation = ConversationManager()  # Enhanced
        self.intent = IntentAnalyzer()           # Enhanced  
        self.situation = SituationMatcher()     # Keep existing
        self.rag = RAGCoordinator()              # Enhanced
    
    def process(self, user_input: str, user_id: str, domain: str = None, context: str = "") -> dict:
        """ENHANCED: Main processing with conversation memory"""
        user_input = user_input.strip()
        if not user_input:
            return format_response("❓ Vui lòng nhập câu hỏi.", source="system")

        # Handle greetings
        greeting_response = handle_greeting(user_input)
        if greeting_response:
            self.conversation.add_interaction(user_id, user_input, greeting_response, "greeting")
            return format_response(greeting_response, source="greeting")

        # Block sensitive content
        sensitive_response = handle_sensitive_content(user_input)
        if sensitive_response:
            return format_response(sensitive_response, source="filter")

        # 1. ENHANCED: Get conversation context
        conversation_context = self.conversation.get_conversation_context(user_id)
        
        # 2. ENHANCED: Resolve vague queries
        resolved_query = self.conversation.resolve_vague_query(user_id, user_input)
        
        logger.info(f"🔍 Enhanced processing: '{user_input}' → '{resolved_query}'")
        if resolved_query != user_input:
            logger.info(f"📝 Vague resolution applied")

        # 3. ENHANCED: Analyze intent with context
        intent_analysis = self.intent.analyze_intent(resolved_query, {
            'has_history': conversation_context['has_history'],
            'topic_thread': conversation_context['topic_thread'],
            'entities': conversation_context['entities']
        })
        
        logger.info(f"🎯 Intent: {intent_analysis['intent_type']} (confidence: {intent_analysis['confidence']:.2f})")
        
        # 4. Domain detection
        detected_domain = domain or _detect_domain_from_query(resolved_query)
        
        # 5. Try JSON matching first
        logger.info("📋 Trying JSON search first...")
        json_result = self.situation.match(resolved_query, intent_analysis, detected_domain)
        
        if json_result:
            logger.info("✅ JSON match found")
            self.conversation.add_interaction(user_id, user_input, json_result, "json_data")
            return format_response(json_result, source="json_data", metadata={
                "domain": detected_domain,
                "intent_analysis": intent_analysis,
                "enhanced_context": conversation_context
            })
        
        # 6. ENHANCED: Route to RAG with full context
        logger.info("❌ No JSON match - routing to RAG...")
        
        rag_data = {
            'original_query': user_input,
            'resolved_query': resolved_query,
            'user_id': user_id,
            'conversation_context': conversation_context,
            'intent_analysis': intent_analysis,
            'entities': conversation_context['entities'],
            'topic_thread': conversation_context['topic_thread'],
            'domain': detected_domain
        }
        
        # Sync RAG call (keep existing pattern)
        def sync_rag_query():
            return asyncio.run(self.rag.query(rag_data))
        
        rag_result = sync_rag_query()
        
        if rag_result['success']:
            logger.info("✅ RAG processing successful")
            self.conversation.add_interaction(user_id, user_input, rag_result['answer'], "rag_engine")
            return format_response(
                rag_result['answer'], 
                source="rag_engine",
                metadata={
                    "intent_analysis": intent_analysis,
                    "rag_metadata": rag_result.get('metadata', {}),
                    "enhanced_context": conversation_context
                }
            )
        else:
            logger.warning("⚠️ RAG processing failed")
            self.conversation.add_interaction(user_id, user_input, rag_result['answer'], "fallback")
            return format_response(rag_result['answer'], source="fallback")

# ===== GLOBAL INSTANCE =====
_unified_processor = UnifiedProcessor()

# ===== PUBLIC INTERFACE =====
def get_user_context(user_id: str) -> dict:
    """Get user context"""
    return _unified_processor.conversation.get_conversation_context(user_id)

def update_user_context(user_id: str, query: str, response: str, source: str):
    """Update user context"""
    _unified_processor.conversation.add_interaction(user_id, query, response, source)

def process_user_query(user_input: str, user_id: str, domain: str = None, context: str = "") -> dict:
    """Main entry point - ENHANCED"""
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
    
    if any(word in combined for word in ['hộ chiếu', 'xuất cảnh', 'nhập cảnh', 'visa']):
        return "xuatnhapcanh"
    elif any(word in combined for word in ['căn cước', 'cccd', 'cmnd']):
        return "cancuoc"
    elif any(word in combined for word in ['cư trú', 'tạm trú']):
        return "cutru"
    
    return "xuatnhapcanh"

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
        r'\b\d{9,12}\b',
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',
        r'\b0\d{9,10}\b',
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    ]
    
    for pattern in personal_patterns:
        if re.search(pattern, user_input):
            return (
                "⚠️ Vui lòng không nhập thông tin cá nhân để đảm bảo an toàn.\n\n"
                "Tôi có thể hỗ trợ:\n"
                "• Thủ tục cấp hộ chiếu\n" 
                "• Thông tin pháp lý xuất nhập cảnh\n"
                "• Hướng dẫn làm hồ sơ"
            )
    
    return None

# ===== SYSTEM MANAGEMENT =====
async def initialize_system(force_rebuild=False):
    """Initialize system"""
    logger.info("🔧 Initializing Enhanced Unified System...")
    
    rag_success = await initialize_rag_engine("xuatnhapcanh")
    
    return {
        'success': True,
        'rag_available': rag_success,
        'features': ['enhanced_conversation_memory', 'smart_vague_resolution', 'intent_analysis', 'json_search_first', 'rag_fallback'],
        'message': f"Enhanced Unified System ready. RAG: {'✅' if rag_success else '❌'}"
    }

def get_system_status():
    """Get system status"""
    rag_engine = get_rag_engine()
    
    status = {
        'unified_processor': {
            'available': True,
            'version': 'Enhanced v2.0',
            'features': ['conversation_memory_4_5_turns', 'smart_vague_resolution', 'enhanced_intent_analysis', 'entity_tracking'],
            'components': ['ConversationManager', 'IntentAnalyzer', 'SituationMatcher', 'RAGCoordinator']
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
    'ConversationManager',
    'IntentAnalyzer', 
    'SituationMatcher',
    'RAGCoordinator'
]