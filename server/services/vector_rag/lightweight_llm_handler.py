# server/services/vector_rag/lightweight_llm_handler.py
"""
LLM Handler siêu nhẹ với Gemini API + Gemma:2b backup
Smart fallback strategy cho độ tin cậy cao
"""
import os
import json
import time
import asyncio
import aiohttp
import requests
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .lightweight_config import LLM_CONFIG, XUATNHAPCANH_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class LightweightLLMHandler:
    """LLM Handler siêu nhẹ với multi-provider fallback"""
    
    def __init__(self, config=None):
        self.config = config or LLM_CONFIG
        
        # Provider status tracking
        self.provider_status = {
            'gemini': {'available': False, 'last_check': None, 'error_count': 0},
            'ollama': {'available': False, 'last_check': None, 'error_count': 0}
        }
        
        # Rate limiting
        self.rate_limits = {
            'gemini': {'requests_per_minute': 60, 'requests': [], 'tokens_per_minute': 32000, 'tokens': []},
            'ollama': {'requests_per_minute': 30, 'requests': [], 'tokens_per_minute': 8000, 'tokens': []}
        }
        
        # Initialize providers
        self._initialize_gemini()
        self._check_ollama_availability()
        
        # Response cache
        self.response_cache = {}
        self.cache_ttl = 1800  # 30 minutes
    
    def _initialize_gemini(self):
        """Khởi tạo Gemini API"""
        if not GEMINI_AVAILABLE:
            logger.warning("⚠️ google-generativeai not installed")
            return
        
        api_key = self.config.gemini_api_key or os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.warning("⚠️ GEMINI_API_KEY not found")
            return
        
        try:
            genai.configure(api_key=api_key)
            self.gemini_model = genai.GenerativeModel(self.config.gemini_model)
            
            # Test connection
            test_response = self.gemini_model.generate_content(
                "Test connection",
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=10,
                    temperature=0.1
                )
            )
            
            if test_response.text:
                self.provider_status['gemini']['available'] = True
                self.provider_status['gemini']['last_check'] = datetime.now()
                logger.info("✅ Gemini API initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Gemini initialization failed: {e}")
            self.provider_status['gemini']['available'] = False
    
    def _check_ollama_availability(self):
        """Kiểm tra Ollama availability"""
        try:
            response = requests.get(
                f"{self.config.ollama_url}/api/tags",
                timeout=5
            )
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m.get('name', '') for m in models]
                
                if any(self.config.ollama_model in name for name in model_names):
                    self.provider_status['ollama']['available'] = True
                    self.provider_status['ollama']['last_check'] = datetime.now()
                    logger.info(f"✅ Ollama model {self.config.ollama_model} available")
                else:
                    logger.warning(f"⚠️ Ollama model {self.config.ollama_model} not found")
                    logger.info(f"📋 Available models: {model_names}")
            
        except Exception as e:
            logger.warning(f"⚠️ Ollama not available: {e}")
            self.provider_status['ollama']['available'] = False
    
    async def generate_async(self, prompt: str, context: str = "", question: str = "") -> Dict[str, Any]:
        """Generate response với smart fallback strategy"""
        
        # Prepare full prompt
        if context and question:
            full_prompt = XUATNHAPCANH_PROMPT_TEMPLATE.format(
                context=context,
                question=question
            )
        else:
            full_prompt = prompt
        
        # Try providers in order
        providers = []
        if self.provider_status['gemini']['available']:
            providers.append('gemini')
        if self.provider_status['ollama']['available']:
            providers.append('ollama')
        
        if not providers:
            return {
                'success': False,
                'response': "❌ Không có LLM provider nào khả dụng. Vui lòng kiểm tra cấu hình.",
                'error': "No providers available"
            }
        
        # Try providers in order
        last_error = None
        for provider in providers:
            try:
                logger.info(f"🤖 Trying provider: {provider}")
                
                if provider == 'gemini':
                    result = await self._generate_gemini_async(full_prompt)
                elif provider == 'ollama':
                    result = await self._generate_ollama_async(full_prompt)
                else:
                    continue
                
                if result['success']:
                    logger.info(f"✅ Generated response using {provider}")
                    return result
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️ Provider {provider} failed: {e}")
                continue
        
        # All providers failed
        return {
            'success': False,
            'response': f"❌ Tất cả LLM providers đều thất bại. Lỗi cuối: {last_error}",
            'error': last_error
        }
    
    async def _generate_gemini_async(self, prompt: str) -> Dict[str, Any]:
        """Generate với Gemini API (async)"""
        if not self.provider_status['gemini']['available']:
            raise Exception("Gemini not available")
        
        try:
            # Sử dụng asyncio.to_thread cho sync API
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.config.max_tokens,
                    temperature=self.config.temperature,
                )
            )
            
            if response.text:
                return {
                    'success': True,
                    'response': response.text.strip(),
                    'provider': 'gemini',
                    'tokens_used': len(response.text.split()) + len(prompt.split())
                }
            else:
                raise Exception("Empty response from Gemini")
                
        except Exception as e:
            self.provider_status['gemini']['error_count'] += 1
            logger.error(f"❌ Gemini generation failed: {e}")
            raise
    
    async def _generate_ollama_async(self, prompt: str) -> Dict[str, Any]:
        """Generate với Ollama API (async)"""
        if not self.provider_status['ollama']['available']:
            raise Exception("Ollama not available")
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.config.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens,
                        "top_p": 0.9
                    }
                }
                
                timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                async with session.post(
                    f"{self.config.ollama_url}/api/generate",
                    json=payload,
                    timeout=timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        generated_text = result.get("response", "").strip()
                        
                        if generated_text:
                            return {
                                'success': True,
                                'response': generated_text,
                                'provider': 'ollama',
                                'tokens_used': len(generated_text.split()) + len(prompt.split())
                            }
                        else:
                            raise Exception("Empty response from Ollama")
                    else:
                        raise Exception(f"Ollama API error: {response.status}")
                        
        except Exception as e:
            self.provider_status['ollama']['error_count'] += 1
            logger.error(f"❌ Ollama generation failed: {e}")
            raise
    
    def generate(self, prompt: str, context: str = "", question: str = "") -> Dict[str, Any]:
        """Sync wrapper cho generate_async"""
        return asyncio.run(self.generate_async(prompt, context, question))
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Lấy status của providers"""
        return {
            'providers': self.provider_status,
            'cache_size': len(self.response_cache)
        }
    
    def clear_cache(self):
        """Xóa response cache"""
        self.response_cache = {}
        logger.info("🗑️ LLM response cache cleared")
    
    def refresh_providers(self):
        """Refresh availability của tất cả providers"""
        logger.info("🔄 Refreshing provider status...")
        self._initialize_gemini()
        self._check_ollama_availability()

class XuatNhapCanhPromptBuilder:
    """Builder cho prompts chuyên biệt xuất nhập cảnh"""
    
    def __init__(self):
        self.base_template = XUATNHAPCANH_PROMPT_TEMPLATE
    
    def detect_question_type(self, question: str) -> str:
        """Detect loại câu hỏi để chọn template phù hợp"""
        question_lower = question.lower()
        
        visa_keywords = ['visa', 'thị thực', 'miễn thị', 'nhập cảnh', 'xuất cảnh']
        procedure_keywords = ['thủ tục', 'hồ sơ', 'cách làm', 'làm thế nào', 'ở đâu']
        legal_keywords = ['điều', 'luật', 'quy định', 'nghị định', 'thông tư', 'vi phạm']
        
        if any(keyword in question_lower for keyword in legal_keywords):
            return 'legal'
        elif any(keyword in question_lower for keyword in visa_keywords):
            return 'visa'
        elif any(keyword in question_lower for keyword in procedure_keywords):
            return 'procedure'
        else:
            return 'general'

class ResponseValidator:
    """Validate chất lượng response"""
    
    @staticmethod
    def validate_response(response: str, question: str) -> Dict[str, Any]:
        """Validate response quality"""
        validation = {
            'is_valid': True,
            'confidence': 1.0,
            'issues': [],
            'suggestions': []
        }
        
        # Check length
        if len(response) < 50:
            validation['issues'].append("Response too short")
            validation['confidence'] -= 0.3
        
        # Check Vietnamese content
        vietnamese_chars = 'áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđ'
        vietnamese_count = sum(1 for char in response.lower() if char in vietnamese_chars)
        alpha_count = sum(1 for char in response if char.isalpha())
        
        if alpha_count > 0:
            vietnamese_ratio = vietnamese_count / alpha_count
            if vietnamese_ratio < 0.8:
                validation['issues'].append("Low Vietnamese content ratio")
                validation['confidence'] -= 0.2
        
        validation['is_valid'] = validation['confidence'] > 0.6
        return validation