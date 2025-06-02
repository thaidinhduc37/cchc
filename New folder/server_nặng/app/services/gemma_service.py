"""
🧠 Gemma Service - Wrapper cho Gemma:2B model
Support both local Ollama và cloud deployment
"""

import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ModelProvider(Enum):
    OLLAMA_LOCAL = "ollama_local"
    OLLAMA_CLOUD = "ollama_cloud" 
    GEMINI_API = "gemini_api"
    OPENAI_API = "openai_api"

class ResponseFormat(Enum):
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"

@dataclass
class GenerationConfig:
    """Configuration for text generation"""
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop_sequences: List[str] = None
    format: ResponseFormat = ResponseFormat.TEXT

@dataclass
class ModelResponse:
    """Response from model"""
    content: str
    tokens_used: int
    generation_time: float
    model_used: str
    confidence: float
    metadata: Dict[str, Any] = None

class GemmaService:
    """
    Gemma Service - Unified interface for Gemma:2B model
    Supports multiple deployment methods với fallback
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.primary_provider = ModelProvider(config.get("primary_provider", "ollama_local"))
        self.fallback_providers = [ModelProvider(p) for p in config.get("fallback_providers", [])]
        
        # Provider configurations
        self.ollama_config = config.get("ollama", {})
        self.gemini_config = config.get("gemini", {})
        self.openai_config = config.get("openai", {})
        
        # Model settings
        self.model_name = config.get("model_name", "gemma:2b")
        self.default_generation_config = GenerationConfig(**config.get("generation", {}))
        
        # Performance tracking
        self.request_stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0,
            "provider_usage": {provider.value: 0 for provider in ModelProvider}
        }
        
        # Cache for prompts (optional)
        self.enable_cache = config.get("enable_cache", False)
        self.prompt_cache = {} if self.enable_cache else None
        
        # Load system prompts
        self.system_prompts = self._load_system_prompts()

    async def generate_legal_answer(self, query: str, context: str, 
                                  domain: str = "general",
                                  config: Optional[GenerationConfig] = None) -> ModelResponse:
        """
        Generate legal answer với context
        
        Args:
            query: User query
            context: Legal context/documents
            domain: Domain context
            config: Generation configuration
            
        Returns:
            ModelResponse với generated answer
        """
        try:
            # Build prompt
            prompt = self._build_legal_prompt(query, context, domain)
            
            # Generate response
            response = await self.generate_text(prompt, config)
            
            # Post-process legal response
            processed_response = self._post_process_legal_response(response, query, domain)
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Error generating legal answer: {e}")
            return ModelResponse(
                content=f"Xin lỗi, không thể tạo câu trả lời: {str(e)}",
                tokens_used=0,
                generation_time=0,
                model_used="error",
                confidence=0.0
            )

    async def generate_flow_guidance(self, step_info: Dict[str, Any], 
                                   user_context: Dict[str, Any],
                                   config: Optional[GenerationConfig] = None) -> ModelResponse:
        """
        Generate enhanced flow guidance
        
        Args:
            step_info: Current step information
            user_context: User context and history
            config: Generation configuration
            
        Returns:
            ModelResponse với enhanced guidance
        """
        try:
            # Build flow prompt
            prompt = self._build_flow_prompt(step_info, user_context)
            
            # Generate response với specific config cho flow
            flow_config = config or GenerationConfig(
                max_tokens=256,
                temperature=0.3,  # Lower temperature for consistent guidance
                format=ResponseFormat.TEXT
            )
            
            response = await self.generate_text(prompt, flow_config)
            
            # Post-process flow response
            processed_response = self._post_process_flow_response(response, step_info)
            
            return processed_response
            
        except Exception as e:
            logger.error(f"Error generating flow guidance: {e}")
            return ModelResponse(
                content="Xin lỗi, không thể tạo hướng dẫn chi tiết.",
                tokens_used=0,
                generation_time=0,
                model_used="error",
                confidence=0.0
            )

    async def generate_text(self, prompt: str, 
                          config: Optional[GenerationConfig] = None) -> ModelResponse:
        """
        Core text generation method với fallback
        
        Args:
            prompt: Input prompt
            config: Generation configuration
            
        Returns:
            ModelResponse
        """
        start_time = time.time()
        self.request_stats["total_requests"] += 1
        
        generation_config = config or self.default_generation_config
        
        # Try primary provider first
        providers_to_try = [self.primary_provider] + self.fallback_providers
        
        for provider in providers_to_try:
            try:
                response = await self._generate_with_provider(prompt, generation_config, provider)
                
                # Track success
                generation_time = time.time() - start_time
                self.request_stats["successful_requests"] += 1
                self.request_stats["provider_usage"][provider.value] += 1
                self._update_avg_response_time(generation_time)
                
                response.generation_time = generation_time
                response.model_used = f"{provider.value}:{self.model_name}"
                
                return response
                
            except Exception as e:
                logger.warning(f"Provider {provider.value} failed: {e}")
                continue
        
        # All providers failed
        self.request_stats["failed_requests"] += 1
        raise Exception("All model providers failed")

    async def _generate_with_provider(self, prompt: str, config: GenerationConfig, 
                                     provider: ModelProvider) -> ModelResponse:
        """Generate text với specific provider"""
        
        if provider == ModelProvider.OLLAMA_LOCAL:
            return await self._generate_ollama(prompt, config, local=True)
        elif provider == ModelProvider.OLLAMA_CLOUD:
            return await self._generate_ollama(prompt, config, local=False)
        elif provider == ModelProvider.GEMINI_API:
            return await self._generate_gemini(prompt, config)
        elif provider == ModelProvider.OPENAI_API:
            return await self._generate_openai(prompt, config)
        else:
            raise ValueError(f"Unknown provider: {provider}")

    async def _generate_ollama(self, prompt: str, config: GenerationConfig, 
                              local: bool = True) -> ModelResponse:
        """Generate using Ollama (local or cloud)"""
        
        base_url = self.ollama_config.get("local_url", "http://localhost:11434") if local else self.ollama_config.get("cloud_url")
        
        if not base_url:
            raise ValueError("Ollama URL not configured")
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "repeat_penalty": config.repeat_penalty,
                "num_predict": config.max_tokens
            },
            "stream": False
        }
        
        if config.stop_sequences:
            payload["options"]["stop"] = config.stop_sequences
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    raise Exception(f"Ollama API error: {response.status}")
                
                result = await response.json()
                
                return ModelResponse(
                    content=result.get("response", ""),
                    tokens_used=result.get("eval_count", 0) + result.get("prompt_eval_count", 0),
                    generation_time=0,  # Will be set by caller
                    model_used=self.model_name,
                    confidence=0.8,  # Default confidence for Ollama
                    metadata={
                        "eval_count": result.get("eval_count", 0),
                        "prompt_eval_count": result.get("prompt_eval_count", 0),
                        "eval_duration": result.get("eval_duration", 0),
                        "provider": "ollama_local" if local else "ollama_cloud"
                    }
                )

    async def _generate_gemini(self, prompt: str, config: GenerationConfig) -> ModelResponse:
        """Generate using Gemini API"""
        
        api_key = self.gemini_config.get("api_key")
        if not api_key:
            raise ValueError("Gemini API key not configured")
        
        # This is a placeholder - actual implementation would use Google's Gemini API
        # For now, fallback to a simple response
        raise NotImplementedError("Gemini API integration not implemented yet")

    async def _generate_openai(self, prompt: str, config: GenerationConfig) -> ModelResponse:
        """Generate using OpenAI API (fallback)"""
        
        api_key = self.openai_config.get("api_key")
        if not api_key:
            raise ValueError("OpenAI API key not configured")
        
        # This is a placeholder for OpenAI integration
        raise NotImplementedError("OpenAI API integration not implemented yet")

    def _build_legal_prompt(self, query: str, context: str, domain: str) -> str:
        """Build prompt cho legal Q&A"""
        
        system_prompt = self.system_prompts.get("legal_qa", "")
        domain_context = self._get_domain_context(domain)
        
        prompt = f"""{system_prompt}

LĨNH VỰC: {domain_context}

NGỮ CẢNH PHÁP LÝ:
{context}

CÂU HỎI: {query}

HƯỚNG DẪN:
- Trả lời chính xác dựa trên ngữ cảnh pháp lý được cung cấp
- Sử dụng ngôn ngữ dễ hiểu, thân thiện
- Nếu không chắc chắn, hãy nói rõ và đề xuất tìm hiểu thêm
- Luôn đề cập đến nguồn pháp lý nếu có

TRẢ LỜI:"""

        return prompt

    def _build_flow_prompt(self, step_info: Dict[str, Any], user_context: Dict[str, Any]) -> str:
        """Build prompt cho flow guidance"""
        
        system_prompt = self.system_prompts.get("flow_guidance", "")
        
        prompt = f"""{system_prompt}

BƯỚC HIỆN TẠI:
Tên: {step_info.get('name', '')}
Mô tả: {step_info.get('description', '')}
Số bước: {step_info.get('step_number', '')} / {step_info.get('total_steps', '')}

NGỮ CẢNH NGƯỜI DÙNG:
Lượt tương tác: {user_context.get('total_interactions', 0)}
Lịch sử: {user_context.get('recent_activity', 'Không có')}

NHIỆM VỤ:
Cung cấp lời giải thích bổ sung, động viên và hướng dẫn chi tiết cho bước này.
Giữ tone thân thiện, hỗ trợ và động viên người dùng.

HƯỚNG DẪN BỔ SUNG:"""

        return prompt

    def _post_process_legal_response(self, response: ModelResponse, query: str, domain: str) -> ModelResponse:
        """Post-process legal response"""
        
        content = response.content.strip()
        
        # Add disclaimers for legal content
        if domain in ["xuatnhapcanh", "cancuoc"]:
            content += "\n\n💡 *Lưu ý: Thông tin này chỉ mang tính chất tham khảo. Vui lòng liên hệ cơ quan chức năng để được hướng dẫn chính thức.*"
        
        # Enhance confidence based on content quality
        confidence = response.confidence
        if "không chắc chắn" in content.lower() or "không rõ" in content.lower():
            confidence *= 0.7
        elif "theo quy định" in content.lower() or "luật" in content.lower():
            confidence = min(confidence * 1.1, 1.0)
        
        response.content = content
        response.confidence = confidence
        
        return response

    def _post_process_flow_response(self, response: ModelResponse, step_info: Dict[str, Any]) -> ModelResponse:
        """Post-process flow guidance response"""
        
        content = response.content.strip()
        
        # Ensure encouraging tone
        if not any(word in content.lower() for word in ["tốt", "tuyệt vời", "hoàn thành", "thành công"]):
            content = "👍 " + content
        
        # Add navigation hints
        step_number = step_info.get('step_number', 0)
        total_steps = step_info.get('total_steps', 0)
        
        if step_number and total_steps:
            if step_number < total_steps:
                content += f"\n\n⏭️ Sẵn sàng chuyển sang bước {step_number + 1}?"
            else:
                content += "\n\n🎉 Bạn đã hoàn thành tất cả các bước!"
        
        response.content = content
        return response

    def _get_domain_context(self, domain: str) -> str:
        """Get domain-specific context"""
        
        domain_contexts = {
            "xuatnhapcanh": "Xuất nhập cảnh, hộ chiếu, visa",
            "cancuoc": "Căn cước công dân, CCCD, định danh",
            "general": "Thủ tục hành chính nói chung"
        }
        
        return domain_contexts.get(domain, domain_contexts["general"])

    def _load_system_prompts(self) -> Dict[str, str]:
        """Load system prompts from configuration"""
        
        default_prompts = {
            "legal_qa": """Bạn là trợ lý AI chuyên về pháp luật Việt Nam, đặc biệt về thủ tục hành chính.
Nhiệm vụ của bạn là trả lời câu hỏi dựa trên văn bản pháp luật được cung cấp.
Hãy trả lời một cách chính xác, dễ hiểu và thân thiện.""",
            
            "flow_guidance": """Bạn là trợ lý hướng dẫn thủ tục hành chính.
Nhiệm vụ của bạn là giúp người dân hiểu rõ từng bước thực hiện thủ tục.
Hãy động viên, hỗ trợ và đưa ra lời giải thích chi tiết, dễ hiểu."""
        }
        
        # Try to load from config file
        prompts_file = Path(self.config.get("prompts_file", "config/prompts.yaml"))
        if prompts_file.exists():
            try:
                import yaml
                with open(prompts_file, 'r', encoding='utf-8') as f:
                    loaded_prompts = yaml.safe_load(f)
                    default_prompts.update(loaded_prompts.get("system_prompts", {}))
            except Exception as e:
                logger.warning(f"Could not load prompts file: {e}")
        
        return default_prompts

    def _update_avg_response_time(self, new_time: float):
        """Update average response time"""
        
        current_avg = self.request_stats["avg_response_time"]
        total_successful = self.request_stats["successful_requests"]
        
        if total_successful == 1:
            self.request_stats["avg_response_time"] = new_time
        else:
            # Moving average
            self.request_stats["avg_response_time"] = (
                (current_avg * (total_successful - 1) + new_time) / total_successful
            )

    async def generate_summary(self, content: str, max_length: int = 100) -> str:
        """Generate summary of content"""
        
        prompt = f"""Tóm tắt nội dung sau trong tối đa {max_length} từ:

{content}

Tóm tắt:"""
        
        config = GenerationConfig(
            max_tokens=max_length + 20,
            temperature=0.3
        )
        
        response = await self.generate_text(prompt, config)
        return response.content.strip()

    async def check_model_health(self) -> Dict[str, Any]:
        """Check health of all configured models"""
        
        health_status = {}
        
        for provider in [self.primary_provider] + self.fallback_providers:
            try:
                # Simple test generation
                test_response = await self._generate_with_provider(
                    "Test", 
                    GenerationConfig(max_tokens=10, temperature=0),
                    provider
                )
                
                health_status[provider.value] = {
                    "status": "healthy",
                    "response_time": test_response.generation_time,
                    "model": test_response.model_used
                }
                
            except Exception as e:
                health_status[provider.value] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        
        return health_status

    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        
        stats = dict(self.request_stats)
        stats["cache_enabled"] = self.enable_cache
        stats["cache_size"] = len(self.prompt_cache) if self.prompt_cache else 0
        stats["primary_provider"] = self.primary_provider.value
        stats["fallback_providers"] = [p.value for p in self.fallback_providers]
        
        return stats

    def clear_cache(self) -> bool:
        """Clear prompt cache"""
        
        if self.prompt_cache is not None:
            self.prompt_cache.clear()
            logger.info("Cleared prompt cache")
            return True
        return False

# Example configuration
def create_default_config() -> Dict[str, Any]:
    """Create default configuration for GemmaService"""
    
    return {
        "primary_provider": "ollama_local",
        "fallback_providers": ["ollama_cloud"],
        "model_name": "gemma:2b",
        "ollama": {
            "local_url": "http://localhost:11434",
            "cloud_url": "https://your-ollama-cloud.com"
        },
        "generation": {
            "max_tokens": 512,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1
        },
        "enable_cache": True,
        "prompts_file": "config/prompts.yaml"
    }

# Test và example usage
async def test_gemma_service():
    """Test GemmaService functionality"""
    
    config = create_default_config()
    service = GemmaService(config)
    
    # Test basic generation
    try:
        response = await service.generate_text("Xin chào, bạn khỏe không?")
        print(f"✅ Basic generation: {response.content[:50]}...")
        print(f"   Tokens: {response.tokens_used}, Time: {response.generation_time:.2f}s")
    except Exception as e:
        print(f"❌ Basic generation failed: {e}")
    
    # Test legal answer
    try:
        legal_response = await service.generate_legal_answer(
            query="Phí làm hộ chiếu bao nhiêu?",
            context="Theo Thông tư 01/2023, phí làm hộ chiếu là 200,000 VNĐ",
            domain="xuatnhapcanh"
        )
        print(f"✅ Legal answer: {legal_response.content[:50]}...")
    except Exception as e:
        print(f"❌ Legal answer failed: {e}")
    
    # Test flow guidance
    try:
        flow_response = await service.generate_flow_guidance(
            step_info={
                "name": "Bước 1: Đăng nhập",
                "description": "Truy cập và đăng nhập vào cổng dịch vụ",
                "step_number": 1,
                "total_steps": 5
            },
            user_context={"total_interactions": 3}
        )
        print(f"✅ Flow guidance: {flow_response.content[:50]}...")
    except Exception as e:
        print(f"❌ Flow guidance failed: {e}")
    
    # Test health check
    try:
        health = await service.check_model_health()
        print(f"✅ Health check: {list(health.keys())}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
    
    # Get stats
    stats = service.get_service_stats()
    print(f"📊 Service stats: {stats['total_requests']} total requests")

if __name__ == "__main__":
    asyncio.run(test_gemma_service())