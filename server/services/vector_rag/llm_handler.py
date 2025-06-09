# server/services/vector_rag/llm_handler.py
"""
LLM Handler - FLEXIBLE: API + Local với Auto Fallback
"""
import asyncio
import aiohttp
import requests
from typing import Dict, Any, Optional, List
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
LEGAL_DOMINANT_PROMPT = """Bạn là chuyên gia pháp luật xuất nhập cảnh Việt Nam.

NGUYÊN TẮC TRẢ LỜI:
✅ TRẢ LỜI THẲNG - đúng trọng tâm câu hỏi
✅ TRÍCH DẪN CHÍNH XÁC - "Điều X Luật số Y/năm" + nội dung cụ thể  
✅ NGẮN GỌN - tối đa 2-3 đoạn
✅ KHÔNG suy đoán - chỉ dựa trên văn bản có sẵn

VĂN BẢN PHÁP LUẬT:
{context}

CÂU HỎI: {question}

YÊU CẦU: Trả lời ngắn gọn, trích dẫn chính xác điều luật.

TRẢ LỜI:"""

PROCEDURE_DOMINANT_PROMPT = """Bạn là chuyên viên thủ tục hành chính xuất nhập cảnh.

NGUYÊN TẮC TRẢ LỜI:
✅ TRẢ LỜI CỤ THỂ - hồ sơ, thời gian, địa điểm, lệ phí
✅ NGẮN GỌN - 2-3 đoạn, đi thẳng vào vấn đề
✅ THỰC TẾ - dựa trên thông tin chính thức
✅ CÓ CẤU TRÚC - để dễ đọc

THÔNG TIN THỦ TỤC:
{context}

CÂU HỎI: {question}

YÊU CẦU: Hướng dẫn ngắn gọn, cụ thể.

TRẢ LỜI:"""

MIXED_CONTEXT_PROMPT = """Bạn là chuyên gia tư vấn pháp luật và thủ tục xuất nhập cảnh.

NGUYÊN TẮC TRẢ LỜI:
✅ TRẢ LỜI TOÀN DIỆN nhưng NGẮN GỌN
✅ PHÂN BIỆT rõ: "Theo pháp luật" vs "Thủ tục thực tế"  
✅ TRÍCH DẪN CHÍNH XÁC văn bản pháp luật
✅ TỐI ĐA 3 đoạn

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {question}

YÊU CẦU: Trả lời đầy đủ nhưng súc tích.

TRẢ LỜI:"""

class LLMHandler:
    """FLEXIBLE LLM Handler - API + Local với Auto Fallback"""
    
    def __init__(self):
        self.config = config
        
        # THÊM: Flexible settings
        self.use_api_first = True  # Ưu tiên API trước
        self.auto_fallback = True  # Tự động fallback khi API fail
        self.force_local_only = False  # Force chỉ dùng local
        self.api_disabled = False  # Tạm tắt API
        
        # Provider tracking với enhanced info
        self.providers = {
            'gemini': {
                'available': False, 
                'errors': 0,
                'type': 'api',
                'cost_per_request': 0.001,
                'last_error': None,
                'quota_exceeded': False
            },
            'gemma': {
                'available': False, 
                'errors': 0,
                'type': 'local',
                'cost_per_request': 0.0,
                'last_error': None,
                'model_loaded': False
            }
        }
        
        # Usage stats
        self.usage_stats = {
            'gemini_requests': 0,
            'gemma_requests': 0,
            'api_cost_estimate': 0.0,
            'fallback_count': 0,
            'session_start': datetime.now()
        }
        
        # Validation settings
        self.min_context_length = 60
        self.min_response_length = 30
        self.max_errors = 3
        
        self._init_providers()
    
    def set_mode(self, mode: str):
        """THÊM: Set LLM mode"""
        mode = mode.lower()
        
        if mode == 'api_first':
            self.use_api_first = True
            self.force_local_only = False
            self.api_disabled = False
            logger.info("🌐 Mode: API First (fallback to local)")
            
        elif mode == 'local_only':
            self.use_api_first = False
            self.force_local_only = True
            self.api_disabled = True
            logger.info("🏠 Mode: Local Only (Gemma:2b)")
            
        elif mode == 'local_first':
            self.use_api_first = False
            self.force_local_only = False
            self.api_disabled = False
            logger.info("🏠 Mode: Local First (fallback to API)")
            
        elif mode == 'api_only':
            self.use_api_first = True
            self.force_local_only = False
            self.api_disabled = False
            # Disable local fallback
            self.auto_fallback = False
            logger.info("☁️ Mode: API Only (no fallback)")
            
        else:
            logger.warning(f"❌ Unknown mode: {mode}")
    
    def disable_api(self, reason: str = "Manual disable"):
        """THÊM: Tạm tắt API"""
        self.api_disabled = True
        self.providers['gemini']['available'] = False
        logger.info(f"⛔ API Disabled: {reason}")
    
    def enable_api(self):
        """THÊM: Bật lại API"""
        self.api_disabled = False
        self._init_gemini()  # Reinitialize
        logger.info("✅ API Enabled")
    
    def _init_providers(self):
        """Initialize providers với flexible logic"""
        # Always try to init both
        if not self.api_disabled:
            self._init_gemini()
        
        self._check_gemma()
        
        # Log available providers
        available = [name for name, info in self.providers.items() if info['available']]
        logger.info(f"🔧 Available providers: {available}")
        
        if not available:
            logger.warning("⚠️ No providers available!")
    
    def _init_gemini(self):
        """Initialize Gemini với enhanced error handling"""
        if self.force_local_only or self.api_disabled:
            logger.info("⛔ Gemini disabled by config")
            self.providers['gemini']['available'] = False
            return
        
        if not GEMINI_AVAILABLE:
            logger.warning("⚠️ google.generativeai not installed")
            self.providers['gemini']['available'] = False
            return
        
        if not self.config.gemini_api_key:
            logger.info("🔑 No Gemini API key - using local only")
            self.providers['gemini']['available'] = False
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
            self.providers['gemini']['errors'] = 0
            self.providers['gemini']['quota_exceeded'] = False
            logger.info("✅ Gemini API configured")
            
        except Exception as e:
            logger.warning(f"⚠️ Gemini init failed: {e}")
            self.providers['gemini']['available'] = False
            self.providers['gemini']['last_error'] = str(e)
    
    def _check_gemma(self):
        """Check Gemma với enhanced detection"""
        try:
            response = requests.get(f"{self.config.ollama_url}/api/tags", timeout=5)
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                # Check if our model exists
                target_model = self.config.ollama_model
                available_models = [name for name in model_names if target_model in name]
                
                if available_models:
                    self.providers['gemma']['available'] = True
                    self.providers['gemma']['model_loaded'] = True
                    self.providers['gemma']['errors'] = 0
                    logger.info(f"✅ Gemma available: {available_models[0]}")
                else:
                    logger.warning(f"⚠️ Model {target_model} not found. Available: {model_names}")
                    
            else:
                logger.warning(f"⚠️ Ollama API error: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️ Gemma check failed: {e}")
            self.providers['gemma']['available'] = False
            self.providers['gemma']['last_error'] = str(e)
    
    def get_provider_order(self) -> List[str]:
        """THÊM: Get provider order dựa trên mode"""
        if self.force_local_only:
            return ['gemma']
        
        if self.use_api_first:
            return ['gemini', 'gemma']
        else:
            return ['gemma', 'gemini']
    
    async def generate_response(self, query: str, context: str) -> Dict[str, Any]:
        """Generate response với flexible provider selection"""
        
        # Validate content
        validation = self.validate_content(context, query)
        if not validation['should_respond']:
            return {
                'success': False,
                'response': '',
                'error': 'insufficient_content',
                'message': 'Không đủ thông tin để trả lời.'
            }
        
        # Select appropriate prompt template
        prompt_template = self._select_prompt_template(context)
        
        # THÊM: Try providers theo order đã config
        provider_order = self.get_provider_order()
        
        for provider_name in provider_order:
            provider_info = self.providers[provider_name]
            
            if not provider_info['available']:
                logger.debug(f"⏭️ Skipping {provider_name} - not available")
                continue
            
            # Skip API if disabled
            if provider_name == 'gemini' and self.api_disabled:
                logger.debug("⏭️ Skipping Gemini - API disabled")
                continue
            
            try:
                logger.info(f"🔄 Trying {provider_name}...")
                
                if provider_name == 'gemini':
                    result = await self._generate_gemini(query, context, prompt_template)
                elif provider_name == 'gemma':
                    result = await self._generate_gemma(query, context, prompt_template)
                else:
                    continue
                
                if result['success']:
                    # Success - reset errors và update stats
                    self.providers[provider_name]['errors'] = 0
                    self._update_usage_stats(provider_name, True)
                    
                    result['provider_used'] = provider_name
                    result['provider_type'] = provider_info['type']
                    
                    logger.info(f"✅ Success with {provider_name}")
                    return result
                
                else:
                    # Provider failed
                    self._handle_provider_error(provider_name, result.get('error', 'unknown'))
                    
                    # If không có fallback, return error
                    if not self.auto_fallback:
                        return result
                    
            except Exception as e:
                logger.warning(f"⚠️ Provider {provider_name} exception: {e}")
                self._handle_provider_error(provider_name, str(e))
                
                if not self.auto_fallback:
                    break
                continue
        
        # All providers failed
        self.usage_stats['fallback_count'] += 1
        
        return {
            'success': False,
            'response': '',
            'error': 'all_providers_failed',
            'message': 'Tất cả AI models đều không khả dụng.',
            'attempted_providers': provider_order,
            'provider_status': {name: info['available'] for name, info in self.providers.items()}
        }
    
    def _handle_provider_error(self, provider_name: str, error: str):
        """THÊM: Handle provider errors với smart detection"""
        provider = self.providers[provider_name]
        provider['errors'] += 1
        provider['last_error'] = error
        
        # Detect quota/limit errors for API
        if provider_name == 'gemini':
            error_lower = error.lower()
            quota_keywords = ['quota', 'limit', 'rate', 'exceeded', 'billing', 'usage']
            
            if any(keyword in error_lower for keyword in quota_keywords):
                provider['quota_exceeded'] = True
                self.api_disabled = True  # Auto disable API
                logger.warning(f"💰 Gemini quota exceeded - auto switching to local")
            
        # Disable provider if too many errors
        if provider['errors'] >= self.max_errors:
            provider['available'] = False
            logger.warning(f"❌ Disabled {provider_name} due to errors: {provider['errors']}")
    
    def _update_usage_stats(self, provider_name: str, success: bool):
        """THÊM: Update usage statistics"""
        if provider_name == 'gemini':
            self.usage_stats['gemini_requests'] += 1
            if success:
                self.usage_stats['api_cost_estimate'] += self.providers['gemini']['cost_per_request']
        
        elif provider_name == 'gemma':
            self.usage_stats['gemma_requests'] += 1
    
    async def _generate_gemini(self, query: str, context: str, prompt_template: str) -> Dict[str, Any]:
        """Generate with Gemini với enhanced error handling"""
        try:
            # Build prompt with selected template
            prompt = prompt_template.format(
                context=context,
                question=query
            )
            
            # Generate với timeout
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
                        'prompt_type': self._get_prompt_type(prompt_template),
                        'cost_estimate': self.providers['gemini']['cost_per_request']
                    }
                else:
                    return {
                        'success': False,
                        'error': 'poor_quality_response',
                        'response_length': len(generated_text)
                    }
            else:
                return {
                    'success': False,
                    'error': 'empty_response'
                }
                
        except Exception as e:
            # Enhanced error detection
            error_msg = str(e).lower()
            
            if any(keyword in error_msg for keyword in ['quota', 'limit', 'rate', 'billing']):
                return {
                    'success': False,
                    'error': 'quota_exceeded',
                    'message': 'API quota exceeded'
                }
            elif 'network' in error_msg or 'timeout' in error_msg:
                return {
                    'success': False,
                    'error': 'network_error',
                    'message': 'Network connection failed'
                }
            else:
                return {
                    'success': False,
                    'error': f"gemini_error: {e}"
                }
    
    async def _generate_gemma(self, query: str, context: str, prompt_template: str) -> Dict[str, Any]:
        """Generate with Gemma với enhanced handling"""
        try:
            # Enhanced prompt for Gemma
            if '=== VĂN BẢN PHÁP LUẬT ===' in context:
                simple_prompt = f"Dựa vào quy định pháp luật sau, trả lời ngắn gọn và chính xác:\n\n{context}\n\nCÂU HỎI: {query}\n\nTRẢ LỜI:"
            else:
                simple_prompt = f"Dựa vào thông tin thủ tục sau, hướng dẫn cụ thể:\n\n{context}\n\nCÂU HỎI: {query}\n\nTRẢ LỜI:"
            
            payload = {
                "model": self.config.ollama_model,
                "prompt": simple_prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": 500,  # Tăng lên để có response đầy đủ hơn
                    "top_p": 0.9,
                    "num_ctx": 2048,  # Tăng context window
                    "repeat_penalty": 1.1
                }
            }
            
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=30)  # Tăng timeout
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
                                'prompt_type': 'local_optimized',
                                'model': self.config.ollama_model,
                                'cost_estimate': 0.0
                            }
                        else:
                            return {
                                'success': False,
                                'error': 'poor_quality_response',
                                'response_length': len(generated_text)
                            }
                    else:
                        return {
                            'success': False,
                            'error': f'ollama_api_error_{response.status}'
                        }
                        
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': 'local_model_timeout'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"gemma_error: {e}"
            }
    
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
            logger.debug("🔀 Using MIXED_CONTEXT_PROMPT")
            return MIXED_CONTEXT_PROMPT
        
        elif has_legal_section:
            logger.debug("⚖️ Using LEGAL_DOMINANT_PROMPT")
            return LEGAL_DOMINANT_PROMPT
        
        elif has_procedure_section:
            logger.debug("📋 Using PROCEDURE_DOMINANT_PROMPT") 
            return PROCEDURE_DOMINANT_PROMPT
        
        else:
            # Fallback analysis
            context_lower = context.lower()
            legal_indicators = ['điều', 'khoản', 'luật số', 'nghị định']
            procedure_indicators = ['thủ tục', 'hồ sơ', 'lệ phí', 'thời hạn']
            
            legal_count = sum(1 for indicator in legal_indicators if indicator in context_lower)
            procedure_count = sum(1 for indicator in procedure_indicators if indicator in context_lower)
            
            if legal_count > procedure_count:
                logger.debug("⚖️ Using LEGAL_DOMINANT_PROMPT (fallback)")
                return LEGAL_DOMINANT_PROMPT
            else:
                logger.debug("📋 Using PROCEDURE_DOMINANT_PROMPT (fallback)")
                return PROCEDURE_DOMINANT_PROMPT
    
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
        """Enhanced response validation"""
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
        
        # Check for proper legal citations
        has_proper_citation = any(pattern in response.lower() for pattern in [
            'điều', 'luật số', 'nghị định', 'thông tư', 'theo quy định'
        ])
        
        # Check response length (should be concise)
        if len(response) > 2000:  # Too long
            logger.debug("Response too long, may not be concise enough")
        
        # Check for useful content
        useful_indicators = [
            'điều', 'khoản', 'thủ tục', 'hồ sơ', 'theo quy định',
            'lệ phí', 'thời gian', 'cơ quan', 'điều kiện', 'được', 'không được'
        ]
        
        useful_count = sum(1 for indicator in useful_indicators if indicator in response.lower())
        return useful_count >= 2 and (has_proper_citation or 'thủ tục' in response.lower())
    
    def get_provider_status(self) -> Dict[str, Any]:
        """THÊM: Enhanced provider status"""
        session_duration = (datetime.now() - self.usage_stats['session_start']).total_seconds()
        
        return {
            'providers': self.providers,
            'current_mode': {
                'use_api_first': self.use_api_first,
                'force_local_only': self.force_local_only,
                'api_disabled': self.api_disabled,
                'auto_fallback': self.auto_fallback
            },
            'usage_stats': {
                **self.usage_stats,
                'session_duration_minutes': session_duration / 60,
                'requests_per_minute': (self.usage_stats['gemini_requests'] + self.usage_stats['gemma_requests']) / max(session_duration / 60, 1)
            },
            'validation_settings': {
                'min_context_length': self.min_context_length,
                'min_response_length': self.min_response_length,
                'max_errors': self.max_errors
            }
        }
    
    def refresh_providers(self):
        """THÊM: Enhanced refresh với stats reset"""
        logger.info("🔄 Refreshing providers...")
        
        # Reset provider states
        for provider in self.providers.values():
            provider['errors'] = 0
            provider['available'] = False
            provider['last_error'] = None
            
        # Reset quota flags
        self.providers['gemini']['quota_exceeded'] = False
        
        # Re-enable API if was auto-disabled
        if self.api_disabled and not self.force_local_only:
            self.api_disabled = False
            logger.info("🔄 Re-enabling API after refresh")
        
        # Reinitialize
        self._init_providers()
        
        active = [name for name, info in self.providers.items() if info['available']]
        logger.info(f"✅ Active providers after refresh: {active}")
    
    # THÊM: Convenience methods
    def use_api_only(self):
        """Force API only mode"""
        self.set_mode('api_only')
    
    def use_local_only(self):
        """Force local only mode"""
        self.set_mode('local_only')
    
    def use_hybrid_mode(self, api_first: bool = True):
        """Hybrid mode với preference"""
        if api_first:
            self.set_mode('api_first')
        else:
            self.set_mode('local_first')
    
    def get_cost_estimate(self) -> float:
        """Get estimated API cost for this session"""
        return self.usage_stats['api_cost_estimate']