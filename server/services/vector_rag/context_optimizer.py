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
        """🔧 FIXED: Main organize reranked data for LLM"""
        self.stats['total_processed'] += 1
        
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
        
        # Determine content type
        content_type = self._determine_content_type(primary_content, query_features)
        
        # Determine answer type & detect exceptions (lightweight)
        answer_type = self._determine_answer_type(primary_content, query_features)
        exception_detected = self._detect_exceptions(primary_content)
        
        # 🔧 FIX: Build context properly
        context = self._build_context(primary_content, primary_citation, supporting_contents)
        
        if primary_citation:
            self.stats['full_citations_extracted'] += 1
        
        logger.info(f"Organized: {primary_citation}, type: {answer_type}, exception: {exception_detected}")
        
        return ContextResult(
            query=query,
            primary_content=primary_content,
            primary_citation=primary_citation,
            context=context,  # 🔧 FIX: Properly set context
            answer_type=answer_type,
            exception_detected=exception_detected,
            supporting_contents=supporting_contents,
            needs_conclusion=needs_conclusion,
            context_type=content_type
        )
    
    def _build_context(self, primary_content: str, primary_citation: str, supporting_contents: List[Dict]) -> str:
        """🔧 NEW: Build organized context for LLM"""
        context_parts = []
        
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
        """Determine content type"""
        if query_features and hasattr(query_features, 'primary_intent'):
            intent = query_features.primary_intent
            if intent == 'PROCEDURE':
                return 'procedure'
            elif intent == 'DIRECT_ARTICLE':
                return 'direct_article'
        
        # Check content indicators
        content_lower = content.lower()
        if any(term in content_lower for term in ['thủ tục', 'hồ sơ', 'lệ phí']):
            return 'procedure'
        
        return 'legal'
    
    def _determine_answer_type(self, content: str, query_features: Any) -> str:
        """Determine answer type - lightweight logic"""
        if not content:
            return "legal"
        
        content_lower = content.lower()
        
        # Simple detection
        if any(term in content_lower for term in ['thủ tục', 'hồ sơ', 'trình tự']):
            return "procedure"
        elif 'điều' in content_lower and len(content) < 200:
            return "direct_quote"  # Short direct citation
        else:
            return "legal"  # Default legal explanation
    
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