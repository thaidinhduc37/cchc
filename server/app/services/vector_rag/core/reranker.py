# server/services/vector_rag/reranker.py
"""
ReRanker for Legal RAG Chatbot - Q&A Optimized
Focus: Prioritize question-answer patterns over pure legal structure
"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger(__name__)

class AccuracyAnalyzer:
    """Analyze chunk accuracy with Q&A pattern priority"""
    
    def __init__(self):
        self.stats = {
            'total_analyses': 0,
            'qa_patterns_found': 0,
            'semantic_matches': 0
        }

    def analyze_accuracy(self, query: str, content: str, query_features: Any) -> Dict[str, Any]:
        """Main analysis with Q&A focus"""
        self.stats['total_analyses'] += 1
        
        accuracy = {
            'qa_similarity': 0.0,
            'content_match': 0.0,
            'intent_match': 0.0,
            'precision_score': 0.0,
            'is_primary_answer': False
        }
        
        # Q&A pattern matching
        accuracy['qa_similarity'] = self._calculate_qa_similarity(query, content)
        
        # Content relevance
        accuracy['content_match'] = self._calculate_content_match(query, content)
        
        # Intent matching
        accuracy['intent_match'] = self._calculate_intent_match(query, content, query_features)
        
        # Final score: Heavy weight on Q&A similarity
        accuracy['precision_score'] = (
            0.5 * accuracy['qa_similarity'] +      # Q&A patterns most important
            0.3 * accuracy['content_match'] +      # Content relevance
            0.2 * accuracy['intent_match']         # Intent matching
        )
        
        accuracy['is_primary_answer'] = accuracy['precision_score'] > 0.6
        
        return accuracy
    
    def _calculate_qa_similarity(self, query: str, content: str) -> float:
        """Calculate Q&A pattern similarity"""
        query_lower = query.lower()
        content_lower = content.lower()
        score = 0.0
        
        # Check for structured Q&A patterns
        qa_patterns = [
            r'(?:câu hỏi|hỏi):\s*(.*?)\n*(?:trả lời|đáp):\s*(.*?)(?=(?:câu hỏi|hỏi):|\Z)',
            r'^\s*\d+\.\s*(.*?)\?\s*\n+(.*?)(?=^\s*\d+\.|\Z)'
        ]
        
        for pattern in qa_patterns:
            matches = re.findall(pattern, content_lower, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            if matches:
                self.stats['qa_patterns_found'] += 1
                for match in matches:
                    if len(match) >= 2:  # Question and answer parts
                        question = match[0].strip()
                        answer = match[1].strip()
                        
                        if question and answer:
                            # Semantic similarity between query and question
                            similarity = self._calculate_text_similarity(query_lower, question)
                            if similarity > 0.3:
                                score += min(similarity * 1.5, 1.0)
                                self.stats['semantic_matches'] += 1
                            
                            # Boost for good answer length
                            if len(answer) > 50:
                                score += 0.3
                break
        
        # Question-answer indicators
        question_indicators = ['ai được', 'có được', 'được không', 'làm thế nào', 'cần gì', 'thủ tục', 'điều kiện', 'bao lâu', 'ở đâu']
        answer_indicators = ['theo quy định', 'căn cứ', 'điều', 'được cấp', 'phải có', 'bao gồm', 'thủ tục thực hiện']
        
        has_query_question = any(indicator in query_lower for indicator in question_indicators)
        has_content_answer = any(indicator in content_lower for indicator in answer_indicators)
        
        if has_query_question and has_content_answer:
            score += 0.4
        
        return min(score, 1.0)
    
    def _calculate_content_match(self, query: str, content: str) -> float:
        """Calculate content relevance"""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        # Word overlap
        common_words = query_words & content_words
        overlap_score = len(common_words) / len(query_words)
        
        # Key concept matching
        legal_concepts = self._extract_legal_concepts(query, content)
        concept_score = len(legal_concepts) * 0.1
        
        return min(overlap_score + concept_score, 1.0)
    
    def _extract_legal_concepts(self, query: str, content: str) -> set:
        """Extract matching legal concepts"""
        concepts = set()
        legal_terms = [
            'xuất cảnh', 'nhập cảnh', 'hộ chiếu', 'thị thực', 'visa',
            'trẻ em', 'người nước ngoài', 'công dân việt nam',
            'điều kiện', 'thủ tục', 'hồ sơ', 'giấy tờ'
        ]
        
        query_lower = query.lower()
        content_lower = content.lower()
        
        for term in legal_terms:
            if term in query_lower and term in content_lower:
                concepts.add(term)
        
        return concepts
    
    def _calculate_intent_match(self, query: str, content: str, query_features: Any) -> float:
        """Calculate intent matching"""
        if not query_features:
            return 0.5
        
        intent = getattr(query_features, 'primary_intent', 'GENERAL')
        content_lower = content.lower()
        
        intent_scores = {
            'DIRECT_ARTICLE': 0.8 if 'điều' in content_lower else 0.3,
            'PROCEDURE': 0.8 if any(term in content_lower for term in ['thủ tục', 'hồ sơ']) else 0.4,
            'CONSULTATION': 0.8 if any(term in content_lower for term in ['điều kiện', 'được phép']) else 0.4,
            'GENERAL': 0.5
        }
        
        return intent_scores.get(intent, 0.5)
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity calculation"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0

class ReRanker:
    """Enhanced ReRanker with Q&A priority"""
    
    def __init__(self):
        self.analyzer = AccuracyAnalyzer()
        self.config = {
            'min_precision': 0.2,
            'max_results': 8
        }
        self.stats = {
            'total_calls': 0,
            'qa_prioritized': 0,
            'avg_processing_time': 0.0
        }

    async def rerank(self, query: str, chunks: List[Dict], context_tier: str = 'general', 
                    query_features: Any = None, conversation_history: List[Dict] = None) -> List[Dict]:
        """Rerank chunks with Q&A priority"""
        start_time = datetime.now()
        self.stats['total_calls'] += 1

        if not chunks:
            return []

        # Light filtering - keep most chunks
        filtered_chunks = self._light_filter(query, chunks, query_features)
        
        # Analyze all chunks
        analyzed_chunks = []
        for chunk in filtered_chunks:
            accuracy = self.analyzer.analyze_accuracy(query, chunk.get('content', ''), query_features)
            
            enhanced_chunk = {
                'content': chunk.get('content', ''),
                'metadata': chunk.get('metadata', {}),
                'score': chunk.get('score', 0.0),
                'precision_score': accuracy['precision_score'],
                'is_primary_answer': accuracy['is_primary_answer'],
                'accuracy_analysis': accuracy,
                'qa_boosted': accuracy['qa_similarity'] > 0.5
            }
            
            analyzed_chunks.append(enhanced_chunk)
        
        # Sort by precision score
        analyzed_chunks.sort(key=lambda x: x['precision_score'], reverse=True)
        
        # Apply threshold and limit results
        final_results = []
        for chunk in analyzed_chunks:
            if chunk['precision_score'] >= self.config['min_precision']:
                final_results.append(chunk)
            
            if len(final_results) >= self.config['max_results']:
                break
        
        # Guarantee at least 3 results
        if len(final_results) < 3 and analyzed_chunks:
            final_results = analyzed_chunks[:3]
        
        # Update stats
        qa_boosted_count = sum(1 for chunk in final_results if chunk.get('qa_boosted', False))
        if qa_boosted_count > 0:
            self.stats['qa_prioritized'] += 1
        
        processing_time = (datetime.now() - start_time).total_seconds()
        self.stats['avg_processing_time'] = (
            (self.stats['avg_processing_time'] * (self.stats['total_calls'] - 1) + processing_time)
            / self.stats['total_calls']
        )
        
        logger.info(f"ReRanker: {len(final_results)} results, {qa_boosted_count} Q&A boosted, time: {processing_time:.2f}s")
        
        return final_results
    
    def _light_filter(self, query: str, chunks: List[Dict], query_features: Any) -> List[Dict]:
        """Light filtering to keep most relevant chunks"""
        if not chunks:
            return []
        
        intent = getattr(query_features, 'primary_intent', 'GENERAL') if query_features else 'GENERAL'
        
        # Only filter for direct article queries
        if intent == 'DIRECT_ARTICLE':
            query_article = re.search(r'điều\s+(\d+)', query.lower())
            if query_article:
                target_article = query_article.group(1)
                
                filtered = []
                for chunk in chunks:
                    content = chunk.get('content', '').lower()
                    metadata = chunk.get('metadata', {})
                    law_unit = metadata.get('law_unit', '')
                    
                    # Keep if related to target article
                    if (f'điều {target_article}' in content or 
                        law_unit.startswith(target_article) or
                        'điều' in content):
                        filtered.append(chunk)
                
                if len(filtered) >= 3:
                    return filtered
        
        # For other intents or insufficient filtering, keep all
        return chunks
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reranker statistics"""
        total = self.stats['total_calls']
        return {
            'version': 'Q&A Optimized ReRanker v1.0',
            'approach': 'Q&A patterns > content match > intent match',
            'performance': {
                'total_calls': total,
                'qa_prioritized_rate': round(self.stats['qa_prioritized'] / max(total, 1), 3),
                'avg_processing_time': round(self.stats['avg_processing_time'], 3)
            },
            'analyzer_stats': self.analyzer.stats,
            'features': [
                'Q&A pattern detection and matching',
                'Semantic similarity for question pairs',
                'Light filtering preserves relevant content',
                'Guaranteed minimum 3 results',
                'Fast processing with simple logic'
            ]
        }

def create_reranker() -> ReRanker:
    """Create ReRanker instance"""
    return ReRanker()