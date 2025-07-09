# server/services/vector_rag/reranker.py
"""
ReRanker - Fixed: Chọn đáp án CHÍNH XÁC, không phải điểm cao nhất
🎯 FIXED: Accuracy-first ranking for legal documents
📋 LOGIC: Query intent + Legal structure + Content accuracy
✅ GOAL: Chính xác > Điểm số similarity
"""
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AccuracyAnalyzer:
    """Phân tích độ chính xác thay vì similarity"""
    
    def __init__(self):
        # Patterns cho legal accuracy
        self.legal_patterns = {
            'article_direct': r'điều\s+(\d+[a-z]?)',
            'clause_direct': r'khoản\s+(\d+)',
            'point_direct': r'điểm\s+([a-z]+)',
            'procedure_indicators': [
                'thủ tục', 'hồ sơ', 'trình tự', 'quy trình', 'làm như thế nào',
                'cần chuẩn bị', 'giấy tờ', 'lệ phí', 'thời gian'
            ],
            'eligibility_indicators': [
                'được không', 'có được', 'được xuất cảnh không', 'được phép không',
                'điều kiện', 'trường hợp nào', 'ai được', 'khi nào được'
            ],
            'restriction_indicators': [
                'không được', 'bị cấm', 'tạm hoãn', 'hạn chế',
                'bị can', 'bị cáo', 'khởi tố', 'vi phạm'
            ]
        }
    
    def analyze_accuracy(self, query: str, content: str, query_features: Any = None) -> Dict[str, Any]:
        """Phân tích độ chính xác thay vì similarity"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        accuracy = {
            'intent_match': 0.0,      # Query intent khớp với content type
            'structure_match': 0.0,   # Legal structure accuracy
            'content_relevance': 0.0, # Content trả lời đúng câu hỏi
            'precision_score': 0.0,   # Overall precision
            'is_primary_answer': False # Đây có phải đáp án chính không
        }
        
        # 1. Intent matching - QUAN TRỌNG NHẤT
        accuracy['intent_match'] = self._check_intent_accuracy(query_lower, content_lower, query_features)
        
        # 2. Structure matching - Đúng điều luật
        accuracy['structure_match'] = self._check_structure_accuracy(query_lower, content_lower, query_features)
        
        # 3. Content relevance - Trả lời đúng câu hỏi
        accuracy['content_relevance'] = self._check_content_accuracy(query_lower, content_lower)
        
        # 4. Calculate precision score
        accuracy['precision_score'] = self._calculate_precision(accuracy)
        
        # 5. Determine if this is primary answer
        accuracy['is_primary_answer'] = self._is_primary_answer(accuracy, query_features)
        
        return accuracy
    
    def _check_intent_accuracy(self, query: str, content: str, query_features: Any) -> float:
        """Check if content matches query intent - MOST IMPORTANT"""
        if not query_features:
            return 0.5  # Neutral when no features
        
        intent = getattr(query_features, 'primary_intent', 'GENERAL')
        
        # DIRECT_ARTICLE intent
        if intent == 'DIRECT_ARTICLE':
            if hasattr(query_features, 'direct_article_info'):
                article_info = query_features.direct_article_info
                target_article = article_info.get('article', '')
                
                # Check if content contains target article
                if re.search(rf'điều\s+{re.escape(target_article)}[^0-9]', content):
                    return 1.0  # Perfect match
                else:
                    return 0.2  # Wrong article = low accuracy
            return 0.6
        
        # PROCEDURE intent
        elif intent == 'PROCEDURE':
            procedure_score = 0.0
            for indicator in self.legal_patterns['procedure_indicators']:
                if indicator in query and indicator in content:
                    procedure_score += 0.2
            return min(procedure_score, 1.0)
        
        # LEGAL (eligibility) intent
        elif intent == 'LEGAL':
            # Check if query asks eligibility và content answers eligibility
            query_asks_eligibility = any(ind in query for ind in self.legal_patterns['eligibility_indicators'])
            content_has_conditions = any(word in content for word in ['điều kiện', 'trường hợp', 'được', 'không được'])
            
            if query_asks_eligibility and content_has_conditions:
                return 0.9
            elif query_asks_eligibility and not content_has_conditions:
                return 0.3  # Query asks eligibility but content doesn't answer
            else:
                return 0.6
        
        return 0.5  # Default
    
    def _check_structure_accuracy(self, query: str, content: str, query_features: Any) -> float:
        """Check legal structure accuracy"""
        structure_score = 0.0
        
        # Direct article match
        query_article = re.search(r'điều\s+(\d+[a-z]?)', query)
        content_article = re.search(r'điều\s+(\d+[a-z]?)', content)
        
        if query_article and content_article:
            if query_article.group(1) == content_article.group(1):
                structure_score += 0.5  # Exact article match
            else:
                structure_score += 0.1  # Different article, lower score
        elif content_article:
            structure_score += 0.3  # Content has article structure
        
        # Clause match if specified
        query_clause = re.search(r'khoản\s+(\d+)', query)
        if query_clause:
            content_clause = re.search(r'khoản\s+(\d+)', content)
            if content_clause and query_clause.group(1) == content_clause.group(1):
                structure_score += 0.3  # Exact clause match
        
        # Legal format indicators
        if re.search(r'điều\s+\d+.*:', content):
            structure_score += 0.2  # Proper legal format
        
        return min(structure_score, 1.0)
    
    def _check_content_accuracy(self, query: str, content: str) -> float:
        """Check if content actually answers the query"""
        relevance_score = 0.0
        
        # Extract key concepts from query
        query_concepts = self._extract_concepts(query)
        content_concepts = self._extract_concepts(content)
        
        # Concept overlap
        if query_concepts:
            overlap = len(query_concepts & content_concepts) / len(query_concepts)
            relevance_score += overlap * 0.4
        
        # Specific question-answer patterns
        question_patterns = {
            'điều kiện': ['điều kiện', 'yêu cầu', 'cần phải'],
            'được không': ['được', 'không được', 'có thể', 'không thể'],
            'thủ tục': ['thủ tục', 'hồ sơ', 'giấy tờ', 'quy trình'],
            'ai': ['công dân', 'người', 'trẻ em', 'người nước ngoài'],
            'khi nào': ['khi', 'trường hợp', 'nếu', 'điều kiện']
        }
        
        for pattern, answers in question_patterns.items():
            if pattern in query:
                if any(answer in content for answer in answers):
                    relevance_score += 0.2
        
        return min(relevance_score, 1.0)
    
    def _extract_concepts(self, text: str) -> set:
        """Extract key legal concepts"""
        concepts = set()
        
        # Legal concepts
        legal_terms = [
            'xuất cảnh', 'nhập cảnh', 'hộ chiếu', 'thị thực', 'visa',
            'trẻ em', 'người nước ngoài', 'công dân việt nam',
            'bị can', 'bị cáo', 'khởi tố', 'tạm hoãn',
            'điều kiện', 'thủ tục', 'hồ sơ', 'giấy tờ'
        ]
        
        for term in legal_terms:
            if term in text:
                concepts.add(term)
        
        return concepts
    
    def _calculate_precision(self, accuracy: Dict[str, float]) -> float:
        """Calculate overall precision score"""
        # Intent matching is most important for accuracy
        weights = {
            'intent_match': 0.5,      # 50% - Most important
            'structure_match': 0.3,   # 30% - Legal structure
            'content_relevance': 0.2  # 20% - Content relevance
        }
        
        precision = (
            accuracy['intent_match'] * weights['intent_match'] +
            accuracy['structure_match'] * weights['structure_match'] +
            accuracy['content_relevance'] * weights['content_relevance']
        )
        
        return min(max(precision, 0.0), 1.0)
    
    def _is_primary_answer(self, accuracy: Dict[str, float], query_features: Any) -> bool:
        """Determine if this is the primary answer to the query"""
        # High precision threshold for primary answer
        if accuracy['precision_score'] < 0.7:
            return False
        
        # Intent must match well
        if accuracy['intent_match'] < 0.8:
            return False
        
        # For direct article queries, structure must match
        if query_features and getattr(query_features, 'primary_intent', '') == 'DIRECT_ARTICLE':
            if accuracy['structure_match'] < 0.8:
                return False
        
        return True

class ReRanker:
    """Fixed ReRanker: Accuracy-first ranking"""
    
    def __init__(self):
        self.analyzer = AccuracyAnalyzer()
        
        # Config for accuracy-first
        self.config = {
            'min_precision': 0.1,  # Minimum precision to include
            'primary_answer_threshold': 0.7,  # Threshold for primary answer
            'max_results': 8
        }
        
        # Stats
        self.stats = {
            'total_calls': 0,
            'primary_answers_found': 0,
            'accuracy_rankings': 0,
            'avg_processing_time': 0.0
        }
        
        logger.info("ReRanker initialized - ACCURACY FIRST")
    
    def rerank(self, query: str, chunks: List[Dict], context_tier: str = 'general', 
               query_features: Any = None) -> List[Dict]:
        """FIXED: Accuracy-first reranking for legal precision"""
        start_time = datetime.now()
        self.stats['total_calls'] += 1
        
        if not chunks:
            return []
        
        logger.info(f"ReRanker: accuracy-first analysis for '{query[:30]}...'")
        
        try:
            analyzed_chunks = []
            primary_answer = None
            
            for i, chunk in enumerate(chunks):
                content = chunk.get('content', '')
                original_score = chunk.get('score', 0.5)
                
                # ACCURACY analysis instead of similarity
                accuracy = self.analyzer.analyze_accuracy(query, content, query_features)
                
                # Create enhanced chunk
                enhanced_chunk = chunk.copy()
                enhanced_chunk.update({
                    'accuracy_analysis': accuracy,
                    'precision_score': accuracy['precision_score'],
                    'is_primary_answer': accuracy['is_primary_answer'],
                    'original_score': original_score,
                    'strategy': 'accuracy_first'
                })
                
                # Track primary answer
                if accuracy['is_primary_answer'] and not primary_answer:
                    primary_answer = enhanced_chunk
                    self.stats['primary_answers_found'] += 1
                
                analyzed_chunks.append(enhanced_chunk)
                
                logger.debug(f"Chunk {i+1}: precision={accuracy['precision_score']:.3f}, primary={accuracy['is_primary_answer']}")
            
            # ACCURACY-FIRST RANKING
            ranked_chunks = self._rank_by_accuracy(analyzed_chunks, primary_answer, query_features)
            
            # Filter by minimum precision
            filtered_chunks = [
                chunk for chunk in ranked_chunks 
                if chunk['precision_score'] >= self.config['min_precision']
            ]
            
            # Take top results
            final_results = filtered_chunks[:self.config['max_results']]
            
            # Format for ContextOptimizer
            formatted_results = []
            for result in final_results:
                formatted_result = {
                    'content': result['content'],
                    'metadata': result.get('metadata', {}),
                    'precision_score': result['precision_score'],
                    'is_primary_answer': result['is_primary_answer'],
                    'accuracy_analysis': result['accuracy_analysis'],
                    'strategy': result['strategy']
                }
                formatted_results.append(formatted_result)
            
            # Track accuracy ranking
            if final_results:
                self.stats['accuracy_rankings'] += 1
            
            # Update stats
            processing_time = (datetime.now() - start_time).total_seconds()
            self._update_stats(processing_time)
            
            if final_results:
                logger.info(f"ReRanker: primary_answer={bool(primary_answer)}, top_precision={final_results[0]['precision_score']:.3f}")
            else:
                logger.info(f"ReRanker: primary_answer={bool(primary_answer)}, no results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Accuracy reranking failed: {e}")
            return chunks[:self.config['max_results']]
    
    def _rank_by_accuracy(self, chunks: List[Dict], primary_answer: Optional[Dict], query_features: Any) -> List[Dict]:
        """Rank by accuracy, not similarity - WITH PROCEDURE PRIORITY BOOST"""
        
        # STEP 1: Put primary answer first if found
        if primary_answer:
            other_chunks = [c for c in chunks if c != primary_answer]
            ranked = [primary_answer] + other_chunks
        else:
            ranked = chunks
        
        # 🔧 NEW STEP 1.5: Apply procedure priority boost = +0.3 (ROADMAP TASK 2.2)
        for chunk in ranked:
            if self._is_procedure_content(chunk):
                chunk['precision_score'] += 0.3  # ROADMAP REQUIREMENT: +0.3 boost
                chunk['procedure_boosted'] = True
                logger.debug(f"   🎯 Procedure boost applied: +0.3")
            else:
                chunk['procedure_boosted'] = False
        
        # STEP 2: Sort by precision score (now includes procedure boost)
        def accuracy_sort_key(chunk):
            precision = chunk['precision_score']
            is_primary = chunk['is_primary_answer']
            intent_match = chunk['accuracy_analysis']['intent_match']
            
            # Primary answers get highest priority
            if is_primary:
                return (1.0, precision, intent_match)
            else:
                return (0.0, precision, intent_match)
        
        ranked.sort(key=accuracy_sort_key, reverse=True)
        
        # STEP 3: Apply query-specific adjustments
        if query_features:
            ranked = self._apply_query_specific_ranking(ranked, query_features)
        
        return ranked
    
    def _apply_query_specific_ranking(self, chunks: List[Dict], query_features: Any) -> List[Dict]:
        """Apply query-specific ranking adjustments"""
        intent = getattr(query_features, 'primary_intent', 'GENERAL')
        
        if intent == 'DIRECT_ARTICLE':
            # For direct article queries, prioritize exact article matches
            article_matches = []
            others = []
            
            for chunk in chunks:
                structure_match = chunk['accuracy_analysis']['structure_match']
                if structure_match >= 0.8:  # High structure match
                    article_matches.append(chunk)
                else:
                    others.append(chunk)
            
            return article_matches + others
        
        elif intent == 'PROCEDURE':
            # For procedure queries, prioritize content with procedure info
            procedure_chunks = []
            others = []
            
            for chunk in chunks:
                content = chunk['content'].lower()
                has_procedure_info = any(term in content for term in ['thủ tục', 'hồ sơ', 'quy trình', 'trình tự'])
                
                if has_procedure_info:
                    procedure_chunks.append(chunk)
                else:
                    others.append(chunk)
            
            return procedure_chunks + others
        
        return chunks  # No specific adjustments

    def _is_procedure_content(self, chunk: Dict) -> bool:
        """🎯 ROADMAP TASK 2.2: Detect procedure content để boost score"""
        content = chunk.get('content', '').lower()
        metadata = chunk.get('metadata', {})
        
        # Method 1: Check metadata field_type (most reliable)
        if metadata.get('field_type'):
            return True
        
        # Method 2: Check for procedure indicators in content
        procedure_indicators = [
            'thủ tục', 'hồ sơ', 'trình tự thực hiện', 'quy trình', 
            'lệ phí', 'thời hạn giải quyết', 'cách thức thực hiện',
            'thành phần hồ sơ', 'giấy tờ cần thiết', 'điều kiện'
        ]
        
        # Count procedure indicators
        indicator_count = sum(1 for indicator in procedure_indicators if indicator in content)
        
        # Method 3: Check content structure (table-like format common in procedures)
        has_structured_format = bool(re.search(r'(?:tên|mã|cơ quan|lĩnh vực|cách thức).*:', content))
        
        # Decision logic
        if indicator_count >= 2:  # Has multiple procedure indicators
            return True
        elif indicator_count >= 1 and has_structured_format:  # Has indicator + structure
            return True
        elif 'thủ tục hành chính' in content:  # Explicit procedure mention
            return True
        
        return False
    
    def _update_stats(self, processing_time: float):
        """Update stats"""
        total = self.stats['total_calls']
        current_avg = self.stats['avg_processing_time']
        self.stats['avg_processing_time'] = (current_avg * (total - 1) + processing_time) / total
    
    def get_stats(self) -> Dict[str, Any]:
        """Get accuracy-focused stats"""
        total = self.stats['total_calls']
        primary_rate = self.stats['primary_answers_found'] / total if total > 0 else 0
        accuracy_rate = self.stats['accuracy_rankings'] / total if total > 0 else 0
        
        return {
            'version': 'Accuracy-First ReRanker v2.0',
            'approach': 'ACCURACY > SIMILARITY',
            'performance': {
                'total_calls': total,
                'primary_answer_rate': round(primary_rate, 3),
                'accuracy_ranking_rate': round(accuracy_rate, 3),
                'avg_processing_time': round(self.stats['avg_processing_time'], 3)
            },
            'accuracy_features': {
                'intent_matching': True,
                'structure_matching': True,
                'content_relevance': True,
                'primary_answer_detection': True,
                'precision_scoring': True
            },
            'quality_metrics': {
                'min_precision_threshold': self.config['min_precision'],
                'primary_answer_threshold': self.config['primary_answer_threshold'],
                'legal_accuracy_focus': True
            }
        }
    
    def reset_stats(self):
        """Reset stats"""
        self.stats = {
            'total_calls': 0,
            'primary_answers_found': 0,
            'accuracy_rankings': 0,
            'avg_processing_time': 0.0
        }
        logger.info("Accuracy-First ReRanker statistics reset")