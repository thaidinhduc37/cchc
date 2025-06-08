# server/services/vector_rag/llm_handler.py
"""
LLM Handler - SỬA LOGIC: 3 prompt templates riêng biệt
"""
import asyncio
import aiohttp
import requests
from typing import Dict, Any, Optional
import logging
from datetime import datetime

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from services.vector_rag.rag_config import config

logger = logging.getLogger(__name__)

# SỬA LOGIC: 3 PROMPT TEMPLATES riêng cho từng loại context
LEGAL_DOMINANT_PROMPT = """Bạn là chuyên gia PHÁP LUẬT xuất nhập cảnh Việt Nam.

NGUYÊN TẮC TRẢ LỜI (LEGAL FOCUS):
✅ Ưu tiên trích dẫn CHÍNH XÁC từ văn bản pháp luật
✅ Nêu rõ Điều, Khoản, Điểm cụ thể
✅ Ghi rõ tên văn bản và năm ban hành
✅ Giải thích ý nghĩa pháp lý

THÔNG TIN PHÁP LUẬT:
{context}

CÂU HỎI: {question}

YÊU CẦU: Trả lời dựa trên VĂN BẢN PHÁP LUẬT, trích dẫn chính xác điều khoản.

TRẢ LỜI:"""

PROCEDURE_DOMINANT_PROMPT = """Bạn là chuyên viên THỦ TỤC HÀNH CHÍNH xuất nhập cảnh.

NGUYÊN TẮC TRẢ LỜI (PROCEDURE FOCUS):
✅ Hướng dẫn cụ thể từng bước thực hiện
✅ Nêu rõ hồ sơ, lệ phí, thời gian, địa điểm
✅ Thông tin thực tế từ Cổng dịch vụ công
✅ Tư vấn thực tiễn cho người dân

THÔNG TIN THỦ TỤC:
{context}

CÂU HỎI: {question}

YÊU CẦU: Hướng dẫn cụ thể thủ tục thực hiện, nêu rõ các bước.

TRẢ LỜI:"""

MIXED_CONTEXT_PROMPT = """Bạn là chuyên gia TƯ VẤN PHÁP LUẬT và THỦ TỤC xuất nhập cảnh.

NGUYÊN TẮC TRẢ LỜI (MIXED):
✅ Kết hợp căn cứ pháp lý + hướng dẫn thực tiễn
✅ Trích dẫn điều luật + giải thích thủ tục
✅ Đảm bảo tính chính xác và thực tiễn
✅ Phân biệt rõ "quy định pháp luật" vs "thủ tục thực hiện"

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {question}

YÊU CẦU: Trả lời đầy đủ cả khía cạnh pháp lý và thủ tục thực hiện.

TRẢ LỜI:"""

class LLMHandler:
    """LLM Handler với 3 prompt templates"""
    
    def __init__(self):
        self.config = config
        
        # Provider tracking
        self.providers = {
            'gemini': {'available': False, 'errors': 0},
            'gemma': {'available': False, 'errors': 0}
        }
        
        # Validation settings
        self.min_context_length = 60
        self.min_response_length = 30
        self.max_errors = 3
        
        self._init_providers()
    
    def _init_providers(self):
        """Initialize providers"""
        self._init_gemini()
        self._check_gemma()
    
    def _init_gemini(self):
        """Initialize Gemini"""
        if not GEMINI_AVAILABLE or not self.config.gemini_api_key:
            logger.warning("⚠️ Gemini not available")
            return
        
        try:
            genai.configure(api_key=self.config.gemini_api_key)
            self.gemini_model = genai.GenerativeModel(
                self.config.gemini_model,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.config.max_tokens,
                    temperature=self.config.temperature
                )
            )
            
            self.providers['gemini']['available'] = True
            logger.info("✅ Gemini configured")
            
        except Exception as e:
            logger.warning(f"⚠️ Gemini init failed: {e}")
    
    def _check_gemma(self):
        """Check Gemma availability"""
        try:
            response = requests.get(f"{self.config.ollama_url}/api/tags", timeout=3)
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                if any(self.config.ollama_model in name for name in model_names):
                    self.providers['gemma']['available'] = True
                    logger.info("✅ Gemma available")
                    
        except Exception as e:
            logger.warning(f"⚠️ Gemma check failed: {e}")
    
    def validate_content(self, context: str, query: str) -> Dict[str, Any]:
        """Simple content validation"""
        if not context or len(context.strip()) < self.min_context_length:
            return {
                'is_valid': False,
                'reason': 'Context quá ngắn',
                'should_respond': False
            }
        
        # Basic keyword overlap check
        import re
        query_words = set(re.findall(r'\b\w{3,}\b', query.lower()))
        context_words = set(re.findall(r'\b\w{3,}\b', context.lower()))
        overlap = len(query_words & context_words)
        
        if overlap < 1:
            return {
                'is_valid': False,
                'reason': 'Context không liên quan',
                'should_respond': False
            }
        
        return {
            'is_valid': True,
            'should_respond': True,
            'overlap_score': overlap / max(len(query_words), 1)
        }
    
    def _select_prompt_template(self, context: str) -> str:
        """SỬA LOGIC: Chọn prompt template phù hợp"""
        
        # Detect context type
        has_legal_section = '=== VĂN BẢN PHÁP LUẬT ===' in context
        has_procedure_section = '=== THỦ TỤC HÀNH CHÍNH ===' in context
        
        if has_legal_section and has_procedure_section:
            logger.info("🔀 Using MIXED_CONTEXT_PROMPT")
            return MIXED_CONTEXT_PROMPT
        
        elif has_legal_section:
            logger.info("⚖️ Using LEGAL_DOMINANT_PROMPT")
            return LEGAL_DOMINANT_PROMPT
        
        elif has_procedure_section:
            logger.info("📋 Using PROCEDURE_DOMINANT_PROMPT") 
            return PROCEDURE_DOMINANT_PROMPT
        
        else:
            # Fallback analysis
            context_lower = context.lower()
            legal_indicators = ['điều', 'khoản', 'luật số', 'nghị định']
            procedure_indicators = ['thủ tục', 'hồ sơ', 'lệ phí', 'thời hạn']
            
            legal_count = sum(1 for indicator in legal_indicators if indicator in context_lower)
            procedure_count = sum(1 for indicator in procedure_indicators if indicator in context_lower)
            
            if legal_count > procedure_count:
                logger.info("⚖️ Using LEGAL_DOMINANT_PROMPT (fallback)")
                return LEGAL_DOMINANT_PROMPT
            else:
                logger.info("📋 Using PROCEDURE_DOMINANT_PROMPT (fallback)")
                return PROCEDURE_DOMINANT_PROMPT
    
    async def generate_response(self, query: str, context: str) -> Dict[str, Any]:
        """Generate response với smart prompt selection"""
        
        # Validate content
        validation = self.validate_content(context, query)
        if not validation['should_respond']:
            return {
                'success': False,
                'response': '',
                'error': 'insufficient_content',
                'message': 'Không đủ thông tin để trả lời.'
            }
        
        # SỬA LOGIC: Select appropriate prompt template
        prompt_template = self._select_prompt_template(context)
        
        # Try providers in order
        for provider_name, provider_info in self.providers.items():
            if not provider_info['available']:
                continue
            
            try:
                if provider_name == 'gemini':
                    result = await self._generate_gemini(query, context, prompt_template)
                elif provider_name == 'gemma':
                    result = await self._generate_gemma(query, context, prompt_template)
                else:
                    continue
                
                if result['success']:
                    # Reset errors on success
                    self.providers[provider_name]['errors'] = 0
                    return result
                else:
                    # Track errors
                    self.providers[provider_name]['errors'] += 1
                    if self.providers[provider_name]['errors'] >= self.max_errors:
                        self.providers[provider_name]['available'] = False
                        logger.warning(f"❌ Disabled {provider_name} due to errors")
                    
            except Exception as e:
                logger.warning(f"⚠️ Provider {provider_name} failed: {e}")
                self.providers[provider_name]['errors'] += 1
                continue
        
        return {
            'success': False,
            'response': '',
            'error': 'all_providers_failed',
            'message': 'Không có AI model nào khả dụng.'
        }
    
    async def _generate_gemini(self, query: str, context: str, prompt_template: str) -> Dict[str, Any]:
        """Generate with Gemini using selected template"""
        try:
            # Build prompt with selected template
            prompt = prompt_template.format(
                context=context,
                question=query
            )
            
            # Generate
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt
            )
            
            if response and response.text:
                generated_text = response.text.strip()
                
                if self._validate_response(generated_text):
                    return {
                        'success': True,
                        'response': generated_text,
                        'provider': 'gemini',
                        'prompt_type': self._get_prompt_type(prompt_template)
                    }
                else:
                    return {
                        'success': False,
                        'error': 'poor_quality_response'
                    }
            else:
                return {
                    'success': False,
                    'error': 'empty_response'
                }
                
        except Exception as e:
            # Handle quota limits
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['quota', 'limit', 'rate']):
                self.providers['gemini']['available'] = False
            
            return {
                'success': False,
                'error': f"gemini_error: {e}"
            }
    
    async def _generate_gemma(self, query: str, context: str, prompt_template: str) -> Dict[str, Any]:
        """Generate with Gemma using selected template"""
        try:
            # Simple prompt for local model (reduce complexity)
            if '=== VĂN BẢN PHÁP LUẬT ===' in context:
                simple_prompt = f"Dựa vào quy định pháp luật sau, trả lời câu hỏi:\n\n{context}\n\nCÂU HỎI: {query}\n\nTRẢ LỜI:"
            else:
                simple_prompt = f"Dựa vào thông tin thủ tục sau, hướng dẫn cụ thể:\n\n{context}\n\nCÂU HỎI: {query}\n\nTRẢ LỜI:"
            
            payload = {
                "model": self.config.ollama_model,
                "prompt": simple_prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": 400,
                    "top_p": 0.9,
                    "num_ctx": 1500
                }
            }
            
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=25)
                async with session.post(
                    f"{self.config.ollama_url}/api/generate",
                    json=payload,
                    timeout=timeout
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        generated_text = result.get("response", "").strip()
                        
                        if generated_text and self._validate_response(generated_text):
                            return {
                                'success': True,
                                'response': generated_text,
                                'provider': 'gemma',
                                'prompt_type': 'simplified'
                            }
                        else:
                            return {
                                'success': False,
                                'error': 'poor_quality_response'
                            }
                    else:
                        return {
                            'success': False,
                            'error': f'api_error_{response.status}'
                        }
                        
        except Exception as e:
            return {
                'success': False,
                'error': f"gemma_error: {e}"
            }
    
    def _get_prompt_type(self, prompt_template: str) -> str:
        """Get prompt type name"""
        if prompt_template == LEGAL_DOMINANT_PROMPT:
            return 'legal_dominant'
        elif prompt_template == PROCEDURE_DOMINANT_PROMPT:
            return 'procedure_dominant'
        elif prompt_template == MIXED_CONTEXT_PROMPT:
            return 'mixed_context'
        else:
            return 'unknown'
    
    def _validate_response(self, response: str) -> bool:
        """Simple response validation"""
        # Minimum length check
        if len(response.strip()) < self.min_response_length:
            return False
        
        # Check for too many negative indicators
        negative_indicators = [
            'không có thông tin', 'không tìm thấy', 'không thể trả lời',
            'tôi không biết', 'xin lỗi'
        ]
        
        negative_count = sum(1 for indicator in negative_indicators if indicator in response.lower())
        if negative_count >= 2:
            return False
        
        # Check for some useful content
        useful_indicators = [
            'điều', 'khoản', 'thủ tục', 'hồ sơ', 'theo quy định',
            'lệ phí', 'thời gian', 'cơ quan', 'điều kiện'
        ]
        
        useful_count = sum(1 for indicator in useful_indicators if indicator in response.lower())
        return useful_count >= 1
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get provider status"""
        return {
            'providers': self.providers,
            'validation_settings': {
                'min_context_length': self.min_context_length,
                'min_response_length': self.min_response_length,
                'max_errors': self.max_errors
            }
        }
    
    def refresh_providers(self):
        """Refresh providers"""
        logger.info("🔄 Refreshing providers...")
        
        for provider in self.providers.values():
            provider['errors'] = 0
            provider['available'] = False
        
        self._init_providers()
        
        active = [name for name, info in self.providers.items() if info['available']]
        logger.info(f"✅ Active providers: {active}")