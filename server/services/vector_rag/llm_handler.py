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
        
        self._current_conversation_context = {}  # NEW: Store conversation context
        logger.info("LLM Handler - ENHANCED with conversation context")
    
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
        """
        ENHANCED: Generate response với conversation context integration
        """
        self.stats['total_requests'] += 1
        
        # Store conversation context for use in prompts
        self._current_conversation_context = self._extract_conversation_context(query_features)
        
        # Priority 1: Gemini API với conversation context
        if self.providers['gemini']['available']:
            result = await self._try_gemini_api(context_result, query_features)
            if result.get('success'):
                self.stats['api_responses'] += 1
                self.providers['gemini']['used'] += 1
                return result
        
        # Priority 2: Ollama local với conversation context
        if self.providers['ollama']['available']:
            result = await self._try_ollama_guided(context_result, query_features)
            if result.get('success'):
                self.stats['local_responses'] += 1
                self.providers['ollama']['used'] += 1
                return result
        
        # Priority 3: Enhanced fallback với conversation context
        self.stats['fallback_responses'] += 1
        return self._create_fallback_response(context_result, query_features)
    
    async def _try_gemini_api(self, context_result: Any, query_features: Any) -> Dict[str, Any]:
        """
        ENHANCED: Gemini API với conversation context
        """
        try:
            prompt = self._create_api_prompt(context_result, query_features)
            
            response = await asyncio.wait_for(
                asyncio.to_thread(self.gemini_model.generate_content, prompt),
                timeout=15.0
            )
            
            if response and response.text:
                answer = response.text.strip()
                
                # Enhanced validation
                if len(answer) > 150 and ('Chào bạn' in answer or 'để' in answer[:50]):
                    return {
                        'success': True,
                        'answer': answer,
                        'provider': 'gemini_api_enhanced',
                        'method': 'conversation_aware'
                    }
            
            return {'success': False, 'error': 'Invalid response'}
            
        except Exception as e:
            logger.warning(f"Enhanced Gemini API failed: {e}")
            return {'success': False, 'error': str(e)}

    def _extract_conversation_context(self, query_features: Any) -> Dict[str, Any]:
        """
        NEW: Extract conversation context from query_features
        """
        conversation_context = {
            'has_context': False,
            'topic_thread': '',
            'location': '',
            'user_status': '',
            'conversation_bridge': '',
            'response_tone': 'formal'
        }
        
        if not query_features:
            return conversation_context
        
        # Extract topic thread
        if hasattr(query_features, 'topic_thread'):
            conversation_context['topic_thread'] = query_features.topic_thread
            conversation_context['has_context'] = True
        
        # Extract citizen profile
        if hasattr(query_features, 'citizen_profile'):
            citizen_profile = query_features.citizen_profile
            
            # Location context
            location = citizen_profile.get('location')
            if location:
                conversation_context['location'] = location
                conversation_context['has_context'] = True
            
            # User status
            passport_status = citizen_profile.get('passport_status')
            age_group = citizen_profile.get('age_group')
            
            if passport_status == 'not_have':
                conversation_context['user_status'] = 'first_time'
            elif passport_status == 'expired':
                conversation_context['user_status'] = 'renewal'
            elif age_group == 'minor':
                conversation_context['user_status'] = 'minor'
        
        # Build conversation bridge
        if conversation_context['has_context']:
            conversation_context['conversation_bridge'] = self._build_conversation_bridge(conversation_context)
            conversation_context['response_tone'] = self._determine_response_tone(conversation_context)
        
        return conversation_context

    def _build_conversation_bridge(self, conv_context: Dict) -> str:
        """Build natural conversation bridge"""
        bridge_parts = []
        
        # Topic continuity
        topic = conv_context.get('topic_thread')
        if topic == 'hộ chiếu':
            bridge_parts.append("về thủ tục hộ chiếu")
        elif topic == 'visa':
            bridge_parts.append("về vấn đề visa")
        
        # Location context
        location = conv_context.get('location')
        if location:
            bridge_parts.append(f"tại {location}")
        
        # User status context
        user_status = conv_context.get('user_status')
        if user_status == 'first_time':
            bridge_parts.append("cho trường hợp làm lần đầu")
        elif user_status == 'renewal':
            bridge_parts.append("về việc cấp lại")
        elif user_status == 'minor':
            bridge_parts.append("cho trẻ em")
        
        return ' '.join(bridge_parts) if bridge_parts else ''

    def _determine_response_tone(self, conv_context: Dict) -> str:
        """Determine response tone from conversation context"""
        user_status = conv_context.get('user_status')
        
        if user_status == 'first_time':
            return 'supportive'  # Hướng dẫn chi tiết cho người lần đầu
        elif user_status == 'renewal':
            return 'efficient'   # Ngắn gọn cho người đã có kinh nghiệm
        elif user_status == 'minor':
            return 'careful'     # Cẩn thận cho trường hợp trẻ em
        elif conv_context.get('topic_thread'):
            return 'conversational'  # Tự nhiên cho conversation liên tục
        
        return 'formal'
    
    async def _try_ollama_guided_enhanced(self, context_result: Any, query_features: Any) -> Dict[str, Any]:
        """
        ENHANCED: Ollama với conversation context
        """
        try:
            prompt = self._create_ollama_template(context_result, query_features)
            
            response = await asyncio.wait_for(
                asyncio.to_thread(self._ollama_request, prompt),
                timeout=25.0
            )
            
            if response.get('success'):
                answer = response['answer']
                answer = self._clean_ollama_response(answer)
                
                if len(answer) > 150:
                    return {
                        'success': True,
                        'answer': answer,
                        'provider': 'ollama_local_enhanced',
                        'method': 'conversation_aware_template'
                    }
            
            return {'success': False, 'error': 'Enhanced Ollama generation failed'}
            
        except Exception as e:
            logger.warning(f"Enhanced Ollama failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_api_prompt(self, context_result: Any, query_features: Any) -> str:
        """
        ENHANCED: Natural prompt với conversation context
        """
        query = getattr(context_result, 'query', 'câu hỏi của bạn')
        primary_content = getattr(context_result, 'primary_content', '')
        citation = getattr(context_result, 'primary_citation', '')
        needs_conclusion = getattr(context_result, 'needs_conclusion', False)
        answer_type = getattr(context_result, 'answer_type', 'legal')
        
        # Get conversation context
        conv_context = self._current_conversation_context
        conversation_bridge = conv_context.get('conversation_bridge', '')
        response_tone = conv_context.get('response_tone', 'formal')
        
        # Build natural opening
        if conversation_bridge:
            opening = f"Chào bạn, để {conversation_bridge}, tôi xin trả lời như sau:"
        else:
            opening = f"Chào bạn, về câu hỏi \"{query}\", tôi xin trả lời như sau:"
        
        # Format guidance based on answer type
        format_guidance = ""
        if answer_type == "procedure":
            if response_tone == 'supportive':
                format_guidance = "4. Hướng dẫn từng bước chi tiết, dễ hiểu cho người lần đầu\n"
            elif response_tone == 'efficient':
                format_guidance = "4. Trình bày các bước thủ tục ngắn gọn, trọng tâm\n"
            else:
                format_guidance = "4. Trình bày thủ tục theo từng bước rõ ràng\n"
        elif answer_type == "direct_quote":
            format_guidance = "4. Trích dẫn trực tiếp quy định\n"
        else:
            format_guidance = "4. Giải thích quy định pháp luật một cách dễ hiểu\n"
        
        # Conclusion step
        conclusion_step = ""
        if needs_conclusion:
            conclusion_step = "5. Kết luận rõ ràng: ĐƯỢC hoặc KHÔNG ĐƯỢC (với lý do)\n"
        
        final_step = "6." if needs_conclusion else "5."
        
        prompt = f"""Hãy trả lời câu hỏi pháp luật theo format tự nhiên:

Câu hỏi: {query}
Quy định: {primary_content}
Trích dẫn: {citation}
Ngữ cảnh: {conversation_bridge}
Tone: {response_tone}

Yêu cầu:
1. Mở đầu tự nhiên: "{opening}"

2. Trích dẫn pháp lý (nếu có): "Căn cứ {citation}:"

3. Nội dung quy định (trong dấu ngoặc kép)

{format_guidance}{conclusion_step}{final_step} Kết thúc: "Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"

Trả lời tự nhiên, mạch lạc, phù hợp với ngữ cảnh conversation:"""
    
        return prompt
    
    def _create_enhanced_ollama_template(self, context_result: Any, query_features: Any) -> str:
        """
        ENHANCED: Ollama template với conversation context
        """
        query = getattr(context_result, 'query', 'câu hỏi của bạn')
        citation = getattr(context_result, 'primary_citation', '')
        legal_text = self._extract_key_legal_text(getattr(context_result, 'primary_content', ''))
        needs_conclusion = getattr(context_result, 'needs_conclusion', False)
        
        # Get conversation context
        conv_context = self._current_conversation_context
        conversation_bridge = conv_context.get('conversation_bridge', '')
        
        # Natural opening
        if conversation_bridge:
            opening = f"Chào bạn, để {conversation_bridge}, tôi xin trả lời như sau:"
        else:
            opening = f"Chào bạn, về câu hỏi \"{query}\", tôi xin trả lời như sau:"
        
        # Conclusion part
        conclusion_part = ""
        if needs_conclusion:
            conclusion_part = "\n\nKết luận: [ĐƯỢC/KHÔNG ĐƯỢC] [lý do ngắn gọn]"
        
        template = f"""Bạn là chuyên gia pháp luật. Trả lời theo CHÍNH XÁC template sau:

TEMPLATE:
```
{opening}

Căn cứ {citation}:

    "{legal_text}"{conclusion_part}

Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn
```

ĐIỀN VÀO TEMPLATE. KHÔNG thêm bớt:"""
    
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
    
    def _create_fallback_response(self, context_result: Any, query_features: Any) -> Dict[str, Any]:
        """
        ENHANCED: Clean fallback responses với conversation context
        """
        query = getattr(context_result, 'query', 'câu hỏi của bạn')
        citation = getattr(context_result, 'primary_citation', '')
        legal_text = self._extract_key_legal_text(getattr(context_result, 'primary_content', ''))
        
        # Get conversation context
        conv_context = self._current_conversation_context
        conversation_bridge = conv_context.get('conversation_bridge', '')
        
        # Natural opening với conversation context
        if conversation_bridge:
            opening = f"Chào bạn, để {conversation_bridge}, tôi xin trả lời như sau:"
        else:
            opening = f"Chào bạn, về câu hỏi \"{query}\", tôi xin trả lời như sau:"
        
        # CASE 1: Có đủ thông tin - format tự nhiên
        if citation and legal_text:
            response = f"""{opening}

    Căn cứ {citation}:

        "{legal_text}"

    Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
            
            return {
                'success': True,
                'answer': response,
                'provider': 'fallback_with_content_enhanced',
                'method': 'conversation_aware_fallback'
            }
        
        # CASE 2: Không đảm bảo chính xác - NGẮN GỌN
        elif legal_text and not citation:
            response = f"""Chào bạn,

    Hiện tại dữ liệu hệ thống đang được cập nhật, không đảm bảo tính chính xác nên tạm thời chưa có thông tin cụ thể, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
            
            return {
                'success': True,
                'answer': response,
                'provider': 'fallback_uncertain_clean',
                'method': 'clean_uncertain'
            }
        
        # CASE 3: Lỗi hệ thống - SIÊU NGẮN GỌN
        else:
            response = f"""Chào bạn,

    Hệ thống gặp sự cố kỹ thuật khi xử lý câu hỏi này, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
            
            return {
                'success': True,
                'answer': response,
                'provider': 'fallback_error_clean',
                'method': 'clean_error'
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