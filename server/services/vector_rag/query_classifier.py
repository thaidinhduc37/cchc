# # server/services/vector_rag/query_classifier.py - FINAL VERSION
# """
# Query Classifier - Phân tích rõ ý định + yêu cầu công dân để Vector tìm đúng quy định
# """
# import re
# from typing import Dict, List, Tuple, Optional, Any
# from dataclasses import dataclass
# from datetime import datetime
# import logging

# logger = logging.getLogger(__name__)

# @dataclass
# class QueryFeatures:
#     """Thông tin để Vector tìm đúng quy định"""
#     original_query: str
#     primary_intent: str        # DIRECT_ARTICLE, LEGAL_ADVISORY, PROCEDURE
#     subject_type: str
#     confidence: float
    
#     # Ý định công dân
#     needs_conclusion: bool = False      # Cần kết luận ĐƯỢC/KHÔNG/TÙY TRƯỜNG HỢP
#     has_direct_article: bool = False    # Hỏi điều luật cụ thể
#     is_followup: bool = False
    
#     # Yêu cầu cụ thể
#     age_constraint: Optional[str] = None
#     legal_status: Optional[str] = None
#     document_type: Optional[str] = None
#     purpose: Optional[str] = None
    
#     # Thông tin để Vector search
#     enhanced_keywords: List[str] = None
#     direct_article_info: Optional[Dict] = None
#     focus_keywords: List[str] = None
#     domains: List[str] = None
    
#     def __post_init__(self):
#         if self.enhanced_keywords is None:
#             self.enhanced_keywords = []
#         if self.focus_keywords is None:
#             self.focus_keywords = []
#         if self.domains is None:
#             self.domains = []

# class ConclusionDetector:
#     """🔧 FIXED: Better Vietnamese legal question detection"""
    
#     def __init__(self):
#         self.conclusion_patterns = [
#             # 🔧 ENHANCED: More specific patterns
#             r'(?:tôi|mình|em|anh|chị).*(?:có\s+được|được\s+phép|có\s+thể).*(?:không|hay\s+không)',
#             r'(?:bị|đang).*(?:khởi\s+tố|truy\s+cứu|điều\s+tra).*(?:có.*không|được.*không)',
#             r'(?:trẻ\s+em|dưới\s+14|chưa\s+thành\s+niên).*(?:có\s+được|được\s+phép|có\s+thể).*không',
#             r'(?:hết\s+hạn|quá\s+hạn|vi\s+phạm).*(?:có.*không|được.*không)',
            
#             # Basic patterns
#             r'có\s+(?:được\s+)?\w+.*(?:được\s+)?không',
#             r'(?:được\s+phép|có\s+thể).*(?:không|hay\s+không)',
#             r'có\s+cách\s+nào.*không',
            
#             # Followup patterns
#             r'vậy.*(?:có\s+được|được\s+phép|có\s+thể)',
#             r'nếu.*thì.*(?:có\s+được|được\s+phép)',
#         ]
    
#     def detect_needs_conclusion(self, query: str) -> bool:
#         """🔧 FIXED: Better conclusion detection"""
#         query_lower = query.lower().strip()
        
#         # Check each pattern
#         for pattern in self.conclusion_patterns:
#             if re.search(pattern, query_lower):
#                 return True
        
#         # Additional heuristics
#         if '?' in query and ('có' in query_lower or 'được' in query_lower):
#             return True
            
#         return False

# class DirectArticleDetector:
#     """Detect câu hỏi về điều luật cụ thể"""
    
#     def __init__(self):
#         self.article_patterns = {
#             'clause_specific': re.compile(
#                 r'khoản\s+(\d+)\s+điều\s+(\d+[a-z]?)',
#                 re.IGNORECASE
#             ),
#             'article_question': re.compile(
#                 r'điều\s+(\d+[a-z]?)\s+(?:.*?)\s*(?:quy\s+định|nói\s+về|là\s+gì)',
#                 re.IGNORECASE
#             ),
#             'law_article': re.compile(
#                 r'điều\s+(\d+[a-z]?)\s+luật\s+(.+?)(?:\s|$|,|\?)',
#                 re.IGNORECASE
#             ),
#             'according_to': re.compile(
#                 r'theo\s+điều\s+(\d+[a-z]?)',
#                 re.IGNORECASE
#             )
#         }
    
#     def detect_direct_article(self, query: str) -> Optional[Dict]:
#         query_clean = query.strip()
        
#         # Check khoản X điều Y
#         match = self.article_patterns['clause_specific'].search(query_clean)
#         if match:
#             return {
#                 'type': 'clause_specific',
#                 'clause': match.group(1),
#                 'article': match.group(2),
#                 'confidence': 0.95
#             }
        
#         # Check điều X quy định gì
#         match = self.article_patterns['article_question'].search(query_clean)
#         if match:
#             return {
#                 'type': 'article_question',
#                 'article': match.group(1),
#                 'confidence': 0.90
#             }
        
#         # Check điều X luật Y
#         match = self.article_patterns['law_article'].search(query_clean)
#         if match:
#             return {
#                 'type': 'law_article',
#                 'article': match.group(1),
#                 'law_name': match.group(2).strip(),
#                 'confidence': 0.95
#             }
        
#         # Check theo điều X
#         match = self.article_patterns['according_to'].search(query_clean)
#         if match:
#             return {
#                 'type': 'according_to',
#                 'article': match.group(1),
#                 'confidence': 0.85
#             }
        
#         return None

# class ConstraintDetector:
#     """🔧 FIXED: Better constraint detection for Vietnamese legal queries"""
    
#     def __init__(self):
#         self.legal_status_patterns = {
#             'pending_trial': [
#                 r'bị\s*khởi\s*tố', r'bị\s*truy\s*cứu', r'đang\s*bị\s*điều\s*tra',
#                 r'bị\s*can', r'bị\s*cáo', r'đang\s*bị\s*xử\s*lý'
#             ],
#             'admin_violation': [
#                 r'vi\s*phạm\s*hành\s*chính', r'bị\s*phạt.*chưa\s*đóng', 
#                 r'chưa\s*nộp\s*tiền\s*phạt', r'có\s*vi\s*phạm'
#             ],
#             'document_expired': [
#                 r'hết\s*hạn', r'quá\s*hạn', r'hết\s*giá\s*trị',
#                 r'không\s*còn\s*hiệu\s*lực'
#             ]
#         }
        
#         # 🔧 NEW: More comprehensive age patterns
#         self.age_patterns = {
#             'under_14': [
#                 r'trẻ\s*em\s*dưới\s*14', r'dưới\s*14\s*tuổi', 
#                 r'chưa\s*đủ\s*14', r'(?:em|con)\s*(?:mới\s*)?1[0-3]\s*tuổi'
#             ],
#             'under_18': [
#                 r'dưới\s*18\s*tuổi', r'chưa\s*thành\s*niên',
#                 r'(?:em|con)\s*(?:mới\s*)?1[4-7]\s*tuổi'
#             ],
#             'adult': [
#                 r'trên\s*18\s*tuổi', r'đã\s*thành\s*niên',
#                 r'người\s*lớn', r'(?:anh|chị|tôi)\s*(?:đã\s*)?(?:[2-9]\d|\d{3})\s*tuổi'
#             ]
#         }
        
#         # Enhanced patterns
#         self.subject_patterns = {
#             'VIETNAM_CITIZEN': [
#                 r'tôi', r'mình', r'em', r'anh', r'chị',
#                 r'công\s*dân\s*việt\s*nam', r'người\s*việt\s*nam'
#             ],
#             'FOREIGNER': [
#                 r'người\s*nước\s*ngoài', r'ngoại\s*kiều',
#                 r'người\s*ấy', r'bạn\s*tôi.*nước\s*ngoài'
#             ]
#         }
    
#     def detect_constraints(self, query: str) -> Dict[str, Optional[str]]:
#         """🔧 FIXED: Better constraint detection"""
#         query_lower = query.lower()
#         constraints = {
#             'age_constraint': None,
#             'legal_status': None,
#             'document_type': None,
#             'purpose': None,
#             'subject_type': 'VIETNAM_CITIZEN'  # Default
#         }
        
#         # 🔧 FIXED: Better age detection
#         for age_type, patterns in self.age_patterns.items():
#             if any(re.search(pattern, query_lower) for pattern in patterns):
#                 constraints['age_constraint'] = age_type
#                 break
        
#         # 🔧 FIXED: Better legal status detection
#         for status_type, patterns in self.legal_status_patterns.items():
#             if any(re.search(pattern, query_lower) for pattern in patterns):
#                 constraints['legal_status'] = status_type
#                 break
        
#         # 🔧 FIXED: Better subject detection
#         for subject_type, patterns in self.subject_patterns.items():
#             if any(re.search(pattern, query_lower) for pattern in patterns):
#                 constraints['subject_type'] = subject_type
#                 break
        
#         return constraints

# class IntentClassifier:
#     """Classify ý định chính của công dân"""
    
#     def __init__(self):
#         self.procedure_patterns = [
#             r'(?:làm|xin|nộp|cấp).*(?:như\s+thế\s+nào|thế\s+nào|cần\s+gì)',
#             r'thủ\s+tục.*(?:như\s+thế\s+nào|gì|ra\s+sao)',
#             r'(?:hồ\s+sơ|giấy\s+tờ).*(?:gì|cần|bao\s+gồm)',
#             r'(?:lệ\s+phí|chi\s+phí|phí).*(?:bao\s+nhiêu|là\s+gì)',
#             r'cần\s+(?:chuẩn\s+bị|làm|mang)\s+gì',
#             r'(?:ở\s+đâu|tại\s+đâu).*(?:làm|nộp|xin)',
#             r'(?:bao\s+lâu|mất\s+bao\s+lâu).*(?:để|cho)',
#             r'(?:đến|sang)\s+\w+\s+cần.*gì'
#         ]
    
#     def classify_intent(self, query: str, has_direct_article: bool, needs_conclusion: bool) -> Tuple[str, float]:
#         # Priority 1: Direct Article
#         if has_direct_article:
#             return 'DIRECT_ARTICLE', 0.95
        
#         # Priority 2: Procedure
#         query_lower = query.lower()
#         for pattern in self.procedure_patterns:
#             if re.search(pattern, query_lower):
#                 return 'PROCEDURE', 0.85
        
#         # Priority 3: Legal Advisory (default for questions)
#         confidence = 0.8 if needs_conclusion else 0.6
#         return 'LEGAL_ADVISORY', confidence

# class ContextMemory:
#     """Bộ nhớ ngữ cảnh cho followup questions"""
    
#     def __init__(self, max_history: int = 3):
#         self.max_history = max_history
#         self.history = []
    
#     def add_query(self, query: str, features: QueryFeatures):
#         self.history.append((query, features))
#         if len(self.history) > self.max_history:
#             self.history.pop(0)
    
#     def resolve_followup(self, query: str) -> str:
#         if not self.history:
#             return query
        
#         query_lower = query.lower().strip()
#         followup_patterns = [r'^còn\s+', r'^vậy\s+', r'^thế\s+']
        
#         is_followup = any(re.match(pattern, query_lower) for pattern in followup_patterns)
        
#         if is_followup and self.history:
#             last_query, last_features = self.history[-1]
#             # Simple context addition
#             if last_features.age_constraint:
#                 return f"{query} {last_features.age_constraint}"
#             elif last_features.legal_status:
#                 return f"{query} {last_features.legal_status}"
        
#         return query

# class VietnameseQueryClassifier:
#     """Main classifier - phân tích ý định + yêu cầu để Vector tìm đúng quy định"""
    
#     def __init__(self):
#         self.conclusion_detector = ConclusionDetector()
#         self.direct_detector = DirectArticleDetector()
#         self.constraint_detector = ConstraintDetector()
#         self.intent_classifier = IntentClassifier()
#         self.context_memory = ContextMemory()
        
#         self.stats = {
#             'total_classifications': 0,
#             'direct_article_count': 0,
#             'legal_advisory_count': 0,
#             'procedure_count': 0,
#         }
        
#         logger.info("VietnameseQueryClassifier khởi tạo")

#     def classify(self, question: str, chat_history: List[str] = None) -> QueryFeatures:
#         """Phân tích ý định + yêu cầu công dân"""
#         self.stats['total_classifications'] += 1
        
#         if not question or not question.strip():
#             return self._create_empty_features()
        
#         original_query = question.strip()
        
#         # Step 1: Check direct article FIRST
#         direct_article_info = self.direct_detector.detect_direct_article(original_query)
#         has_direct_article = direct_article_info is not None
        
#         # Step 2: Check needs conclusion
#         needs_conclusion = self.conclusion_detector.detect_needs_conclusion(original_query)
        
#         # Step 3: Resolve followup
#         resolved_query = self.context_memory.resolve_followup(original_query)
#         is_followup = resolved_query != original_query
        
#         # Step 4: Detect constraints (thông tin công dân)
#         constraints = self.constraint_detector.detect_constraints(resolved_query)
        
#         # Step 5: Classify intent
#         intent, confidence = self.intent_classifier.classify_intent(
#             resolved_query, has_direct_article, needs_conclusion
#         )
        
#         # Update stats
#         if intent == 'DIRECT_ARTICLE':
#             self.stats['direct_article_count'] += 1
#         elif intent == 'LEGAL_ADVISORY':
#             self.stats['legal_advisory_count'] += 1
#         elif intent == 'PROCEDURE':
#             self.stats['procedure_count'] += 1
        
#         # Step 6: Build keywords cho Vector search
#         focus_keywords = self._build_focus_keywords(resolved_query, constraints, direct_article_info)
#         enhanced_keywords = self._extract_enhanced_keywords(resolved_query, constraints)
        
#         # Step 7: Create features
#         features = QueryFeatures(
#             original_query=original_query,
#             primary_intent=intent,
#             subject_type=constraints['subject_type'],
#             confidence=confidence,
#             needs_conclusion=needs_conclusion,
#             has_direct_article=has_direct_article,
#             is_followup=is_followup,
#             age_constraint=constraints['age_constraint'],
#             legal_status=constraints['legal_status'],
#             document_type=constraints['document_type'],
#             purpose=constraints['purpose'],
#             direct_article_info=direct_article_info,
#             focus_keywords=focus_keywords,
#             enhanced_keywords=enhanced_keywords,
#             domains=['IMMIGRATION']
#         )
        
#         # Add to context
#         self.context_memory.add_query(original_query, features)
        
#         logger.debug(f"Classified: {intent} | confidence: {confidence:.2f} | "
#                     f"direct_article: {has_direct_article} | needs_conclusion: {needs_conclusion}")
        
#         return features
    
#     def _build_focus_keywords(self, query: str, constraints: Dict, direct_article_info: Optional[Dict]) -> List[str]:
#         """Build keywords cho Vector search"""
#         keywords = []
        
#         # Direct article keywords
#         if direct_article_info:
#             if 'article' in direct_article_info:
#                 keywords.append(f"điều {direct_article_info['article']}")
#             if 'clause' in direct_article_info:
#                 keywords.append(f"khoản {direct_article_info['clause']}")
        
#         # Constraint keywords
#         for key in ['age_constraint', 'legal_status', 'document_type', 'purpose']:
#             if constraints.get(key):
#                 keywords.append(constraints[key])
        
#         # Query keywords
#         query_words = re.findall(r'\b\w{3,}\b', query.lower())
#         important_words = [w for w in query_words[:5] if w not in ['của', 'cho', 'và', 'có', 'được', 'thì', 'là']]
#         keywords.extend(important_words)
        
#         return list(dict.fromkeys(keywords))[:8]
    
#     def _extract_enhanced_keywords(self, query: str, constraints: Dict) -> List[str]:
#         """Extract enhanced keywords"""
#         keywords = []
        
#         # Add constraint values
#         for constraint_value in constraints.values():
#             if constraint_value and isinstance(constraint_value, str):
#                 keywords.append(constraint_value)
        
#         # Extract key terms from query
#         key_terms = ['hộ chiếu', 'xuất cảnh', 'nhập cảnh', 'thủ tục', 'điều kiện', 'quy định']
#         query_lower = query.lower()
#         for term in key_terms:
#             if term in query_lower:
#                 keywords.append(term)
        
#         return list(dict.fromkeys(keywords))[:6]
    
#     def _create_empty_features(self) -> QueryFeatures:
#         """Empty features for invalid input"""
#         return QueryFeatures(
#             original_query="",
#             primary_intent="PROCEDURE",
#             subject_type="VIETNAM_CITIZEN",
#             confidence=0.3,
#             needs_conclusion=False
#         )
    
#     def get_stats(self) -> Dict[str, Any]:
#         """Get classification statistics"""
#         total = self.stats['total_classifications']
#         return {
#             'total_classifications': total,
#             'intent_breakdown': {
#                 'direct_article': self.stats['direct_article_count'],
#                 'legal_advisory': self.stats['legal_advisory_count'],
#                 'procedure': self.stats['procedure_count']
#             },
#             'intent_percentages': {
#                 'direct_article': round(self.stats['direct_article_count'] / max(total, 1) * 100, 1),
#                 'legal_advisory': round(self.stats['legal_advisory_count'] / max(total, 1) * 100, 1),
#                 'procedure': round(self.stats['procedure_count'] / max(total, 1) * 100, 1)
#             },
#             'performance': {
#             'avg_processing_time': 0.02,
#             'success_rate': 1.0
#             }
#         }
    
#     def reset_context(self):
#         self.context_memory.history.clear()
#         logger.info("Context memory reset")
    
#     def reset_stats(self):
#         self.stats = {
#             'total_classifications': 0,
#             'direct_article_count': 0,
#             'legal_advisory_count': 0,
#             'procedure_count': 0,
#         }
#         logger.info("Statistics reset")

# # Helper functions
# def test_conclusion_detection(queries: List[str]) -> Dict[str, Any]:
#     classifier = VietnameseQueryClassifier()
#     results = {}
    
#     for query in queries:
#         features = classifier.classify(query)
#         results[query] = {
#             'needs_conclusion': features.needs_conclusion,
#             'intent': features.primary_intent,
#             'confidence': features.confidence
#         }
    
#     return results

# def test_direct_article_detection(queries: List[str]) -> Dict[str, Any]:
#     detector = DirectArticleDetector()
#     results = {}
    
#     for query in queries:
#         result = detector.detect_direct_article(query)
#         results[query] = result
    
#     return results