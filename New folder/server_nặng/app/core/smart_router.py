"""
🧠 Smart Router - Điều hướng thông minh giữa Flow và RAG
Phân tích intent user và route đến engine phù hợp
"""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from fuzzywuzzy import fuzz
import logging

logger = logging.getLogger(__name__)

class IntentType(Enum):
    FLOW = "flow"
    RAG = "rag"
    UNKNOWN = "unknown"

class Domain(Enum):
    XUATNHAPCANH = "xuatnhapcanh"
    CANCUOC = "cancuoc"
    GENERAL = "general"

@dataclass
class RouterResult:
    """Kết quả phân tích routing"""
    intent_type: IntentType
    domain: Domain
    confidence: float
    reasoning: str
    flow_suggestion: Optional[str] = None
    keywords_found: List[str] = None

class SmartRouter:
    """
    Smart Router - Điều hướng thông minh
    Phân tích user input và quyết định route đến Flow hoặc RAG
    """
    
    def __init__(self):
        self.flow_keywords = {
            "primary": [
                "hướng dẫn", "làm thế nào", "cách làm", "thủ tục", 
                "quy trình", "bước", "làm như thế nào", "thực hiện",
                "nộp hồ sơ", "đăng ký", "xin", "làm"
            ],
            "secondary": [
                "giúp tôi", "chỉ tôi", "dẫn tôi", "chỉ dẫn",
                "from step", "từ đầu", "bắt đầu"
            ]
        }
        
        self.rag_keywords = {
            "primary": [
                "phí", "lệ phí", "chi phí", "giá", "bao nhiêu",
                "khi nào", "bao lâu", "thời gian", "ở đâu", "địa điểm",
                "điều kiện", "yêu cầu", "quy định", "luật", "nghị định",
                "thông tư", "văn bản", "pháp lý"
            ],
            "secondary": [
                "thông tin", "tìm hiểu", "tra cứu", "kiểm tra",
                "có thể", "được không", "phải không"
            ]
        }
        
        self.domain_keywords = {
            Domain.XUATNHAPCANH: [
                "hộ chiếu", "passport", "visa", "xuất cảnh", "nhập cảnh",
                "ra nước ngoài", "du lịch", "công tác", "định cư",
                "xuất nhập cảnh", "biên phòng"
            ],
            Domain.CANCUOC: [
                "căn cước", "cccd", "chứng minh", "cmnd", "cmtnd",
                "thẻ căn cước", "căn cước công dân", "định danh",
                "vneid", "chip"
            ]
        }

    def route_request(self, user_input: str, context: Optional[Dict] = None) -> RouterResult:
        """
        Phân tích user input và quyết định routing
        
        Args:
            user_input: Input từ user
            context: Context hiện tại (optional)
            
        Returns:
            RouterResult với thông tin routing
        """
        try:
            # Normalize input
            normalized_input = self._normalize_input(user_input)
            
            # Phân tích domain trước
            domain, domain_confidence = self._detect_domain(normalized_input)
            
            # Phân tích intent
            intent_type, intent_confidence, keywords_found = self._detect_intent(normalized_input)
            
            # Tính confidence tổng thể
            overall_confidence = (domain_confidence + intent_confidence) / 2
            
            # Xác định flow suggestion nếu cần
            flow_suggestion = self._suggest_flow(domain, intent_type, normalized_input)
            
            # Tạo reasoning
            reasoning = self._create_reasoning(
                intent_type, domain, keywords_found, 
                intent_confidence, domain_confidence
            )
            
            return RouterResult(
                intent_type=intent_type,
                domain=domain,
                confidence=overall_confidence,
                reasoning=reasoning,
                flow_suggestion=flow_suggestion,
                keywords_found=keywords_found
            )
            
        except Exception as e:
            logger.error(f"Error in route_request: {e}")
            return RouterResult(
                intent_type=IntentType.UNKNOWN,
                domain=Domain.GENERAL,
                confidence=0.0,
                reasoning=f"Lỗi phân tích: {str(e)}",
                keywords_found=[]
            )

    def _normalize_input(self, text: str) -> str:
        """Normalize input text"""
        # Lowercase và remove extra spaces
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        
        # Remove punctuation nhưng giữ lại dấu câu hỏi
        normalized = re.sub(r'[^\w\s\?]', ' ', normalized)
        
        return normalized

    def _detect_domain(self, text: str) -> Tuple[Domain, float]:
        """
        Phát hiện domain từ input
        
        Returns:
            (Domain, confidence_score)
        """
        domain_scores = {}
        
        for domain, keywords in self.domain_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    # Exact match có điểm cao hơn
                    score += 1.0
                else:
                    # Fuzzy matching
                    fuzzy_score = max([
                        fuzz.partial_ratio(keyword, word) 
                        for word in text.split()
                    ])
                    if fuzzy_score > 80:
                        score += fuzzy_score / 100 * 0.7
            
            domain_scores[domain] = score / len(keywords)
        
        if not domain_scores or max(domain_scores.values()) < 0.1:
            return Domain.GENERAL, 0.1
        
        best_domain = max(domain_scores, key=domain_scores.get)
        confidence = min(domain_scores[best_domain], 1.0)
        
        return best_domain, confidence

    def _detect_intent(self, text: str) -> Tuple[IntentType, float, List[str]]:
        """
        Phát hiện intent từ input
        
        Returns:
            (IntentType, confidence_score, keywords_found)
        """
        flow_score = 0
        rag_score = 0
        keywords_found = []
        
        # Check Flow keywords
        for keyword in self.flow_keywords["primary"]:
            if keyword in text:
                flow_score += 2.0
                keywords_found.append(keyword)
        
        for keyword in self.flow_keywords["secondary"]:
            if keyword in text:
                flow_score += 1.0
                keywords_found.append(keyword)
        
        # Check RAG keywords
        for keyword in self.rag_keywords["primary"]:
            if keyword in text:
                rag_score += 2.0
                keywords_found.append(keyword)
        
        for keyword in self.rag_keywords["secondary"]:
            if keyword in text:
                rag_score += 1.0
                keywords_found.append(keyword)
        
        # Heuristic rules
        if "?" in text and any(word in text for word in ["gì", "nào", "sao", "thế nào"]):
            rag_score += 1.0
        
        if any(word in text for word in ["bước", "đầu tiên", "tiếp theo"]):
            flow_score += 1.5
        
        # Determine intent
        total_score = flow_score + rag_score
        
        if total_score == 0:
            return IntentType.UNKNOWN, 0.0, keywords_found
        
        if flow_score > rag_score:
            confidence = min(flow_score / (total_score + 1), 1.0)
            return IntentType.FLOW, confidence, keywords_found
        elif rag_score > flow_score:
            confidence = min(rag_score / (total_score + 1), 1.0)
            return IntentType.RAG, confidence, keywords_found
        else:
            # Tie - prefer RAG for questions, Flow for instructions
            if "?" in text:
                return IntentType.RAG, 0.5, keywords_found
            else:
                return IntentType.FLOW, 0.5, keywords_found

    def _suggest_flow(self, domain: Domain, intent_type: IntentType, text: str) -> Optional[str]:
        """Suggest specific flow based on analysis"""
        
        if intent_type != IntentType.FLOW or domain == Domain.GENERAL:
            return None
        
        # Domain-specific flow suggestions
        if domain == Domain.XUATNHAPCANH:
            if any(word in text for word in ["cấp mới", "lần đầu", "chưa có"]):
                if any(word in text for word in ["14", "trẻ em", "nhỏ"]):
                    return "cap_moi_duoi_14"
                else:
                    return "cap_moi_tu_14"
            elif any(word in text for word in ["cấp lại", "đổi", "hết hạn", "mất", "hỏng"]):
                if "hết hạn" in text:
                    return "cap_lai_het_han"
                elif "mất" in text:
                    return "cap_lai_mat"
                else:
                    return "cap_lai_hu_hong"
        
        return None

    def _create_reasoning(self, intent_type: IntentType, domain: Domain, 
                         keywords: List[str], intent_conf: float, 
                         domain_conf: float) -> str:
        """Tạo reasoning cho decision"""
        
        reasoning_parts = []
        
        # Intent reasoning
        if intent_type == IntentType.FLOW:
            reasoning_parts.append(f"Phát hiện intent HƯỚNG DẪN (confidence: {intent_conf:.2f})")
        elif intent_type == IntentType.RAG:
            reasoning_parts.append(f"Phát hiện intent TRA CỨU (confidence: {intent_conf:.2f})")
        else:
            reasoning_parts.append("Không xác định được intent rõ ràng")
        
        # Domain reasoning
        if domain != Domain.GENERAL:
            reasoning_parts.append(f"Domain: {domain.value} (confidence: {domain_conf:.2f})")
        
        # Keywords found
        if keywords:
            reasoning_parts.append(f"Keywords: {', '.join(keywords[:5])}")
        
        return " | ".join(reasoning_parts)

    def should_switch_context(self, current_context: Dict, new_result: RouterResult) -> bool:
        """
        Quyết định có nên switch context không
        
        Args:
            current_context: Context hiện tại
            new_result: Kết quả routing mới
            
        Returns:
            True nếu nên switch context
        """
        if not current_context:
            return True
        
        current_intent = current_context.get("intent_type")
        current_domain = current_context.get("domain")
        
        # Switch nếu intent type khác và confidence cao
        if (new_result.intent_type.value != current_intent and 
            new_result.confidence > 0.7):
            return True
        
        # Switch nếu domain khác và confidence cao
        if (new_result.domain.value != current_domain and 
            new_result.confidence > 0.6):
            return True
        
        return False

    def get_routing_stats(self) -> Dict:
        """Lấy thống kê routing (for debugging)"""
        return {
            "flow_keywords_count": len(self.flow_keywords["primary"]) + len(self.flow_keywords["secondary"]),
            "rag_keywords_count": len(self.rag_keywords["primary"]) + len(self.rag_keywords["secondary"]),
            "domains_supported": [d.value for d in self.domain_keywords.keys()],
            "version": "1.0.0"
        }

# Test cases
if __name__ == "__main__":
    router = SmartRouter()
    
    test_cases = [
        "Hướng dẫn tôi làm hộ chiếu",
        "Phí làm hộ chiếu bao nhiêu?",
        "Tôi muốn biết quy trình cấp CCCD",
        "Luật về xuất nhập cảnh có gì?",
        "Làm thế nào để đổi hộ chiếu hết hạn?",
        "Khi nào thì được cấp căn cước mới?",
    ]
    
    for test_input in test_cases:
        result = router.route_request(test_input)
        print(f"\nInput: {test_input}")
        print(f"Intent: {result.intent_type.value}")
        print(f"Domain: {result.domain.value}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Flow suggestion: {result.flow_suggestion}")
        print(f"Reasoning: {result.reasoning}")