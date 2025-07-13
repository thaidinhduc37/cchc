# server/services/vector_rag/context_optimizer.py - FIXED VERSION
"""
Context Optimizer - FIXED: Sửa lỗi context_type compatibility
🎯 VAI TRÒ: Extract + organize legal content từ reranker cho LLM
📋 KEY: Trích dẫn đầy đủ chính xác (điểm/khoản/điều)
✅ OUTPUT: Clean organized data for LLM to format
"""
import logging
import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ContextResult:
    """🔧 FIXED: Organized data for LLM - sửa lỗi context_type"""
    query: str = ""
    primary_content: str = ""
    primary_citation: str = ""
    context: str = ""                     # Main context content
    
    # Content organization
    answer_type: str = "legal"    
    exception_detected: bool = False  
    supporting_contents: List[Dict] = None  
    needs_conclusion: bool = False 
    context_type: str = "legal"           # 🔧 FIX: Unified naming - only use context_type
    
    def __post_init__(self):
        if self.supporting_contents is None:
            self.supporting_contents = []
    
        if not self.context and self.primary_content:
            self.context = self.primary_content
            

class ContextOptimizer:
    """🔧 FIXED: Organize data for LLM - trích dẫn đầy đủ"""
    
    def __init__(self):
        self.stats = {'total_processed': 0, 'full_citations_extracted': 0}
        logger.info("ContextOptimizer - FIXED for LLM compatibility")
    
    
    
    async def optimize_context(self, reranker_results: List[Dict], query_features: Any) -> ContextResult:
        """
        ENHANCED: Store query_features for use in other methods
        """
        self.stats['total_processed'] += 1
        
        # Store query_features for use in _build_context()
        self._current_query_features = query_features
        
        # === REST OF METHOD UNCHANGED ===
        if not reranker_results:
            return ContextResult(
                query=self._get_query(query_features),
                primary_content="Không tìm thấy quy định phù hợp.",
                primary_citation="",
                context="Không tìm thấy quy định phù hợp.",
                content_type="error"
            )
        
        query = self._get_query(query_features)
        
        # Extract primary content (reranker đã chọn accurate nhất)
        primary = reranker_results[0]
        primary_content = primary.get('content', '')
        
        # Extract FULL citation (quan trọng nhất)
        primary_citation = self._extract_full_citation(primary_content)
        
        # Supporting content (max 2)
        supporting_contents = []
        for result in reranker_results[1:3]:
            content = result.get('content', '')
            if content and len(content) > 50:
                citation = self._extract_full_citation(content)
                supporting_contents.append({
                    'content': content,
                    'citation': citation
                })
        
        # Check if needs conclusion
        needs_conclusion = self._check_needs_conclusion(query_features)
        
        # ENHANCED: Use enhanced methods
        content_type = self._determine_content_type(primary_content, query_features)
        answer_type = self._determine_answer_type(primary_content, query_features)
        exception_detected = self._detect_exceptions(primary_content)
        
        # ENHANCED: Build context with conversation awareness
        context = self._build_context(primary_content, primary_citation, supporting_contents)
        
        if primary_citation:
            self.stats['full_citations_extracted'] += 1
        
        logger.info(f"Enhanced context: {primary_citation}, type: {content_type}, answer: {answer_type}")
        
        return ContextResult(
            query=query,
            primary_content=primary_content,
            primary_citation=primary_citation,
            context=context,
            answer_type=answer_type,
            exception_detected=exception_detected,
            supporting_contents=supporting_contents,
            needs_conclusion=needs_conclusion,
            context_type=content_type
        )

    def _build_context(self, primary_content: str, primary_citation: str, supporting_contents: List[Dict]) -> str:
        """
        ENHANCED: Build context with conversation awareness
        """
        context_parts = []
        
        # === NEW: CONVERSATION CONTINUITY CHECK ===
        # Add conversation bridge if available
        if hasattr(self, '_current_query_features') and self._current_query_features:
            continuity_note = self._extract_continuity_note(self._current_query_features)
            if continuity_note:
                context_parts.append(continuity_note)
        
        # === EXISTING LOGIC (unchanged) ===
        # Primary content with citation
        if primary_citation:
            context_parts.append(f"Căn cứ {primary_citation}:")
        context_parts.append(primary_content)
        
        # Supporting content
        for i, support in enumerate(supporting_contents[:2]):
            support_citation = support.get('citation', '')
            support_content = support.get('content', '')
            
            if support_citation and support_content:
                context_parts.append(f"\nTham khảo thêm {support_citation}:")
                context_parts.append(support_content[:200] + "..." if len(support_content) > 200 else support_content)
        
        return "\n\n".join(context_parts)
    
    def _get_query(self, query_features: Any) -> str:
        """Get original query"""
        if query_features and hasattr(query_features, 'original_query'):
            return query_features.original_query
        return "câu hỏi của bạn"
    
    def _extract_full_citation(self, content: str) -> str:
        """Extract FULL legal citation - đầy đủ chính xác"""
        if not content:
            return ""
        
        # Pattern priority: Điểm → Khoản → Điều
        citation_patterns = [
            # Điểm X khoản Y Điều Z (most specific)
            (r'điểm\s+([a-z]+)\s+khoản\s+(\d+)\s+điều\s+(\d+[a-z]?)', 
             lambda m: f"Điểm {m.group(1)} khoản {m.group(2)} Điều {m.group(3)}"),
            
            # Khoản X Điều Y
            (r'khoản\s+(\d+)\s+điều\s+(\d+[a-z]?)', 
             lambda m: f"Khoản {m.group(1)} Điều {m.group(2)}"),
            
            # Điều X (standalone)
            (r'điều\s+(\d+[a-z]?)', 
             lambda m: f"Điều {m.group(1)}")
        ]
        
        content_lower = content.lower()
        
        # Try patterns in priority order
        for pattern, formatter in citation_patterns:
            match = re.search(pattern, content_lower)
            if match:
                return formatter(match)
        
        return ""
    
    def _check_needs_conclusion(self, query_features: Any) -> bool:
        """Check if needs ĐƯỢC/KHÔNG conclusion"""
        if not query_features:
            return False
        
        # Check query classifier result
        if hasattr(query_features, 'needs_conclusion'):
            return query_features.needs_conclusion
        
        # Fallback: check original query
        if hasattr(query_features, 'original_query'):
            query = query_features.original_query.lower()
            conclusion_indicators = [
                'được không', 'có được', 'được xuất cảnh không',
                'có thể không', 'được phép không'
            ]
            return any(indicator in query for indicator in conclusion_indicators)
        
        return False
    
    def _determine_content_type(self, content: str, query_features: Any) -> str:
        """
        ENHANCED: Determine content type with conversation context
        """
        # === EXISTING LOGIC ===
        if query_features and hasattr(query_features, 'primary_intent'):
            intent = query_features.primary_intent
            if intent == 'PROCEDURE':
                return 'procedure'
            elif intent == 'DIRECT_ARTICLE':
                return 'direct_article'
        
        # Check content indicators (existing)
        content_lower = content.lower()
        if any(term in content_lower for term in ['thủ tục', 'hồ sơ', 'lệ phí']):
            return 'procedure'
        
        # === NEW: CONVERSATION CONTEXT ENHANCEMENT ===
        if query_features:
            # Check conversation topic thread
            if hasattr(query_features, 'topic_thread'):
                topic_thread = query_features.topic_thread
                if topic_thread == 'hộ chiếu' and 'hộ chiếu' in content_lower:
                    return 'passport_focused'
                elif topic_thread == 'visa' and 'visa' in content_lower:
                    return 'visa_focused'
            
            # Check citizen profile context
            if hasattr(query_features, 'citizen_profile'):
                citizen_profile = query_features.citizen_profile
                
                # First-time applicant context
                if citizen_profile.get('passport_status') == 'not_have':
                    if any(term in content_lower for term in ['lần đầu', 'chưa có']):
                        return 'first_time_guidance'
                
                # Expired passport context  
                elif citizen_profile.get('passport_status') == 'expired':
                    if any(term in content_lower for term in ['cấp lại', 'hết hạn']):
                        return 'renewal_guidance'
                
                # Minor context
                if citizen_profile.get('age_group') == 'minor':
                    if any(term in content_lower for term in ['trẻ em', 'dưới 14']):
                        return 'minor_procedures'
        
        return 'legal'  # Default
    
    def _determine_answer_type(self, content: str, query_features: Any) -> str:
        """
        ENHANCED: Determine answer type with conversation context  
        """
        if not content:
            return "legal"
        
        content_lower = content.lower()
        
        # === EXISTING LOGIC ===
        # Simple detection
        if any(term in content_lower for term in ['thủ tục', 'hồ sơ', 'trình tự']):
            return "procedure"
        elif 'điều' in content_lower and len(content) < 200:
            return "direct_quote"  # Short direct citation
        
        # === NEW: CONVERSATION-AWARE ANSWER TYPE ===
        if query_features:
            # Check conversation context for better answer type
            if hasattr(query_features, 'citizen_profile'):
                citizen_profile = query_features.citizen_profile
                
                # Supportive answer type for first-time users
                if citizen_profile.get('passport_status') == 'not_have':
                    return "supportive_guidance"
                
                # Efficient answer type for experienced users
                elif citizen_profile.get('passport_status') in ['expired', 'valid']:
                    return "efficient_guidance"
                
                # Special handling for minors
                if citizen_profile.get('age_group') == 'minor':
                    return "minor_guidance"
            
            # Check for conversational context
            if hasattr(query_features, 'topic_thread') and query_features.topic_thread:
                # Conversational answer for continuing topics
                return "conversational"
            
            # Check original query for tone hints
            if hasattr(query_features, 'original_query'):
                original_query = query_features.original_query.lower()
                
                # Question-style queries need explanatory answers
                if any(word in original_query for word in ['tại sao', 'vì sao', 'như thế nào']):
                    return "explanatory"
                
                # Location-specific queries
                if any(word in original_query for word in ['ở đâu', 'tại đâu']):
                    return "location_specific"
        
        return "legal"  # Default

    def _extract_continuity_note(self, query_features: Any) -> str:
        """
        HELPER: Extract conversation continuity note (simple)
        """
        if not query_features:
            return ""
        
        continuity_parts = []
        
        # Topic continuity
        if hasattr(query_features, 'topic_thread'):
            topic_thread = query_features.topic_thread
            if topic_thread == 'hộ chiếu':
                continuity_parts.append("Tiếp tục về thủ tục hộ chiếu")
            elif topic_thread == 'visa':
                continuity_parts.append("Về vấn đề visa bạn hỏi")
        
        # Location context
        if hasattr(query_features, 'citizen_profile'):
            citizen_profile = query_features.citizen_profile
            location = citizen_profile.get('location')
            
            if location and hasattr(query_features, 'original_query'):
                original_query = query_features.original_query.lower()
                if any(word in original_query for word in ['ở đâu', 'tại đâu', 'thì sao']):
                    continuity_parts.append(f"Đối với {location}")
        
        return ', '.join(continuity_parts) if continuity_parts else ""

    
    def _detect_exceptions(self, content: str) -> bool:
        """Detect exceptions/restrictions - simple check"""
        if not content:
            return False
        
        content_lower = content.lower()
        exception_words = ['không được', 'bị cấm', 'tạm hoãn', 'hạn chế', 'trừ trường hợp', 'ngoại trừ']
        
        return any(word in content_lower for word in exception_words)
    
    def get_stats(self) -> Dict[str, Any]:
        """Simple stats"""
        total = self.stats['total_processed']
        citation_rate = self.stats['full_citations_extracted'] / total if total > 0 else 0
        
        return {
            'version': 'Context Optimizer - FIXED v1.1',
            'role': 'Organize reranked data for LLM',
            'performance': {
                'total_processed': total,
                'full_citation_rate': round(citation_rate, 3)
            },
            'features': ['full_citation_extraction', 'content_organization', 'conclusion_detection', 'context_type_compatibility']
        }
    
    def reset_stats(self):
        """Reset stats"""
        self.stats = {'total_processed': 0, 'full_citations_extracted': 0}
        logger.info("Context Optimizer statistics reset")

# Backward compatibility
VietnameseContextOptimizer = ContextOptimizer