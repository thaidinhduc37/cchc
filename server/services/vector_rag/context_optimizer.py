# server/services/vector_rag/context_optimizer.py
"""
Context Optimizer - NÂNG CẤP NHẸ: Giữ nguyên logic cũ + enhance từ từ
"""
import re
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class OptimizedContext:
    """✅ GIỮ NGUYÊN Original structure"""
    context: str
    confidence_score: float
    source_summary: str
    context_type: str
    total_sources: int
    web_sources: int
    vector_sources: int

class VietnameseContextOptimizer:
    """✅ GIỮ NGUYÊN logic cũ + enhance nhẹ thôi"""
    
    def __init__(self):
        # ✅ GIỮ NGUYÊN original settings
        self.max_context_length = 6000
        self.max_sources = 12
        self.min_section_length = 15
        
        # ✅ GIỮ NGUYÊN original indicators + enhance nhẹ
        self.legal_indicators = [
            'điều', 'khoản', 'điểm', 'luật số', 'nghị định số', 'thông tư số',
            'theo quy định tại điều', 'căn cứ luật', 'quy định chi tiết',
            # ✨ CHỈ THÊM một ít indicators rõ ràng
            'căn cứ pháp lý', 'theo luật', 'pháp luật quy định'
        ]
        
        self.procedure_indicators = [
            'mã thủ tục', 'tên thủ tục', 'yêu cầu - điều kiện', 'thành phần hồ sơ',
            'trình tự thực hiện', 'cách thức thực hiện', 'thời hạn giải quyết',
            'phí', 'lệ phí', 'cơ quan thực hiện', 'căn cứ pháp lý',
            'kết quả thực hiện', 'biểu mẫu', 'hồ sơ gồm',
            # ✨ CHỈ THÊM một ít indicators rõ ràng
            'điều kiện thủ tục', 'yêu cầu hồ sơ', 'cách thức nộp'
        ]
    
    def optimize_context(self, search_results: List[Dict], query_features: Any = None) -> OptimizedContext:
        """✅ GIỮ NGUYÊN logic cũ - chỉ enhance nhẹ thôi"""
        
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
        
        # 1. PHÂN LOẠI results thành legal vs procedure - ✅ LOGIC CŨ
        legal_results, procedure_results = self._classify_results(search_results)
        
        # 2. BUILD context with clear separation - ✅ LOGIC CŨ
        context = self._build_separated_context(legal_results, procedure_results)
        
        # 3. Create source summary - ✅ LOGIC CŨ
        source_summary = self._create_source_summary(legal_results, procedure_results)
        
        # 4. Calculate confidence - ✅ LOGIC CŨ với enhance nhẹ
        confidence = self._calculate_confidence_enhanced(legal_results + procedure_results, context)
        
        # 5. Determine context type - ✅ LOGIC CŨ
        web_count = len(procedure_results)
        vector_count = len(legal_results)
        
        if vector_count > web_count:
            context_type = 'vector_dominant'
        elif web_count > vector_count:
            context_type = 'web_dominant'
        else:
            context_type = 'balanced'
        
        return OptimizedContext(
            context=context,
            confidence_score=confidence,
            source_summary=source_summary,
            context_type=context_type,
            total_sources=len(search_results),
            web_sources=web_count,
            vector_sources=vector_count
        )
    
    def _classify_results(self, results: List[Dict]) -> tuple:
        """✅ GIỮ NGUYÊN logic cũ - chỉ enhance scoring nhẹ"""
        legal_results = []
        procedure_results = []
        
        for result in results:
            content = result.get('content', '').lower()
            metadata = result.get('metadata', {})
            content_type = metadata.get('content_type', '')
            
            # Score by content type - enhance nhẹ từ logic cũ
            legal_score = self._score_legal_content_enhanced(content)
            procedure_score = self._score_procedure_content_enhanced(content)
            
            # Classify based on metadata + content score - ✅ LOGIC CŨ
            if content_type == 'legal_document' or legal_score > procedure_score:
                legal_results.append(result)
            elif content_type == 'web_procedure' or procedure_score > legal_score:
                procedure_results.append(result)
            else:
                # Mixed - add to stronger category - ✅ LOGIC CŨ
                if legal_score >= procedure_score:
                    legal_results.append(result)
                else:
                    procedure_results.append(result)
        
        return legal_results[:3], procedure_results[:3]  # ✅ GIỮ NGUYÊN Top 3 each
    
    def _score_legal_content_enhanced(self, content: str) -> float:
        """✨ Enhance nhẹ từ logic cũ"""
        score = 0.0
        # Original scoring - GIỮ NGUYÊN
        for indicator in self.legal_indicators:
            if indicator in content:
                score += 0.2
        return min(score, 1.0)
    
    def _score_procedure_content_enhanced(self, content: str) -> float:
        """✨ Enhance nhẹ từ logic cũ"""
        score = 0.0
        # Original scoring - GIỮ NGUYÊN  
        for indicator in self.procedure_indicators:
            if indicator in content:
                score += 0.15
        return min(score, 1.0)
    
    def _build_separated_context(self, legal_results: List[Dict], procedure_results: List[Dict]) -> str:
        """✅ GIỮ NGUYÊN logic cũ"""
        context_parts = []
        current_length = 0
        
        # Section 1: VĂN BẢN PHÁP LUẬT - ✅ LOGIC CŨ
        if legal_results:
            legal_section = self._build_legal_section(legal_results)
            if legal_section and len(legal_section) > 50:
                context_parts.append("=== VĂN BẢN PHÁP LUẬT ===")
                context_parts.append(legal_section)
                current_length += len(legal_section) + 30
        
        # Section 2: THỦ TỤC HÀNH CHÍNH - ✅ LOGIC CŨ
        if procedure_results and current_length < self.max_context_length - 500:
            procedure_section = self._build_procedure_section(procedure_results)
            if procedure_section and len(procedure_section) > 50:
                context_parts.append("\n=== THỦ TỤC HÀNH CHÍNH ===")
                context_parts.append(procedure_section)
        
        return '\n'.join(context_parts)
    
    def _build_legal_section(self, legal_results: List[Dict]) -> str:
        """✅ GIỮ NGUYÊN logic cũ với enhance nhẹ"""
        parts = []
        for result in legal_results[:3]:  # ✅ GIỮ NGUYÊN Top 3
            content = result.get('content', '').strip()
            if len(content) >= self.min_section_length:
                # ✨ Smart truncation thay vì hard cut
                if len(content) > 2500:
                    content = self._smart_truncate(content, 2500)
                parts.append(content)
        
        return '\n\n'.join(parts)
    
    def _build_procedure_section(self, procedure_results: List[Dict]) -> str:
        """✅ GIỮ NGUYÊN logic cũ với enhance nhẹ"""
        parts = []
        for result in procedure_results[:3]:  # ✅ GIỮ NGUYÊN Top 3
            content = result.get('content', '').strip()
            if len(content) >= self.min_section_length:
                # ✨ Smart truncation thay vì hard cut
                if len(content) > 1200:
                    content = self._smart_truncate(content, 1200)
                parts.append(content)
        
        return '\n\n'.join(parts)
    
    def _smart_truncate(self, content: str, max_length: int) -> str:
        """✨ NEW: Smart truncation at sentence boundaries"""
        if len(content) <= max_length:
            return content
        
        # Try to truncate at sentence boundary
        sentences = re.split(r'[.!?]\s+', content)
        truncated = ""
        
        for sentence in sentences:
            if len(truncated + sentence) + 1 <= max_length - 3:
                truncated += sentence + ". "
            else:
                break
        
        if truncated.strip():
            return truncated.strip() + "..."
        else:
            # Fallback: simple truncation
            return content[:max_length-3] + "..."
    
    def _create_source_summary(self, legal_results: List[Dict], procedure_results: List[Dict]) -> str:
        """✅ GIỮ NGUYÊN logic cũ"""
        sources = []
        
        for result in legal_results[:2]:
            source = result.get('metadata', {}).get('file_name', 'Văn bản pháp luật')
            sources.append(f"LUẬT: {source}")
        
        for result in procedure_results[:2]:
            source = result.get('metadata', {}).get('title', 'Thủ tục hành chính')
            sources.append(f"TTHC: {source}")
        
        return '; '.join(sources)
    
    def _calculate_confidence_enhanced(self, all_results: List[Dict], context: str) -> float:
        """✨ Enhance nhẹ từ logic cũ"""
        if not all_results or not context:
            return 0.0
        
        # ✅ GIỮ NGUYÊN Base confidence từ logic cũ
        avg_score = sum(r.get('score', 0.5) for r in all_results) / len(all_results)
        
        # ✅ GIỮ NGUYÊN Section separation bonus
        has_legal = '=== VĂN BẢN PHÁP LUẬT ===' in context
        has_procedure = '=== THỦ TỤC HÀNH CHÍNH ===' in context
        
        separation_bonus = 0.0
        if has_legal and has_procedure:
            separation_bonus = 0.2
        elif has_legal or has_procedure:
            separation_bonus = 0.1
        
        # ✅ GIỮ NGUYÊN Content quality từ logic cũ
        quality_keywords = sum(1 for kw in ['điều', 'khoản', 'thủ tục', 'hồ sơ'] if kw in context.lower())
        quality_factor = min(quality_keywords / 4.0, 0.2)
        
        # ✨ CHỈ THÊM một chút content completeness bonus
        completeness_bonus = 0.0
        if any(word in context.lower() for word in ['gồm có', 'bao gồm', 'cụ thể', 'theo quy định']):
            completeness_bonus = 0.05
        
        final_confidence = avg_score * 0.5 + separation_bonus + quality_factor + completeness_bonus + 0.15
        return min(final_confidence, 1.0)
    
    # ✅ KEEP ALL ORIGINAL METHODS cho backward compatibility
    def _score_legal_content(self, content: str) -> float:
        """✅ Original legal scoring"""
        score = 0.0
        for indicator in self.legal_indicators:
            if indicator in content:
                score += 0.2
        return min(score, 1.0)
    
    def _score_procedure_content(self, content: str) -> float:
        """✅ Original procedure scoring"""
        score = 0.0
        for indicator in self.procedure_indicators:
            if indicator in content:
                score += 0.15
        return min(score, 1.0)
    
    def _calculate_confidence(self, all_results: List[Dict], context: str) -> float:
        """✅ Original confidence calculation"""
        if not all_results or not context:
            return 0.0
        
        # Base confidence
        avg_score = sum(r.get('score', 0.5) for r in all_results) / len(all_results)
        
        # Section separation bonus
        has_legal = '=== VĂN BẢN PHÁP LUẬT ===' in context
        has_procedure = '=== THỦ TỤC HÀNH CHÍNH ===' in context
        
        separation_bonus = 0.0
        if has_legal and has_procedure:
            separation_bonus = 0.2
        elif has_legal or has_procedure:
            separation_bonus = 0.1
        
        # Content quality
        quality_keywords = sum(1 for kw in ['điều', 'khoản', 'thủ tục', 'hồ sơ'] if kw in context.lower())
        quality_factor = min(quality_keywords / 4.0, 0.2)
        
        final_confidence = avg_score * 0.5 + separation_bonus + quality_factor + 0.2
        return min(final_confidence, 1.0)