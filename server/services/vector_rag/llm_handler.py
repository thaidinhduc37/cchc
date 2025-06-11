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
        """SỬA: Generate with Gemini với provider tag"""
        try:
            prompt = prompt_template.format(
                context=context,
                question=query
            )
            
            response = await asyncio.to_thread(
                self.gemini_model.generate_content,
                prompt
            )
            
            if response and response.text:
                generated_text = response.text.strip()
                
                # SỬA: Validate với provider='gemini'
                if self._validate_response(generated_text, provider='gemini'):
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
        """SỬA: Generate với enhanced legal citation prompts"""
        try:
            if '=== VĂN BẢN PHÁP LUẬT ===' in context:
                limited_context = context[:4000] + "..." if len(context) > 4000 else context
                
                # SỬA: Detect query type và chọn enhanced prompt
                query_type = self._detect_query_type(query)
                
                if query_type == 'comparison':
                    # Enhanced comparison với strict citation requirements
                    simple_prompt = f"""Văn bản pháp luật Việt Nam:

{limited_context}

Câu hỏi: {query}

PHÂN TÍCH PHÁP LÝ CHI TIẾT:

FORMAT CHÍNH XÁC:
**Căn cứ pháp lý:**
Căn cứ Điều [số].1 Luật Xuất cảnh, nhập cảnh của người Việt Nam số 47/2019/QH14:
[Trích xuất chính xác nội dung điều luật]

Căn cứ Điều [số] Bộ luật Tố tụng hình sự số 101/2015/QH13:
[Trích xuất quy định về tạm hoãn xuất cảnh]

**Phân tích:**
[Giải thích cách áp dụng các điều luật trên vào tình huống]

**KẾT LUẬN CHÍNH XÁC:**
[Trả lời rõ ràng: CÓ/KHÔNG được xuất cảnh]

**Lưu ý:**
[Điều kiện ngoại lệ hoặc thủ tục đặc biệt nếu có]

Trả lời đầy đủ và chính xác:"""

                elif query_type == 'procedure':
                    # Enhanced procedure với structured analysis
                    simple_prompt = f"""Văn bản pháp luật Việt Nam:

{limited_context}

Câu hỏi: {query}

PHÂN TÍCH THỦ TỤC:
1. Tìm căn cứ pháp lý từ nhiều cấp văn bản
2. Xác định quy trình thực hiện cụ thể
3. Liệt kê yêu cầu, điều kiện, thời hạn

FORMAT BẮT BUỘC:
**Căn cứ pháp lý:**
- Điều [số] Luật [tên đầy đủ] số [X/năm]: [quy định chung]
- Điều [số] Nghị định số [X/năm]: [quy định chi tiết] 
- Thông tư số [X/năm]: [hướng dẫn thực hiện]

**Thủ tục cụ thể:**
- Hồ sơ: [danh sách chi tiết]
- Thời hạn: [thời gian cụ thể]
- Nơi nộp: [cơ quan thẩm quyền]
- Lệ phí: [mức phí nếu có]

**Lưu ý:** [điều kiện đặc biệt nếu có]

Trả lời chi tiết:"""

                elif query_type == 'factual':
                    # Enhanced factual với precise data extraction
                    simple_prompt = f"""Văn bản pháp luật Việt Nam:

{limited_context}

Câu hỏi: {query}

TRÍCH XUẤT THÔNG TIN CỤ THỂ:
1. Tìm số liệu chính xác từ từng cấp văn bản
2. So sánh và đối chiếu các quy định
3. Đưa ra thông tin cuối cùng và chính xác nhất

FORMAT BẮT BUỘC:
**Theo Luật gốc:**
- Điều [số] Luật [tên đầy đủ]: [quy định về phí/thời gian/số lượng]

**Theo văn bản hướng dẫn:**
- Nghị định số [X/năm]: [mức cụ thể, chi tiết]
- Thông tư số [X/năm]: [hướng dẫn thực hiện]

**Thông tin chính xác hiện tại:**
[Số liệu cuối cùng được áp dụng với đơn vị rõ ràng]

**Ghi chú:** [Thời điểm có hiệu lực, điều kiện áp dụng]

Trả lời cụ thể:"""

                elif query_type == 'definition':
                    # Enhanced definition với comprehensive legal interpretation
                    simple_prompt = f"""Văn bản pháp luật Việt Nam:

{limited_context}

Câu hỏi: {query}

PHÂN TÍCH ĐỊNH NGHĨA PHÁP LÝ:
1. Tìm định nghĩa chính thức trong từng văn bản
2. Phân tích mối quan hệ giữa các định nghĩa
3. Đưa ra hiểu biết toàn diện về khái niệm

FORMAT BẮT BUỘC:
**Định nghĩa chính thức:**
- Theo Điều [số] Luật [tên đầy đủ] số [X/năm]: 
  "[Trích dẫn nguyên văn định nghĩa]"

**Quy định bổ sung:**
- Theo Nghị định số [X/năm]: "[Quy định chi tiết/mở rộng]"
- Theo Thông tư số [X/năm]: "[Hướng dẫn hiểu và áp dụng]"

**Hiểu biết tổng hợp:**
[Giải thích đầy đủ khái niệm với ví dụ cụ thể nếu có]

**Phân biệt:** [So với các khái niệm tương tự nếu có]

Trả lời chuyên sâu:"""

                else:
                    # Enhanced general với professional legal analysis
                    simple_prompt = f"""Văn bản pháp luật Việt Nam:

{limited_context}

Câu hỏi: {query}

NGHIÊN CỨU PHÁP LÝ TOÀN DIỆN:
1. Phân tích từ góc độ nhiều cấp văn bản pháp luật
2. Xem xét mối quan hệ giữa các quy định
3. Đưa ra tư vấn chuyên nghiệp và thực tiễn

FORMAT CHUYÊN NGHIỆP:
**Căn cứ pháp lý chính:**
- Điều [số] Luật [tên đầy đủ] số [X/năm]: [quy định cơ bản]

**Văn bản hướng dẫn thi hành:**
- Nghị định số [X/năm]: [quy định chi tiết]
- Thông tư số [X/năm]: [hướng dẫn kỹ thuật]

**Văn bản liên quan khác:**
- [Quyết định/Chỉ thị/Công văn nếu có]: [quy định bổ sung]

**Phân tích và tư vấn:**
[Giải thích cách áp dụng quy định vào tình huống cụ thể]

**Khuyến nghị thực tiễn:**
[Hướng dẫn cụ thể cho người hỏi]

Trả lời chuyên nghiệp và đầy đủ:"""

            else:
                # Enhanced administrative procedure với professional structure
                simple_prompt = f"""Thông tin thủ tục hành chính:

{context[:2500]}

Câu hỏi: {query}

HƯỚNG DẪN THỦ TỤC CHUYÊN NGHIỆP:
1. Xác định căn cứ pháp lý đầy đủ
2. Hướng dẫn quy trình từng bước chi tiết
3. Lưu ý các điều kiện và yêu cầu đặc biệt

FORMAT HƯỚNG DẪN:
**Căn cứ pháp lý:**
- Thông tư số [X/năm] của [Bộ/Cơ quan]: [quy định chính]
- Quyết định số [X/năm]: [quy định bổ sung]
- Công văn hướng dẫn số [X]: [hướng dẫn chi tiết]

**Quy trình thực hiện:**
Bước 1: [Hành động cụ thể]
Bước 2: [Hành động tiếp theo]
Bước 3: [Hoàn tất thủ tục]

**Hồ sơ yêu cầu:**
- [Danh sách giấy tờ cụ thể với số lượng]

**Thời gian và địa điểm:**
- Thời hạn: [X ngày làm việc]
- Nơi nộp: [Địa chỉ cụ thể]
- Lệ phí: [Mức phí cụ thể]

**Lưu ý quan trọng:**
[Các điều kiện đặc biệt cần chú ý]

Hướng dẫn chi tiết và thực tế:"""
            
            payload = {
                "model": self.config.ollama_model,
                "prompt": simple_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.01,          # Giảm thêm để tránh hallucination
                    "num_predict": 650,           # Tăng để tránh bị cắt
                    "top_p": 0.4,                 # Giảm mạnh để focus
                    "num_ctx": 4096,             
                    "repeat_penalty": 1.25,       # Tăng để tránh lặp
                    "stop": [
                        "Câu hỏi:", "PHÂN TÍCH:", "FORMAT:", "NHIỆM VỤ:",
                        "Văn bản pháp luật:", "Thông tin thủ tục:", 
                        "YÊU CẦU:", "HƯỚNG DẪN:", "TRÍCH XUẤT:",
                        "NGHIÊN CỨU PHÁP LÝ:", "Trả lời chuyên nghiệp:",
                        "Trả lời chi tiết:", "Trả lời cụ thể:", "Trả lời chuyên sâu:",
                        "Hướng dẫn chi tiết và thực tế:"
                    ]
                }
            }
            
            async with aiohttp.ClientSession() as session:
                timeout = aiohttp.ClientTimeout(total=35)  # Tăng timeout
                async with session.post(
                    f"{self.config.ollama_url}/api/generate",
                    json=payload,
                    timeout=timeout
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        generated_text = result.get("response", "").strip()
                        
                        # SỬA: Adaptive cleaning based on query type
                        generated_text = self._clean_adaptive_response(generated_text, query_type)
                        
                        logger.info(f"🤖 Gemma [{query_type}]: '{generated_text[:100]}...'")
                        
                        if generated_text and self._validate_adaptive_response(generated_text, query_type):
                            return {
                                'success': True,
                                'response': generated_text,
                                'provider': 'gemma',
                                'prompt_type': f'adaptive_{query_type}',
                                'model': self.config.ollama_model,
                                'cost_estimate': 0.0
                            }
                        else:
                            logger.warning(f"❌ Gemma validation failed for {query_type}")
                            return {
                                'success': False,
                                'error': 'poor_quality_response',
                                'query_type': query_type
                            }
                    else:
                        return {
                            'success': False,
                            'error': f'ollama_api_error_{response.status}'
                        }
                        
        except Exception as e:
            return {
                'success': False,
                'error': f"gemma_error: {e}"
            }

    def _clean_adaptive_response(self, response: str, query_type: str) -> str:
        """THÊM: Enhanced cleaning với legal citation preservation"""
        if not response:
            return ""
        
        # Remove professional legal instruction artifacts
        artifacts_to_remove = [
            "Trả lời:", "PHÂN TÍCH PHÁP LÝ:", "FORMAT BẮT BUỘC:", "PHÂN TÍCH THỦ TỤC:",
            "TRÍCH XUẤT THÔNG TIN CỤ THỂ:", "PHÂN TÍCH ĐỊNH NGHĨA PHÁP LÝ:", 
            "NGHIÊN CỨU PHÁP LÝ TOÀN DIỆN:", "HƯỚNG DẪN THỦ TỤC CHUYÊN NGHIỆP:",
            "FORMAT CHUYÊN NGHIỆP:", "FORMAT HƯỚNG DẪN:", "Trả lời chuyên nghiệp:",
            "Trả lời chi tiết:", "Trả lời cụ thể:", "Trả lời chuyên sâu:",
            "Hướng dẫn chi tiết và thực tế:", "Trả lời chuyên nghiệp và đầy đủ:",
            "YÊU CẦU:", "NHIỆM VỤ:", "1. Tìm", "2. Trích dẫn", "3. Phân tích",
            "4. Đưa ra", "1. Tìm căn cứ", "2. Xác định", "3. Liệt kê"
        ]
        
        for artifact in artifacts_to_remove:
            response = response.replace(artifact, "").strip()
        
        # Clean response và ensure completeness
        lines = response.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 5:
                # Skip instruction commentary
                skip_phrases = [
                    'phân tích pháp lý:', 'format chính xác:', 'format bắt buộc:',
                    'trả lời đầy đủ:', 'trả lời chính xác:', 'trả lời chuyên nghiệp:',
                    'nhiệm vụ:', 'yêu cầu:', 'hướng dẫn:', 'chi tiết:'
                ]
                
                # PROFESSIONAL legal content indicators
                legal_starters = [
                    'căn cứ', 'theo điều', 'điều ', 'luật số', 'nghị định',
                    'thông tư', 'quyết định', 'khoản ', 'theo quy định',
                    'kết luận:', 'phân tích:', 'lưu ý:', 'ghi chú:',
                    'người bị', 'trường hợp', 'được', 'không được', 'bị cấm',
                    'căn cứ pháp lý:', 'kết luận chính xác:', 'phân tích và tư vấn:',
                    'thủ tục cụ thể:', 'hồ sơ yêu cầu:', 'thời gian:', 'địa điểm:',
                    'bước 1:', 'bước 2:', 'bước 3:', 'thời hạn:', 'lệ phí:'
                ]
                
                is_legal_content = any(starter in line.lower() for starter in legal_starters)
                has_skip_phrase = any(skip_phrase in line.lower() for skip_phrase in skip_phrases)
                
                if is_legal_content or not has_skip_phrase:
                    # Clean formatting nhưng preserve structure
                    line = line.replace('- ', '').replace('• ', '').strip()
                    if line and not line.lower().startswith(('1.', '2.', '3.', '4.')):
                        cleaned_lines.append(line)
        
        result = '\n'.join(cleaned_lines).strip()
        
        # Ensure proper legal citation format
        if result and not any(starter in result.lower()[:80] for starter in ['căn cứ', 'theo điều']):
            import re
            legal_patterns = [
                r'điều \d+[.]?\d*\s*(?:luật|nghị định|thông tư|bộ luật)[^.]*',
                r'luật [^,]* số \d+/\d+[^.]*',
                r'nghị định số \d+/\d+[^.]*'
            ]
            
            for pattern in legal_patterns:
                matches = re.findall(pattern, result.lower())
                if matches:
                    for line in cleaned_lines:
                        if any(word in line.lower() for word in matches[0].split()[:3]):
                            if not line.lower().startswith(('căn cứ', 'theo')):
                                result = f"Căn cứ {line.strip()}\n{result}"
                                break
                    break
        
        # Ensure conclusion exists
        if result and 'kết luận' not in result.lower():
            if 'không được' in result.lower() or 'bị tạm hoãn' in result.lower():
                result += f"\n\nKết luận: Không được xuất cảnh khi bị khởi tố."
            elif 'được phép' in result.lower() or 'có thể' in result.lower():
                result += f"\n\nKết luận: Có thể được xuất cảnh trong một số trường hợp."
        
        return result

    def _validate_adaptive_response(self, response: str, query_type: str) -> bool:
        """THÊM: Enhanced validation với comprehensive legal requirements"""
        if len(response.strip()) < 20:
            return False
        
        response_lower = response.lower()
        
        # Enhanced comprehensive legal citation pattern checking
        import re
        legal_citation_patterns = [
            r'căn cứ điều \d+',
            r'theo điều \d+',
            r'điều \d+[a-z]?\s+luật',
            r'điều \d+[a-z]?\s+nghị định', 
            r'điều \d+[a-z]?\s+thông tư',
            r'theo quy định tại điều',
            r'luật số \d+/\d+',
            r'nghị định số \d+/\d+',
            r'thông tư số \d+/\d+',
            r'khoản \d+[a-z]? điều \d+',
            r'quyết định số \d+/\d+',
            r'chỉ thị số \d+/\d+',
            r'công văn số \d+/\d+',
            r'căn cứ pháp lý',
            r'văn bản liên quan',
            r'theo luật [^,]*',
            r'theo nghị định [^,]*',
            r'theo thông tư [^,]*'
        ]
        
        has_proper_citation = any(re.search(pattern, response_lower) for pattern in legal_citation_patterns)
        
        # Enhanced basic legal indicators for comprehensive coverage
        basic_legal_indicators = [
            'điều', 'luật', 'nghị định', 'thông tư', 'quy định', 
            'căn cứ', 'theo', 'khoản', 'được', 'không được',
            'quyết định', 'chỉ thị', 'công văn', 'hướng dẫn'
        ]
        has_basic_legal = sum(1 for word in basic_legal_indicators if word in response_lower) >= 3  # Tăng yêu cầu
        
        # Must have either proper citation OR strong legal indicators
        if not has_proper_citation and not has_basic_legal:
            return False
        
        # Enhanced type-specific validation
        if query_type == 'comparison':
            # Cần có multiple legal references + comprehensive conclusion
            legal_count = len(re.findall(r'(?:luật|nghị định|thông tư)', response_lower))
            has_legal = any(word in response_lower for word in ['điều', 'luật', 'quy định', 'căn cứ'])
            conclusion_words = [
                'được', 'không được', 'có thể', 'không thể', 'kết luận', 
                'do đó', 'vậy', 'bị cấm', 'được phép', 'tổng hợp'
            ]
            has_conclusion = any(word in response_lower for word in conclusion_words)
            return has_legal and has_conclusion and legal_count >= 1  # Ít nhất 1 loại văn bản
        
        elif query_type == 'procedure':
            # Cần có multiple legal sources + comprehensive procedure
            legal_source_count = len(re.findall(r'(?:luật|nghị định|thông tư|quyết định)', response_lower))
            has_legal_basis = has_proper_citation or any(word in response_lower for word in ['theo', 'quy định', 'căn cứ'])
            procedure_words = [
                'hồ sơ', 'thủ tục', 'gồm', 'yêu cầu', 'nộp tại', 
                'thời hạn', 'bước', 'cần', 'phải', 'cách thức'
            ]
            has_procedure = any(word in response_lower for word in procedure_words)
            return has_legal_basis and has_procedure and legal_source_count >= 1
        
        elif query_type == 'factual':
            # Cần có multiple sources + comprehensive data
            legal_source_count = len(re.findall(r'(?:luật|nghị định|thông tư)', response_lower))
            has_legal_basis = has_proper_citation or any(word in response_lower for word in ['theo', 'điều', 'quy định'])
            
            # Check for comprehensive specific data
            has_numbers = any(re.search(pattern, response_lower) for pattern in [
                r'\d+\s*đồng', r'\d+\s*ngày', r'\d+\s*tháng', 
                r'\d+\s*%', r'\d+\s*lần', r'\d+\s*năm', r'\d+\s*triệu'
            ])
            has_fee_time_info = any(word in response_lower for word in ['phí', 'lệ phí', 'thời gian', 'bao lâu', 'mức'])
            has_comprehensive_info = 'tổng hợp' in response_lower or legal_source_count >= 2
            
            return has_legal_basis and (has_numbers or has_fee_time_info) and (has_comprehensive_info or legal_source_count >= 1)
        
        elif query_type == 'definition':
            # Cần có comprehensive definition từ multiple sources
            legal_source_count = len(re.findall(r'(?:luật|nghị định|thông tư)', response_lower))
            has_legal_basis = has_proper_citation or any(word in response_lower for word in ['theo', 'điều'])
            definition_indicators = ['"', 'là', 'được hiểu', 'có nghĩa', 'định nghĩa', 'được quy định', 'tổng hợp']
            has_definition = any(indicator in response_lower for indicator in definition_indicators)
            return has_legal_basis and has_definition and legal_source_count >= 1
        
        else:
            # General validation - comprehensive legal research from multiple sources
            comprehensive_legal_words = [
                'điều', 'quy định', 'theo', 'được', 'phải', 'luật',
                'nghị định', 'thông tư', 'căn cứ', 'khoản', 'trường hợp',
                'quyết định', 'chỉ thị', 'công văn'
            ]
            legal_word_count = sum(1 for word in comprehensive_legal_words if word in response_lower)
            
            # Check for multiple legal document types
            legal_types = ['luật', 'nghị định', 'thông tư', 'quyết định', 'chỉ thị']
            legal_type_count = sum(1 for legal_type in legal_types if legal_type in response_lower)
            
            # Enhanced context words for immigration law
            context_words = [
                'xuất cảnh', 'nhập cảnh', 'hộ chiếu', 'visa', 'thị thực',
                'người nước ngoài', 'công dân', 'cơ quan', 'thẩm quyền',
                'tạm hoãn', 'khởi tố', 'bị can', 'bị cáo'
            ]
            context_count = sum(1 for word in context_words if word in response_lower)
            
            # Check for comprehensive indicators
            comprehensive_indicators = ['tổng hợp', 'kết luận', 'căn cứ pháp lý', 'văn bản liên quan']
            has_comprehensive = any(indicator in response_lower for indicator in comprehensive_indicators)
            
            return (legal_word_count >= 3 and 
                   legal_type_count >= 1 and 
                   (context_count >= 1 or has_proper_citation or has_comprehensive))

    def _detect_query_type(self, query: str) -> str:
        """THÊM: Enhanced query type detection cho comprehensive research"""
        query_lower = query.lower()
        
        # Legal definition queries - EXPANDED
        if any(pattern in query_lower for pattern in [
            'là gì', 'định nghĩa', 'có nghĩa', 'được hiểu', 'khái niệm'
        ]):
            return 'definition'
        
        # Legal comparison queries - EXPANDED
        elif any(pattern in query_lower for pattern in [
            'có được', 'được không', 'có thể không', 'khác nhau', 'so với',
            'phân biệt', 'giống nhau', 'khác biệt', 'so sánh'
        ]):
            return 'comparison'
        
        # Procedural queries - EXPANDED  
        elif any(pattern in query_lower for pattern in [
            'hồ sơ', 'thủ tục', 'cách', 'làm thế nào', 'gồm', 'cần',
            'bước', 'quy trình', 'trình tự', 'nộp đơn', 'đăng ký'
        ]):
            return 'procedure'
        
        # Fee/time/factual queries - EXPANDED
        elif any(pattern in query_lower for pattern in [
            'phí', 'lệ phí', 'bao nhiêu', 'thời gian', 'bao lâu',
            'mức', 'chi phí', 'thời hạn', 'khi nào', 'ngày'
        ]):
            return 'factual'
        
        else:
            return 'general'

    
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
    
    def _validate_response(self, response: str, provider: str = 'unknown') -> bool:
        """SỬA: Enhanced response validation với relaxed cho Gemma:2b"""
        
        # SỬA: Giảm minimum length cho Gemma:2b
        min_length = 15 if provider == 'gemma' else self.min_response_length
        if len(response.strip()) < min_length:
            logger.debug(f"Response too short: {len(response)} < {min_length}")
            return False
        
        # SỬA: Relaxed negative indicators cho Gemma:2b
        negative_indicators = [
            'không có thông tin', 'không tìm thấy', 'không thể trả lời',
            'tôi không biết', 'xin lỗi'
        ]
        
        negative_count = sum(1 for indicator in negative_indicators if indicator in response.lower())
        max_negative = 3 if provider == 'gemma' else 2  # More tolerant for Gemma
        
        if negative_count >= max_negative:
            logger.debug(f"Too many negative indicators: {negative_count}")
            return False
        
        # SỬA: Relaxed content validation cho Gemma:2b
        if provider == 'gemma':
            # Gemma:2b - chỉ cần có ít nhất 1 useful indicator
            useful_indicators = [
                'điều', 'khoản', 'thủ tục', 'hồ sơ', 'theo quy định',
                'lệ phí', 'thời gian', 'cơ quan', 'điều kiện', 'được', 'không được',
                'cấm', 'xuất cảnh', 'hộ chiếu'  # Thêm keywords cho query này
            ]
            useful_count = sum(1 for indicator in useful_indicators if indicator in response.lower())
            return useful_count >= 1  # Chỉ cần 1 useful word
        
        else:
            # API providers - strict validation
            has_proper_citation = any(pattern in response.lower() for pattern in [
                'điều', 'luật số', 'nghị định', 'thông tư', 'theo quy định'
            ])
            
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