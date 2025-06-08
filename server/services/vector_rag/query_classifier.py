# server/services/vector_rag/query_classifier.py
"""
Query Classifier - SỬA LOGIC: Thêm query normalization
"""
import re
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
import logging
from services.vector_rag.rag_config import XUATNHAPCANH_WEB_PROCEDURES

logger = logging.getLogger(__name__)

@dataclass
class QueryFeatures:
    """Query features với normalization"""
    primary_intent: str = "GENERAL"
    confidence: float = 0.0
    search_strategy: str = "hybrid"
    legal_articles: List[str] = None
    procedure_entities: List[str] = None
    has_specific_article: bool = False
    has_procedure_request: bool = False
    enhanced_keywords: List[str] = None
    
    # SỬA LOGIC: Thêm normalized query
    original_query: str = ""
    normalized_query: str = ""
    extracted_entities: List[str] = None
    context_needed: bool = False
    
    def __post_init__(self):
        for field in ['legal_articles', 'procedure_entities', 'enhanced_keywords', 'extracted_entities']:
            if getattr(self, field) is None:
                setattr(self, field, [])

class VietnameseQueryClassifier:
    """Query Classifier với normalization logic"""
    
    def __init__(self):
        # Core intents
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
        
        # SỬA LOGIC: Entity mapping cho normalization
        self.entity_mapping = {
            'hộ chiếu': ['ho chieu', 'passport', 'hc'],
            'thị thực': ['thi thuc', 'visa', 'tt'],  
            'tạm trú': ['tam tru', 'temporary residence'],
            'thường trú': ['thuong tru', 'permanent residence'],
            'trẻ em': ['tre em', 'children', 'child', 'bé', 'con'],
            'lệ phí': ['le phi', 'phí', 'chi phí', 'fee'],
            'hồ sơ': ['ho so', 'giấy tờ', 'documents'],
            'thời gian': ['thoi gian', 'bao lâu', 'mất bao nhiêu'],
            'cơ quan': ['co quan', 'ở đâu', 'nơi nào']
        }
        
        # Incomplete patterns cần context
        self.incomplete_patterns = [
            r'^(còn|thế còn|vậy|vậy thì)',
            r'^(làm sao|thế nào)(?!\s+để)',
            r'^(có|được không)',
            r'^(bao nhiêu|mấy|bao lâu)', 
        ]
        
        # Legal patterns
        self.legal_patterns = {
            'article': r'điều\s+(\d+[a-z]?)',
            'paragraph': r'khoản\s+(\d+)',
            'point': r'điểm\s+([a-z]+)'
        }
        
        # Domain entities
        self.domain_entities = [
            'hộ chiếu', 'thị thực', 'tạm trú', 'thường trú', 
            'xuất cảnh', 'nhập cảnh', 'trẻ em', 'lệ phí'
        ]
        
        # Procedures
        self.procedures = XUATNHAPCANH_WEB_PROCEDURES
    
    def classify(self, question: str, chat_history: List[str] = None) -> QueryFeatures:
        """SỬA LOGIC: Classify với normalization"""
        original_question = question.strip()
        
        # 1. Normalize query trước
        normalized_question = self._normalize_query(original_question, chat_history)
        
        # 2. Extract entities từ normalized query
        extracted_entities = self._extract_entities(normalized_question)
        
        # 3. Extract legal references
        legal_refs = self._extract_legal_refs(normalized_question)
        
        # 4. Detect intent
        intent, confidence = self._detect_intent(normalized_question, legal_refs)
        
        # 5. Match procedures
        procedure_entities = self._match_procedures(normalized_question)
        
        # 6. Generate enhanced keywords
        enhanced_keywords = self._generate_enhanced_keywords(normalized_question, extracted_entities)
        
        # 7. Determine search strategy
        search_strategy = self._get_search_strategy(intent, legal_refs, procedure_entities)
        
        # 8. Check if context was needed
        context_needed = len(normalized_question) > len(original_question)
        
        features = QueryFeatures(
            original_query=original_question,
            normalized_query=normalized_question,
            primary_intent=intent,
            confidence=confidence,
            search_strategy=search_strategy,
            legal_articles=legal_refs,
            procedure_entities=procedure_entities,
            has_specific_article=len(legal_refs) > 0,
            has_procedure_request=len(procedure_entities) > 0,
            enhanced_keywords=enhanced_keywords,
            extracted_entities=extracted_entities,
            context_needed=context_needed
        )
        
        logger.info(f"🎯 Classified: {intent} (conf: {confidence:.2f}) | Normalized: {context_needed}")
        return features
    
    def _normalize_query(self, query: str, chat_history: List[str] = None) -> str:
        """SỬA LOGIC: Normalize câu hỏi"""
        query_lower = query.lower().strip()
        
        # Check if needs context
        needs_context = self._needs_context(query_lower)
        
        # Add context from history if needed
        if needs_context and chat_history:
            enhanced_query = self._add_context_from_history(query, chat_history)
        else:
            enhanced_query = query
        
        # Normalize entities
        normalized = self._normalize_entities(enhanced_query)
        
        # Make standalone if incomplete
        if self._is_incomplete_question(normalized.lower()):
            normalized = self._make_standalone(normalized)
        
        return normalized
    
    def _needs_context(self, query: str) -> bool:
        """Check if query needs context"""
        for pattern in self.incomplete_patterns:
            if re.match(pattern, query):
                return True
        
        # Very short and vague
        if len(query.split()) <= 3 and any(word in query for word in ['gì', 'sao', 'nào']):
            return True
        
        return False
    
    def _add_context_from_history(self, query: str, history: List[str]) -> str:
        """Add context from chat history"""
        if not history:
            return query
        
        # Get entities from recent history
        recent_entities = set()
        for prev_query in history[-3:]:
            for entity in self.domain_entities:
                if entity in prev_query.lower():
                    recent_entities.add(entity)
        
        if recent_entities:
            main_entity = list(recent_entities)[0]
            query_lower = query.lower()
            
            if query_lower.startswith('còn'):
                return f"{main_entity} {query}"
            elif query_lower.startswith('thế'):
                return f"Thế {main_entity} {query[3:]}"
            else:
                return f"{main_entity} {query}"
        
        return query
    
    def _normalize_entities(self, query: str) -> str:
        """Normalize entities in query"""
        normalized = query.lower()
        
        # Replace variants with standard forms
        for standard, variants in self.entity_mapping.items():
            for variant in variants:
                if variant in normalized:
                    normalized = normalized.replace(variant, standard)
        
        return normalized
    
    def _is_incomplete_question(self, query: str) -> bool:
        """Check if question is incomplete"""
        return len(query.split()) <= 4 and not any(entity in query for entity in self.domain_entities)
    
    def _make_standalone(self, query: str) -> str:
        """Make question standalone"""
        if 'làm' in query and 'thủ tục' not in query:
            return f"Thủ tục {query}"
        
        if any(word in query for word in ['điều kiện', 'cần gì']):
            return f"Điều kiện {query}"
        
        return query
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract entities from query"""
        entities = []
        query_lower = query.lower()
        
        for entity in self.domain_entities:
            if entity in query_lower:
                entities.append(entity)
        
        return entities
    
    def _extract_legal_refs(self, query: str) -> List[str]:
        """Extract legal references"""
        legal_refs = []
        
        for ref_type, pattern in self.legal_patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            for match in matches:
                if ref_type == 'article':
                    legal_refs.append(f"Điều {match}")
                elif ref_type == 'paragraph':
                    legal_refs.append(f"Khoản {match}")
                elif ref_type == 'point':
                    legal_refs.append(f"Điểm {match}")
        
        return legal_refs
    
    def _detect_intent(self, query: str, legal_refs: List[str]) -> Tuple[str, float]:
        """Detect intent"""
        if legal_refs:
            return 'LEGAL', 0.9
        
        query_lower = query.lower()
        intent_scores = {}
        
        for intent, config in self.core_intents.items():
            if not config['keywords']:
                intent_scores[intent] = 0.3
                continue
            
            matches = sum(1 for kw in config['keywords'] if kw in query_lower)
            if matches > 0:
                score = min((matches / len(config['keywords'])) * config['weight'], 0.95)
                intent_scores[intent] = score
        
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            best_score = intent_scores[best_intent]
            
            if best_score >= 0.2:
                return best_intent, best_score
        
        return 'GENERAL', 0.4
    
    def _match_procedures(self, query: str) -> List[str]:
        """Match procedures"""
        query_words = set(query.lower().split())
        matched = []
        
        for proc_name, code in self.procedures.items():
            proc_words = set(proc_name.lower().split())
            intersection = query_words & proc_words
            
            if len(intersection) >= 2:
                score = len(intersection) / len(proc_words)
                if score > 0.3:
                    matched.append(f"procedure_{code}")
        
        return matched
    
    def _generate_enhanced_keywords(self, query: str, entities: List[str]) -> List[str]:
        """Generate enhanced keywords"""
        keywords = set(re.findall(r'\b\w{3,}\b', query.lower()))
        keywords.update(entities)
        
        # Add variants for entities
        for entity in entities:
            if entity in self.entity_mapping:
                keywords.update(self.entity_mapping[entity][:2])
        
        # Remove stop words
        stop_words = {'các', 'của', 'và', 'có', 'được', 'cho', 'với', 'như', 'này', 'đó'}
        keywords = keywords - stop_words
        
        return list(keywords)
    
    def _get_search_strategy(self, intent: str, legal_refs: List[str], procedure_entities: List[str]) -> str:
        """Determine search strategy"""
        if intent == 'LEGAL' or legal_refs:
            return 'vector_priority'
        elif intent == 'PROCEDURE' or procedure_entities:
            return 'web_priority'
        else:
            return 'hybrid'
    
    def format_query_for_vector(self, question: str, features: QueryFeatures) -> str:
        """Format query for vector search - use normalized version"""
        if features.has_specific_article:
            return features.normalized_query
        
        # Build enhanced query from normalized + entities
        parts = [features.normalized_query]
        parts.extend(features.legal_articles[:2])
        parts.extend([e for e in features.extracted_entities if not e.startswith('procedure_')])
        
        enhanced = ' '.join(parts)
        return re.sub(r'\s+', ' ', enhanced).strip()[:150]
    
    def get_search_config(self, features: QueryFeatures) -> Dict[str, Any]:
        """Get search configuration"""
        base_config = {
            'vector_k': 5,
            'web_k': 3,
            'similarity_threshold': 0.15
        }
        
        if features.search_strategy == 'vector_priority':
            base_config.update({'vector_k': 7, 'web_k': 2})
        elif features.search_strategy == 'web_priority':
            base_config.update({'vector_k': 3, 'web_k': 5})
        
        return base_config