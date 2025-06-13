# server/services/vector_rag/context_optimizer.py
"""
Context Optimizer - SỬA: Tăng cường logic phân biệt văn bản pháp luật
"""
import re
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class OptimizedContext:
    """Giữ nguyên structure"""
    context: str
    confidence_score: float
    source_summary: str
    context_type: str
    total_sources: int
    web_sources: int
    vector_sources: int

class VietnameseContextOptimizer:
    """SỬA: Nâng cấp logic phân biệt văn bản pháp luật chính xác"""
    
    def __init__(self):
        # Giữ nguyên original settings
        self.max_context_length = 6000
        self.max_sources = 12
        self.min_section_length = 15
        
        # SỬA: Nâng cấp legal indicators với domain specificity
        self.legal_indicators = [
            'điều', 'khoản', 'điểm', 'luật số', 'nghị định số', 'thông tư số',
            'theo quy định tại điều', 'căn cứ luật', 'quy định chi tiết',
            'căn cứ pháp lý', 'theo luật', 'pháp luật quy định'
        ]
        
        # THÊM: Document classification patterns
        self.document_patterns = {
            'xuat_nhap_canh_congdan': {
                'markers': ['luật xuất cảnh, nhập cảnh của công dân việt nam', 'số 49/2019', 'công dân việt nam'],
                'domain': 'xuất nhập cảnh công dân',
                'priority': 10
            },
            'xuat_nhap_canh_nuocngoai': {
                'markers': ['luật nhập cảnh, xuất cảnh, quá cảnh, cư trú của người nước ngoài', 'số 47/2014', 'người nước ngoài'],
                'domain': 'xuất nhập cảnh người nước ngoài', 
                'priority': 8
            },
            'to_tung_hinh_su': {
                'markers': ['bộ luật tố tụng hình sự', 'tố tụng hình sự', 'bị can', 'bị cáo'],
                'domain': 'tố tụng hình sự',
                'priority': 5  # Lower priority unless specifically asked
            },
            'hanh_chinh': {
                'markers': ['vi phạm hành chính', 'xử phạt hành chính'],
                'domain': 'hành chính',
                'priority': 3
            }
        }
        
        # SỬA: Enhanced procedure indicators
        self.procedure_indicators = [
            'mã thủ tục', 'tên thủ tục', 'yêu cầu - điều kiện', 'thành phần hồ sơ',
            'trình tự thực hiện', 'cách thức thực hiện', 'thời hạn giải quyết',
            'phí', 'lệ phí', 'cơ quan thực hiện', 'căn cứ pháp lý',
            'kết quả thực hiện', 'biểu mẫu', 'hồ sơ gồm',
            'điều kiện thủ tục', 'yêu cầu hồ sơ', 'cách thức nộp'
        ]
    
    def optimize_context(self, search_results: List[Dict], query_features: Any = None) -> OptimizedContext:
        """SỬA: Logic với document classification"""
        
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
        
        # 1. SỬA: Classify results với domain awareness
        legal_results, procedure_results = self._classify_results_enhanced(search_results, query_features)
        
        # 2. Build context with domain prioritization
        context = self._build_domain_aware_context(legal_results, procedure_results, query_features)
        
        # 3. Create source summary
        source_summary = self._create_source_summary(legal_results, procedure_results)
        
        # 4. Calculate confidence với domain weighting
        confidence = self._calculate_confidence_domain_aware(legal_results + procedure_results, context, query_features)
        
        # 5. Determine context type
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
    
    def _classify_results_enhanced(self, results: List[Dict], query_features: Any = None) -> tuple:
        """SỬA: Enhanced classification với domain detection"""
        legal_results = []
        procedure_results = []
        
        # Extract query intent để prioritize domain
        query_domain = self._extract_query_domain(query_features)
        
        for result in results:
            content = result.get('content', '').lower()
            metadata = result.get('metadata', {})
            content_type = metadata.get('content_type', '')
            
            # SỬA: Document domain classification
            doc_domain = self._classify_document_domain(content, metadata)
            
            # Score with domain relevance
            legal_score = self._score_legal_content_domain_aware(content, doc_domain, query_domain)
            procedure_score = self._score_procedure_content(content)
            
            # Add domain relevance bonus
            if doc_domain == query_domain:
                legal_score += 0.3  # Bonus for domain match
            
            # Classify based on enhanced scoring
            if content_type == 'legal_document' or legal_score > procedure_score:
                legal_results.append({**result, 'domain': doc_domain, 'domain_score': legal_score})
            elif content_type == 'web_procedure' or procedure_score > legal_score:
                procedure_results.append(result)
            else:
                if legal_score >= procedure_score:
                    legal_results.append({**result, 'domain': doc_domain, 'domain_score': legal_score})
                else:
                    procedure_results.append(result)
        
        # SỬA: Sort by domain relevance và score
        legal_results.sort(key=lambda x: (x.get('domain_score', 0), x.get('score', 0)), reverse=True)
        
        return legal_results[:4], procedure_results[:3]  # Tăng legal results
    
    def _classify_document_domain(self, content: str, metadata: Dict) -> str:
        """THÊM: Classify document domain"""
        content_lower = content.lower()
        
        for domain_key, domain_info in self.document_patterns.items():
            markers = domain_info['markers']
            match_count = sum(1 for marker in markers if marker in content_lower)
            
            if match_count >= 1:  # At least 1 marker match
                return domain_info['domain']
        
        return 'general'
    
    def _extract_query_domain(self, query_features: Any) -> str:
        """FIXED: Extract query domain - cross-domain cho criminal law + immigration"""
        if not query_features:
            return 'cross_domain'  # FIXED: Multi-domain query
            
        query = getattr(query_features, 'normalized_query', '').lower()
        
        # FIXED: "bị khởi tố" cần cả criminal law + immigration law
        if any(word in query for word in ['bị khởi tố', 'khởi tố', 'bị can', 'bị cáo']):
            return 'cross_domain'  # FIXED: Cần cả 2 domain
        elif 'tạm hoãn xuất cảnh' in query:
            return 'cross_domain'  # FIXED: Intersection query
        elif any(word in query for word in ['người nước ngoài', 'thị thực', 'visa']):
            return 'xuất nhập cảnh người nước ngoài'
        elif any(word in query for word in ['hộ chiếu', 'xuất cảnh', 'nhập cảnh']):
            return 'xuất nhập cảnh công dân'
        
        return 'cross_domain'  # FIXED: Default to cross-domain
    
    def _score_legal_content_domain_aware(self, content: str, doc_domain: str, query_domain: str) -> float:
        """FIXED: Legal scoring - no penalty for cross-domain queries"""
        score = 0.0
        
        # Original indicator scoring
        for indicator in self.legal_indicators:
            if indicator in content:
                score += 0.2
        
        # FIXED: Cross-domain query handling
        if query_domain == 'cross_domain':
            # BONUS for relevant domains in cross-domain queries
            if doc_domain in ['tố tụng hình sự', 'xuất nhập cảnh công dân']:
                score += 0.4  # Strong bonus for both relevant domains
            elif doc_domain == 'xuất nhập cảnh người nước ngoài':
                score += 0.2  # Moderate bonus for related domain
            
            # SPECIAL: Extra bonus for intersection content
            intersection_keywords = ['tạm hoãn xuất cảnh', 'bị khởi tố', 'xuất cảnh', 'khởi tố']
            intersection_count = sum(1 for kw in intersection_keywords if kw in content.lower())
            score += intersection_count * 0.3
            
        else:
            # Normal domain matching
            if doc_domain == query_domain:
                score += 0.4
            elif doc_domain in ['xuất nhập cảnh công dân', 'xuất nhập cảnh người nước ngoài'] and \
                query_domain in ['xuất nhập cảnh công dân', 'xuất nhập cảnh người nước ngoài']:
                score += 0.2
            
            # REMOVED: No penalty for cross-domain content anymore
        
        return min(score, 1.0)
        
    def _score_procedure_content(self, content: str) -> float:
        """Giữ nguyên procedure scoring"""
        score = 0.0
        for indicator in self.procedure_indicators:
            if indicator in content:
                score += 0.15
        return min(score, 1.0)
    
    def _build_domain_aware_context(self, legal_results: List[Dict], procedure_results: List[Dict], query_features: Any = None) -> str:
        """SỬA: Build context với domain prioritization"""
        context_parts = []
        current_length = 0
        
        # Section 1: Primary domain legal content
        if legal_results:
            legal_section = self._build_legal_section_prioritized(legal_results, query_features)
            if legal_section and len(legal_section) > 50:
                context_parts.append("=== VĂN BẢN PHÁP LUẬT ===")
                context_parts.append(legal_section)
                current_length += len(legal_section) + 30
        
        # Section 2: Procedures
        if procedure_results and current_length < self.max_context_length - 500:
            procedure_section = self._build_procedure_section(procedure_results)
            if procedure_section and len(procedure_section) > 50:
                context_parts.append("\n=== THỦ TỤC HÀNH CHÍNH ===")
                context_parts.append(procedure_section)
        
        return '\n'.join(context_parts)
    
    def _build_legal_section_prioritized(self, legal_results: List[Dict], query_features: Any = None) -> str:
        """FIXED: Build legal section - prioritize cross-domain content"""
        parts = []
        query_domain = self._extract_query_domain(query_features)
        
        if query_domain == 'cross_domain':
            # FIXED: For cross-domain queries, prioritize by content relevance
            # Group by domain but don't exclude any
            criminal_law_results = []
            immigration_law_results = []
            other_results = []
            
            for result in legal_results:
                domain = result.get('domain', 'general')
                if domain == 'tố tụng hình sự':
                    criminal_law_results.append(result)
                elif domain in ['xuất nhập cảnh công dân', 'xuất nhập cảnh người nước ngoài']:
                    immigration_law_results.append(result)
                else:
                    other_results.append(result)
            
            # FIXED: Include both criminal and immigration law
            prioritized_results = []
            
            # Add top criminal law (điều về tạm hoãn xuất cảnh)
            prioritized_results.extend(criminal_law_results[:2])
            
            # Add top immigration law (xuất cảnh regulations)
            prioritized_results.extend(immigration_law_results[:2])
            
            # Fill remaining with other relevant results
            remaining = 4 - len(prioritized_results)
            if remaining > 0:
                prioritized_results.extend(other_results[:remaining])
            
            # Build content from all prioritized results
            for result in prioritized_results[:4]:
                content = result.get('content', '').strip()
                if len(content) >= self.min_section_length:
                    if len(content) > 2500:
                        content = self._smart_truncate_with_legal_structure(content, 2500)
                    parts.append(content)
        
        else:
            # Original single-domain logic
            domain_groups = {}
            for result in legal_results:
                domain = result.get('domain', 'general')
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(result)
            
            # Prioritize query domain first
            if query_domain in domain_groups:
                primary_results = domain_groups[query_domain][:2]
                for result in primary_results:
                    content = result.get('content', '').strip()
                    if len(content) >= self.min_section_length:
                        if len(content) > 2500:
                            content = self._smart_truncate_with_legal_structure(content, 2500)
                        parts.append(content)
            
            # Add related domains
            remaining_space = 3 - len(parts)
            for domain, results in domain_groups.items():
                if domain != query_domain and remaining_space > 0:
                    for result in results[:remaining_space]:
                        content = result.get('content', '').strip()
                        if len(content) >= self.min_section_length:
                            if len(content) > 2000:
                                content = self._smart_truncate_with_legal_structure(content, 2000)
                            parts.append(content)
                            remaining_space -= 1
                            if remaining_space <= 0:
                                break
        
        return '\n\n'.join(parts)
    
    def _smart_truncate_with_legal_structure(self, content: str, max_length: int) -> str:
        """SỬA: Smart truncation keeping legal structure"""
        if len(content) <= max_length:
            return content
        
        # Try to truncate at article boundary (Điều)
        dieu_matches = list(re.finditer(r'Điều \d+[a-z]?\.', content))
        if len(dieu_matches) > 1:
            # Find last complete article within limit
            for match in reversed(dieu_matches):
                if match.start() <= max_length - 50:
                    return content[:match.start()].strip() + "\n\n[...]"
        
        # Try to truncate at paragraph boundary (khoản)
        khoan_matches = list(re.finditer(r'\n\d+\.', content))
        if khoan_matches:
            for match in reversed(khoan_matches):
                if match.start() <= max_length - 50:
                    return content[:match.start()].strip() + "\n\n[...]"
        
        # Try sentence boundary
        sentences = re.split(r'[.!?]\s+', content)
        truncated = ""
        for sentence in sentences:
            if len(truncated + sentence) + 1 <= max_length - 10:
                truncated += sentence + ". "
            else:
                break
        
        if truncated.strip():
            return truncated.strip() + "\n\n[...]"
        else:
            return content[:max_length-10] + "\n\n[...]"
    
    def _build_procedure_section(self, procedure_results: List[Dict]) -> str:
        """Giữ nguyên procedure section building"""
        parts = []
        for result in procedure_results[:3]:
            content = result.get('content', '').strip()
            if len(content) >= self.min_section_length:
                if len(content) > 1200:
                    content = self._smart_truncate(content, 1200)
                parts.append(content)
        
        return '\n\n'.join(parts)
    
    def _smart_truncate(self, content: str, max_length: int) -> str:
        """Giữ nguyên smart truncation"""
        if len(content) <= max_length:
            return content
        
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
            return content[:max_length-3] + "..."
    
    def _create_source_summary(self, legal_results: List[Dict], procedure_results: List[Dict]) -> str:
        """SỬA: Enhanced source summary với domain info"""
        sources = []
        
        for result in legal_results[:2]:
            metadata = result.get('metadata', {})
            source = metadata.get('file_name', 'Văn bản pháp luật')
            domain = result.get('domain', 'general')
            
            if domain != 'general':
                sources.append(f"LUẬT ({domain}): {source}")
            else:
                sources.append(f"LUẬT: {source}")
        
        for result in procedure_results[:2]:
            metadata = result.get('metadata', {})
            source = metadata.get('title', 'Thủ tục hành chính')
            sources.append(f"TTHC: {source}")
        
        return '; '.join(sources)
    
    def _calculate_confidence_domain_aware(self, all_results: List[Dict], context: str, query_features: Any = None) -> float:
        """FIXED: Confidence calculation cho cross-domain queries"""
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
        
        # FIXED: Cross-domain relevance bonus
        query_domain = self._extract_query_domain(query_features)
        domain_bonus = 0.0
        
        if query_domain == 'cross_domain':
            # Check for intersection content (criminal + immigration law)
            criminal_indicators = ['bị khởi tố', 'bị can', 'bị cáo', 'tố tụng hình sự']
            immigration_indicators = ['xuất cảnh', 'nhập cảnh', 'hộ chiếu', 'công dân việt nam']
            
            criminal_count = sum(1 for indicator in criminal_indicators if indicator in context.lower())
            immigration_count = sum(1 for indicator in immigration_indicators if indicator in context.lower())
            
            if criminal_count >= 1 and immigration_count >= 1:
                domain_bonus = 0.25  # Strong bonus for cross-domain content
            elif criminal_count >= 2 or immigration_count >= 2:
                domain_bonus = 0.15  # Moderate bonus for strong single domain
        
        else:
            # Original single-domain logic
            if query_domain == 'xuất nhập cảnh công dân':
                if any(marker in context.lower() for marker in ['công dân việt nam', 'luật số 49/2019']):
                    domain_bonus = 0.15
            elif query_domain == 'xuất nhập cảnh người nước ngoài':
                if any(marker in context.lower() for marker in ['người nước ngoài', 'luật số 47/2014']):
                    domain_bonus = 0.15
        
        # Legal citation accuracy bonus
        citation_bonus = 0.0
        if re.search(r'điều \d+[a-z]?\s+(?:luật|bộ luật)', context.lower()):
            citation_bonus = 0.15  # Increased for proper legal citations
        
        final_confidence = avg_score * 0.4 + separation_bonus + quality_factor + domain_bonus + citation_bonus + 0.1
        return min(final_confidence, 1.0)
    
    # Giữ nguyên các original methods để backward compatibility
    def _calculate_confidence(self, all_results: List[Dict], context: str) -> float:
        """Original confidence calculation"""
        if not all_results or not context:
            return 0.0
        
        avg_score = sum(r.get('score', 0.5) for r in all_results) / len(all_results)
        
        has_legal = '=== VĂN BẢN PHÁP LUẬT ===' in context
        has_procedure = '=== THỦ TỤC HÀNH CHÍNH ===' in context
        
        separation_bonus = 0.0
        if has_legal and has_procedure:
            separation_bonus = 0.2
        elif has_legal or has_procedure:
            separation_bonus = 0.1
        
        quality_keywords = sum(1 for kw in ['điều', 'khoản', 'thủ tục', 'hồ sơ'] if kw in context.lower())
        quality_factor = min(quality_keywords / 4.0, 0.2)
        
        final_confidence = avg_score * 0.5 + separation_bonus + quality_factor + 0.2
        return min(final_confidence, 1.0)