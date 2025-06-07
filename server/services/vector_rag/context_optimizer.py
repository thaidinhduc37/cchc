# server/services/vector_rag/context_optimizer.py
"""
Context Optimizer - OPTIMIZED & CONCISE
"""
import re
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class OptimizedContext:
    """Optimized context structure"""
    context: str
    confidence_score: float
    source_summary: str
    context_type: str
    total_sources: int
    web_sources: int
    vector_sources: int

class VietnameseContextOptimizer:
    """Simplified context optimizer"""
    
    def __init__(self):
        self.max_context_length = 1800
        self.max_sources = 5
        self.min_section_length = 40
        
        # Key quality indicators
        self.quality_keywords = [
            'điều', 'khoản', 'quy định', 'thủ tục', 'hồ sơ',
            'lệ phí', 'thời gian', 'cơ quan', 'điều kiện',
            'hộ chiếu', 'thị thực', 'tạm trú', 'thường trú'
        ]
    
    def optimize_context(self, search_results: List[Dict], query_features: Any = None) -> OptimizedContext:
        """Optimize context - simplified"""
        
        if not search_results:
            return OptimizedContext(
                context="",
                confidence_score=0.0,
                source_summary="Không có dữ liệu",
                context_type="empty",
                total_sources=0,
                web_sources=0,
                vector_sources=0
            )
        
        # 1. Score and sort results
        scored_results = self._score_results(search_results)
        
        # 2. Select top sources
        selected_sources = self._select_top_sources(scored_results)
        
        # 3. Build context
        context, source_summary = self._build_context(selected_sources)
        
        # 4. Calculate confidence
        confidence = self._calculate_confidence(selected_sources, context)
        
        # 5. Determine context type
        web_count = len([s for s in selected_sources if s.get('metadata', {}).get('content_type') == 'web_procedure'])
        vector_count = len([s for s in selected_sources if s.get('metadata', {}).get('content_type') == 'legal_document'])
        
        if web_count > vector_count:
            context_type = 'web_dominant'
        elif vector_count > web_count:
            context_type = 'vector_dominant'
        else:
            context_type = 'balanced'
        
        return OptimizedContext(
            context=context,
            confidence_score=confidence,
            source_summary=source_summary,
            context_type=context_type,
            total_sources=len(selected_sources),
            web_sources=web_count,
            vector_sources=vector_count
        )
    
    def _score_results(self, results: List[Dict]) -> List[Dict]:
        """Score results based on quality"""
        scored = []
        
        for result in results:
            content = result.get('content', '')
            score = result.get('score', 0.5)
            
            # Content quality boost
            content_lower = content.lower()
            keyword_count = sum(1 for kw in self.quality_keywords if kw in content_lower)
            quality_boost = min(keyword_count * 0.1, 0.4)
            
            # Length penalty for too short content
            if len(content) < 100:
                score -= 0.2
            
            # Legal structure bonus
            if any(pattern in content_lower for pattern in ['điều ', 'khoản ', 'theo quy định']):
                score += 0.2
            
            final_score = min(score + quality_boost, 1.0)
            
            result_copy = result.copy()
            result_copy['final_score'] = final_score
            scored.append(result_copy)
        
        return sorted(scored, key=lambda x: x['final_score'], reverse=True)
    
    def _select_top_sources(self, scored_results: List[Dict]) -> List[Dict]:
        """Select top sources"""
        # Filter by minimum quality
        quality_threshold = 0.2
        filtered = [r for r in scored_results if r['final_score'] >= quality_threshold]
        
        # Take top sources
        return filtered[:self.max_sources]
    
    def _build_context(self, sources: List[Dict]) -> tuple:
        """Build context from sources"""
        if not sources:
            return "", "Không có nguồn"
        
        context_parts = []
        source_info = []
        current_length = 0
        
        for i, source in enumerate(sources):
            content = source.get('content', '').strip()
            
            if len(content) < self.min_section_length:
                continue
            
            # Add section header
            source_type = 'WEB' if source.get('metadata', {}).get('content_type') == 'web_procedure' else 'LUẬT'
            section_header = f"\n--- NGUỒN {i+1} ({source_type}) ---\n"
            
            # Check if fits
            estimated_length = current_length + len(section_header) + len(content)
            
            if estimated_length > self.max_context_length:
                # Truncate content to fit
                remaining_space = self.max_context_length - current_length - len(section_header) - 50
                if remaining_space > 100:
                    content = content[:remaining_space] + "..."
                else:
                    break
            
            # Add to context
            formatted_section = section_header + content
            context_parts.append(formatted_section)
            current_length += len(formatted_section)
            
            # Track source info
            source_name = source.get('metadata', {}).get('file_name', source.get('title', 'Unknown'))
            source_info.append(f"{source_type}: {source_name}")
        
        final_context = '\n'.join(context_parts)
        source_summary = '; '.join(source_info[:3])
        
        return final_context, source_summary
    
    def _calculate_confidence(self, sources: List[Dict], context: str) -> float:
        """Calculate confidence score"""
        if not sources or not context:
            return 0.0
        
        # Base confidence from source scores
        avg_score = sum(s.get('final_score', 0.5) for s in sources) / len(sources)
        
        # Source count factor
        count_factor = min(len(sources) / 3.0, 1.0)
        
        # Context quality factor
        context_keywords = sum(1 for kw in self.quality_keywords if kw in context.lower())
        quality_factor = min(context_keywords / 5.0, 1.0)
        
        # Diversity bonus
        has_web = any(s.get('metadata', {}).get('content_type') == 'web_procedure' for s in sources)
        has_vector = any(s.get('metadata', {}).get('content_type') == 'legal_document' for s in sources)
        diversity_bonus = 0.2 if (has_web and has_vector) else 0.1
        
        final_confidence = (avg_score * 0.4 + count_factor * 0.2 + quality_factor * 0.2) + diversity_bonus
        return min(final_confidence + 0.15, 1.0)  # Base boost
    
    def validate_context_quality(self, context: str, query: str) -> Dict[str, Any]:
        """Validate context quality"""
        if not context or len(context) < 50:
            return {
                'is_valid': False,
                'reason': 'Context quá ngắn',
                'quality_score': 0.0
            }
        
        # Check keyword overlap
        query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
        context_words = set(re.findall(r'\b\w{3,}\b', context.lower()))
        overlap = len(query_words & context_words)
        
        if overlap < 1:
            return {
                'is_valid': False,
                'reason': 'Context không liên quan',
                'quality_score': 0.2
            }
        
        quality_score = min(overlap / max(len(query_words), 1) + 0.4, 1.0)
        
        return {
            'is_valid': True,
            'quality_score': quality_score,
            'word_overlap': overlap,
            'context_length': len(context)
        }