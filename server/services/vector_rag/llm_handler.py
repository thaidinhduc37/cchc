# server/services/rag/llm_handler.py
"""
LLM Handler - OPTIMIZED & SIMPLIFIED
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

from services.vector_rag.rag_config import config, ENHANCED_LEGAL_PROMPT

logger = logging.getLogger(__name__)

class LLMHandler:
    """Simplified LLM Handler with basic validation"""
    
    def __init__(self):
        self.config = config
        
        # Provider tracking
        self.providers = {
            'gemini': {'available': False, 'errors': 0},
            'gemma': {'available': False, 'errors': 0}
        }
        
        # Simplified validation settings
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
    
    async def generate_response(self, query: str, context: str) -> Dict[str, Any]:
        """Generate response with simplified flow"""
        
        # Validate content
        validation = self.validate_content(context, query)
        if not validation['should_respond']:
            return {
                'success': False,
                'response': '',
                'error': 'insufficient_content',
                'message': 'Không đủ thông tin để trả lời.'
            }
        
        # Try providers in order
        for provider_name, provider_info in self.providers.items():
            if not provider_info['available']:
                continue
            
            try:
                if provider_name == 'gemini':
                    result = await self._generate_gemini(query, context)
                elif provider_name == 'gemma':
                    result = await self._generate_gemma(query, context)
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
    
    async def _generate_gemini(self, query: str, context: str) -> Dict[str, Any]:
        """Generate with Gemini"""
        try:
            # Build prompt
            prompt = ENHANCED_LEGAL_PROMPT.format(
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
                        'provider': 'gemini'
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
    
    async def _generate_gemma(self, query: str, context: str) -> Dict[str, Any]:
        """Generate with Gemma local"""
        try:
            # Simple prompt for local model
            prompt = f"""Dựa vào thông tin sau, trả lời câu hỏi:

THÔNG TIN:
{context}

CÂU HỎI: {query}

TRẢ LỜI:"""
            
            payload = {
                "model": self.config.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": 400,  # Limit for speed
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
                                'provider': 'gemma'
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