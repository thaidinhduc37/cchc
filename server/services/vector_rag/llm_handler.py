# server/services/vector_rag/llm_handler.py - FIXED VERSION
"""
LLM Handler - FIXED: Đã thêm import re và sửa lỗi fallback responses
🎯 VAI TRÒ: Generate natural response từ organized context
📋 API: Gemini tự format đẹp
📋 LOCAL: Ollama cần template rõ ràng
✅ OUTPUT: Professional legal response with full citations
"""
import re  # 🔧 FIX: Thêm import re
import asyncio
import requests
from typing import Dict, Any, Optional
import logging

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from services.vector_rag.rag_config import config

logger = logging.getLogger(__name__)

class LLMHandler:
    """FIXED LLM Handler - đã sửa tất cả lỗi"""
    
    def __init__(self):
        self.config = config
        self.providers = {
            'gemini': {'available': False, 'used': 0},
            'ollama': {'available': False, 'used': 0}
        }
        
        self.stats = {
            'total_requests': 0,
            'api_responses': 0,      # Gemini API
            'local_responses': 0,    # Ollama local
            'fallback_responses': 0  # Emergency
        }
        
        self._init_providers()
        logger.info("LLM Handler - FIXED (đã sửa tất cả lỗi)")
    
    def _init_providers(self):
        """Init providers"""
        # Gemini API
        if self.config.gemini_api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=self.config.gemini_api_key)
                self.gemini_model = genai.GenerativeModel(
                    self.config.gemini_model,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=1000,
                        temperature=0.1,
                        top_p=0.9
                    )
                )
                self.providers['gemini']['available'] = True
                logger.info("✅ Gemini API ready")
            except Exception as e:
                logger.warning(f"❌ Gemini init failed: {e}")
        
        # Ollama local
        try:
            response = requests.get(f"{self.config.ollama_url}/api/tags", timeout=3)
            if response.status_code == 200:
                models = response.json().get('models', [])
                if any(self.config.ollama_model in model['name'] for model in models):
                    self.providers['ollama']['available'] = True
                    logger.info("✅ Ollama local ready")
        except:
            logger.warning("❌ Ollama not available")
    
    async def generate_response(self, query: str, context_result: Any, query_features: Any = None) -> Dict[str, Any]:
        """Main: Generate response từ organized context"""
        self.stats['total_requests'] += 1
        
        # Priority 1: Gemini API
        if self.providers['gemini']['available']:
            result = await self._try_gemini_api(context_result)
            if result.get('success'):
                self.stats['api_responses'] += 1
                self.providers['gemini']['used'] += 1
                return result
        
        # Priority 2: Ollama local
        if self.providers['ollama']['available']:
            result = await self._try_ollama_guided(context_result)
            if result.get('success'):
                self.stats['local_responses'] += 1
                self.providers['ollama']['used'] += 1
                return result
        
        # Priority 3: Emergency fallback
        self.stats['fallback_responses'] += 1
        return self._create_fallback_response(context_result)
    
    async def _try_gemini_api(self, context_result: Any) -> Dict[str, Any]:
        """Gemini API - minimal prompt"""
        try:
            prompt = self._create_api_prompt(context_result)
            
            response = await asyncio.wait_for(
                asyncio.to_thread(self.gemini_model.generate_content, prompt),
                timeout=15.0
            )
            
            if response and response.text:
                answer = response.text.strip()
                
                if len(answer) > 200 and 'Chào bạn' in answer:
                    return {
                        'success': True,
                        'answer': answer,
                        'provider': 'gemini_api',
                        'method': 'api_natural_formatting'
                    }
            
            return {'success': False, 'error': 'Invalid response'}
            
        except Exception as e:
            logger.warning(f"Gemini API failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _try_ollama_guided(self, context_result: Any) -> Dict[str, Any]:
        """Ollama local - detailed template"""
        try:
            prompt = self._create_ollama_template(context_result)
            
            response = await asyncio.wait_for(
                asyncio.to_thread(self._ollama_request, prompt),
                timeout=25.0
            )
            
            if response.get('success'):
                answer = response['answer']
                answer = self._clean_ollama_response(answer)
                
                if len(answer) > 200:
                    return {
                        'success': True,
                        'answer': answer,
                        'provider': 'ollama_local',
                        'method': 'guided_template'
                    }
            
            return {'success': False, 'error': 'Ollama generation failed'}
            
        except Exception as e:
            logger.warning(f"Ollama failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_api_prompt(self, context_result: Any) -> str:
        """Simple prompt for API"""
        query = getattr(context_result, 'query', 'câu hỏi của bạn')
        primary_content = getattr(context_result, 'primary_content', '')
        citation = getattr(context_result, 'primary_citation', '')
        needs_conclusion = getattr(context_result, 'needs_conclusion', False)
        answer_type = getattr(context_result, 'answer_type', 'legal')
        exception_detected = getattr(context_result, 'exception_detected', False)
        
        format_guidance = ""
        if answer_type == "procedure":
            format_guidance = "4. Trình bày theo từng bước thủ tục rõ ràng\n"
        elif answer_type == "direct_quote":
            format_guidance = "4. Trích dẫn trực tiếp ngắn gọn\n"
        else:
            format_guidance = "4. Giải thích quy định pháp luật\n"
        
        if exception_detected:
            format_guidance += "5. LƯU Ý: Có ngoại lệ/hạn chế trong quy định\n"
        
        conclusion_step = ""
        if needs_conclusion:
            conclusion_step = "6. Kết luận rõ ràng: ĐƯỢC hoặc KHÔNG ĐƯỢC (với lý do)\n"
        
        final_step = "7." if needs_conclusion else "6."
        
        prompt = f"""Hãy trả lời câu hỏi pháp luật sau theo định dạng chuẩn:

Câu hỏi: {query}
Quy định pháp luật: {primary_content}
Trích dẫn: {citation}

Yêu cầu:
1. Bắt đầu: "Chào bạn, dựa trên quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam, tôi xin trả lời câu hỏi: \"{query}\" như sau:"

2. Trích dẫn đầy đủ: "Căn cứ {citation}, Luật Xuất cảnh, nhập cảnh của công dân Việt Nam:"

3. Nội dung quy định với dấu ngoặc kép và indent

{format_guidance}{conclusion_step}{final_step} Kết thúc: "Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"

Trả lời chuyên nghiệp, trích dẫn chính xác:"""
        
        return prompt
    
    def _create_ollama_template(self, context_result: Any) -> str:
        """Detailed template for Ollama"""
        query = getattr(context_result, 'query', 'câu hỏi của bạn')
        primary_content = getattr(context_result, 'primary_content', '')
        citation = getattr(context_result, 'primary_citation', '')
        needs_conclusion = getattr(context_result, 'needs_conclusion', False)
        answer_type = getattr(context_result, 'answer_type', 'legal')
        exception_detected = getattr(context_result, 'exception_detected', False)
        
        legal_quote = self._extract_key_legal_text(primary_content)
        
        conclusion_part = ""
        if needs_conclusion:
            conclusion_part = "\nKết luận: [ĐƯỢC/KHÔNG ĐƯỢC] [lý do ngắn gọn]"
        
        exception_note = ""
        if exception_detected:
            exception_note = "\n\nLƯU Ý: Quy định có ngoại lệ/hạn chế cần xem xét."
        
        template = f"""Bạn là chuyên gia pháp luật. Hãy trả lời theo CHÍNH XÁC template sau:

TEMPLATE CHUẨN:
```
Chào bạn, dựa trên quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam, tôi xin trả lời câu hỏi: "{query}" như sau:

Căn cứ {citation}, Luật Xuất cảnh, nhập cảnh của công dân Việt Nam:

    "{legal_quote}"{exception_note}{conclusion_part}

Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn
```

DỮ LIỆU:
- Câu hỏi: {query}
- Trích dẫn: {citation}
- Nội dung luật: {legal_quote}
- Loại trả lời: {answer_type}
- Cần kết luận: {'Có' if needs_conclusion else 'Không'}
- Có ngoại lệ: {'Có' if exception_detected else 'Không'}

ĐIỀN VÀO TEMPLATE TRÊN. KHÔNG thêm bớt gì:"""
        
        return template
    
    def _extract_key_legal_text(self, content: str) -> str:
        """Extract key legal text for quotation"""
        if not content:
            return ""
        
        sentences = content.split('. ')
        key_sentences = []
        
        for sentence in sentences[:3]:
            sentence = sentence.strip()
            if len(sentence) > 20:
                key_sentences.append(sentence)
        
        result = '. '.join(key_sentences)
        
        if len(result) > 300:
            result = result[:300] + "..."
        
        return result
    
    def _ollama_request(self, prompt: str) -> Dict[str, Any]:
        """Ollama request"""
        try:
            response = requests.post(
                f"{self.config.ollama_url}/api/generate",
                json={
                    "model": self.config.ollama_model,
                    "prompt": prompt,
                    "system": "Bạn là chuyên gia pháp luật. Trả lời theo chính xác template được cung cấp. KHÔNG thêm bớt.",
                    "options": {"temperature": 0.0, "top_p": 0.8},
                    "stream": False
                },
                timeout=20
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('response', '').strip()
                if len(answer) > 100:
                    return {"success": True, "answer": answer}
            
            return {'success': False, 'error': 'Invalid response'}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _clean_ollama_response(self, response: str) -> str:
        """Clean Ollama response"""
        if not response:
            return ""
        
        response = response.strip()
        response = response.replace('```', '')
        response = re.sub(r'^(TRẢ LỜI|RESPONSE):\s*', '', response, flags=re.IGNORECASE)
        
        if response.count('Chào bạn, dựa trên quy định') > 1:
            parts = response.split('Chào bạn, dựa trên quy định')
            if len(parts) > 1:
                response = 'Chào bạn, dựa trên quy định' + parts[1]
        
        return response
    
    def _create_fallback_response(self, context_result: Any) -> Dict[str, Any]:
        """🔧 FIXED: Better fallback responses cho từng trường hợp"""
        query = getattr(context_result, 'query', 'câu hỏi của bạn')
        citation = getattr(context_result, 'primary_citation', '')
        legal_text = self._extract_key_legal_text(getattr(context_result, 'primary_content', ''))
        exception_detected = getattr(context_result, 'exception_detected', False)
        
        # 🔧 CASE 1: Có đủ thông tin nhưng LLM thất bại
        if citation and legal_text:
            exception_note = "\n\nLƯU Ý: Quy định có ngoại lệ/hạn chế cần xem xét." if exception_detected else ""
            
            response = f"""Chào bạn, dựa trên quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam, tôi xin trả lời câu hỏi: "{query}" như sau:

Căn cứ {citation}, Luật Xuất cảnh, nhập cảnh của công dân Việt Nam:

    "{legal_text}"{exception_note}

Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
            
            return {
                'success': True,
                'answer': response,
                'provider': 'fallback_with_content',
                'method': 'direct_citation'
            }
        
        # 🔧 CASE 2: Có thông tin nhưng không đảm bảo chính xác
        elif legal_text and not citation:
            response = f"""Chào bạn, dựa trên quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam, tôi xin trả lời câu hỏi: "{query}" như sau:

Hiện tại dữ liệu hệ thống đang được cập nhật, không đảm bảo tính chính xác nên tạm thời chưa có thông tin cụ thể, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
            
            return {
                'success': True,
                'answer': response,
                'provider': 'fallback_uncertain',
                'method': 'uncertain_data'
            }
        
        # 🔧 CASE 3: Thất bại hoàn toàn - lỗi hệ thống  
        else:
            response = f"""Chào bạn, dựa trên quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam, tôi xin trả lời câu hỏi: "{query}" như sau:

Hệ thống gặp sự cố kỹ thuật khi xử lý câu hỏi này, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
            
            return {
                'success': True,
                'answer': response,
                'provider': 'fallback_error',
                'method': 'system_error'
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Simple stats"""
        total = self.stats['total_requests']
        return {
            'version': 'LLM Handler - FIXED v1.1',
            'approach': 'API first (natural), Ollama guided (template)',
            'performance': {
                'total_requests': total,
                'api_rate': round(self.stats['api_responses'] / total, 3) if total > 0 else 0,
                'local_rate': round(self.stats['local_responses'] / total, 3) if total > 0 else 0,
                'fallback_rate': round(self.stats['fallback_responses'] / total, 3) if total > 0 else 0
            },
            'providers': {
                'gemini': self.providers['gemini'],
                'ollama': self.providers['ollama']
            }
        }
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Provider status"""
        return {
            'gemini_available': self.providers['gemini']['available'],
            'ollama_available': self.providers['ollama']['available'],
            'any_provider_available': any(p['available'] for p in self.providers.values())
        }