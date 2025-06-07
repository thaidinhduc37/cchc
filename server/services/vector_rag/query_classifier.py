# server/services/vector_rag/query_classifier.py
"""
Query Classifier - OPTIMIZED & CONCISE (3 core intents)
"""
import re
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import logging
from services.vector_rag.rag_config import XUATNHAPCANH_WEB_PROCEDURES

logger = logging.getLogger(__name__)

@dataclass
class QueryFeatures:
    """Simplified query features"""
    primary_intent: str = "GENERAL"
    confidence: float = 0.0
    search_strategy: str = "hybrid"
    legal_articles: List[str] = None
    procedure_entities: List[str] = None
    has_specific_article: bool = False
    has_procedure_request: bool = False
    enhanced_keywords: List[str] = None
    
    def __post_init__(self):
        for field in ['legal_articles', 'procedure_entities', 'enhanced_keywords']:
            if getattr(self, field) is None:
                setattr(self, field, [])

class VietnameseQueryClassifier:
    """Simplified Query Classifier - 3 core intents only"""
    
    def __init__(self):
        # 3 core intents only
        self.core_intents = {
            'LEGAL': {
                'keywords': ['điều', 'khoản', 'điểm', 'luật', 'nghị định', 'thông tư', 'quy định', 'theo'],
                'weight': 0.9
            },
            'PROCEDURE': {
                'keywords': ['thủ tục', 'hồ sơ', 'cấp', 'làm', 'xin', 'nộp', 'trình tự', 'quy trình', 'bước'],
                'weight': 0.8
            },
            'GENERAL': {
                'keywords': [],
                'weight': 0.5
            }
        }
        
        # Simple patterns
        self.legal_patterns = {
            'article': r'điều\s+(\d+[a-z]?)',
            'paragraph': r'khoản\s+(\d+)',
            'point': r'điểm\s+([a-z]+)'
        }
        
        # Domain entities
        self.domain_entities = [
            'hộ chiếu', 'passport', 'thị thực', 'visa',
            'tạm trú', 'thường trú', 'xuất cảnh', 'nhập cảnh'
        ]
        
        # Known procedures
        self.procedures = XUATNHAPCANH_WEB_PROCEDURES
    
    def classify(self, question: str) -> QueryFeatures:
        """Classify query - simplified"""
        question_lower = question.lower().strip()
        features = QueryFeatures()
        
        # 1. Extract legal references
        self._extract_legal_refs(question_lower, features)
        
        # 2. Detect intent (3 core types only)
        intent, confidence = self._detect_intent(question_lower, features)
        features.primary_intent = intent
        features.confidence = confidence
        
        # 3. Extract domain entities
        self._extract_entities(question_lower, features)
        
        # 4. Match procedures
        self._match_procedures(question_lower, features)
        
        # 5. Determine search strategy
        features.search_strategy = self._get_search_strategy(features)
        
        # 6. Generate keywords
        features.enhanced_keywords = self._generate_keywords(question_lower, features)
        
        logger.info(f"🎯 Classified: {features.primary_intent} (conf: {features.confidence:.2f})")
        return features
    
    def _extract_legal_refs(self, question: str, features: QueryFeatures):
        """Extract legal references"""
        # Extract articles
        for match in re.finditer(self.legal_patterns['article'], question):
            article_ref = f"Điều {match.group(1)}"
            features.legal_articles.append(article_ref)
            features.has_specific_article = True
        
        # Extract paragraphs
        for match in re.finditer(self.legal_patterns['paragraph'], question):
            para_ref = f"Khoản {match.group(1)}"
            features.legal_articles.append(para_ref)
            features.has_specific_article = True
    
    def _detect_intent(self, question: str, features: QueryFeatures) -> Tuple[str, float]:
        """Detect intent from 3 core types"""
        # If has specific legal article → LEGAL
        if features.has_specific_article:
            return 'LEGAL', 0.9
        
        # Score each intent
        intent_scores = {}
        
        for intent, config in self.core_intents.items():
            if not config['keywords']:  # GENERAL
                intent_scores[intent] = 0.3
                continue
            
            # Count keyword matches
            matches = sum(1 for kw in config['keywords'] if kw in question)
            
            if matches > 0:
                # Simple scoring
                score = min((matches / len(config['keywords'])) * config['weight'], 0.95)
                intent_scores[intent] = score
        
        # Get best intent
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            best_score = intent_scores[best_intent]
            
            # Minimum threshold
            if best_score >= 0.2:
                return best_intent, best_score
        
        return 'GENERAL', 0.4
    
    def _extract_entities(self, question: str, features: QueryFeatures):
        """Extract domain entities"""
        for entity in self.domain_entities:
            if entity in question:
                features.procedure_entities.append(entity)
                features.has_procedure_request = True
    
    def _match_procedures(self, question: str, features: QueryFeatures):
        """Match known procedures"""
        question_words = set(question.split())
        
        for proc_name, code in self.procedures.items():
            proc_words = set(proc_name.lower().split())
            
            # Simple intersection scoring
            intersection = question_words & proc_words
            if len(intersection) >= 2:  # At least 2 matching words
                score = len(intersection) / len(proc_words)
                if score > 0.3:
                    features.procedure_entities.append(f"procedure_{code}")
                    features.has_procedure_request = True
    
    def _get_search_strategy(self, features: QueryFeatures) -> str:
        """Determine search strategy"""
        if features.primary_intent == 'LEGAL' or features.has_specific_article:
            return 'vector_priority'
        elif features.primary_intent == 'PROCEDURE':
            return 'web_priority'
        else:
            return 'hybrid'
    
    def _generate_keywords(self, question: str, features: QueryFeatures) -> List[str]:
        """Generate enhanced keywords"""
        keywords = set(re.findall(r'\b\w{3,}\b', question))
        
        # Add legal articles
        for article in features.legal_articles:
            keywords.update(article.lower().split())
        
        # Add domain entities (exclude procedure codes)
        for entity in features.procedure_entities:
            if not entity.startswith('procedure_'):
                keywords.add(entity)
        
        # Remove common stop words
        stop_words = {'các', 'của', 'và', 'có', 'được', 'cho', 'với', 'như', 'này', 'đó'}
        keywords = keywords - stop_words
        
        return list(keywords)
    
    def format_query_for_vector(self, question: str, features: QueryFeatures) -> str:
        """Format query for vector search"""
        if features.has_specific_article:
            return question
        
        # Build enhanced query
        parts = [question]
        
        # Add legal articles
        parts.extend(features.legal_articles[:2])
        
        # Add relevant entities
        relevant_entities = [e for e in features.procedure_entities if not e.startswith('procedure_')]
        parts.extend(relevant_entities[:2])
        
        enhanced = ' '.join(parts)
        return re.sub(r'\s+', ' ', enhanced).strip()[:150]
    
    def get_search_config(self, features: QueryFeatures) -> Dict[str, Any]:
        """Get search configuration"""
        base_config = {
            'vector_k': 5,
            'web_k': 3,
            'similarity_threshold': 0.15
        }
        
        # Adjust based on strategy
        if features.search_strategy == 'vector_priority':
            base_config.update({'vector_k': 7, 'web_k': 2})
        elif features.search_strategy == 'web_priority':
            base_config.update({'vector_k': 3, 'web_k': 5})
        
        return base_config

# Alias
QueryClassifier = VietnameseQueryClassifier