# app/services/vector_rag/llm/prompt_manager.py
"""
Prompt Manager - Quản lý prompt cho các LLM khác nhau
🎯 VAI TRÒ: Load và customize prompt từ file .txt
📋 MODELS: API/PhoGPT vs Gemma:2b với prompt phù hợp
✅ OUTPUT: Prompt đã được customize với context
"""
import os
import re
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class QuestionType(Enum):
    LEGAL_QA = "legal_qa"
    PROCEDURE_GUIDE = "procedure_guide" 
    CONFLICT_RESOLUTION = "conflict_resolution"
    SYSTEM = "system_prompts"

class ModelType(Enum):
    API_PHO_GPT = "api_pho_gpt"  # Gemini API hoặc PhoGPT
    GEMMA_2B = "gemma_2b"

@dataclass
class PromptContext:
    """Context để customize prompt"""
    query: str
    primary_content: str = ""
    primary_citation: str = ""
    conversation_bridge: str = ""
    user_status: str = ""
    location: str = ""
    procedure_type: str = ""
    conflict_situation: str = ""
    conflict_issue: str = ""
    needs_conclusion: bool = False
    supporting_contents: list = None
    
    def __post_init__(self):
        if self.supporting_contents is None:
            self.supporting_contents = []

class PromptManager:
    """Quản lý prompt templates từ file .txt"""
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            current_dir = os.path.dirname(__file__)
            self.prompts_dir = os.path.join(current_dir, "prompts")
        else:
            self.prompts_dir = prompts_dir
        
        self.prompt_cache = {}
        self.stats = {
            'prompts_loaded': 0,
            'cache_hits': 0,
            'customizations': 0,
            'files_loaded': set()
        }
        
        logger.info(f"🎯 Prompt Manager initialized - dir: {self.prompts_dir}")
    
    def get_prompt(self, question_type: str, model_type: str, context: PromptContext) -> str:
        """
        Lấy prompt phù hợp từ file .txt và customize với context
        
        Args:
            question_type: "legal_qa", "procedure_guide", "conflict_resolution", "system_prompts"
            model_type: "api_pho_gpt", "gemma_2b" 
            context: PromptContext object chứa thông tin để customize
        
        Returns:
            str: Prompt đã được customize
        """
        try:
            # Classify model type
            if model_type in ["gemini_api", "pho_gpt"]:
                model_section = "API_PHO_GPT"
            elif model_type == "gemma_2b":
                model_section = "GEMMA_2B"
            else:
                logger.warning(f"Unknown model type: {model_type}, using API_PHO_GPT")
                model_section = "API_PHO_GPT"
            
            # Load prompt template
            prompt_template = self._load_prompt_template(question_type, model_section)
            
            if not prompt_template:
                logger.error(f"Failed to load prompt: {question_type} / {model_section}")
                return self._get_fallback_prompt(context)
            
            # Customize prompt với context
            customized_prompt = self._customize_prompt(prompt_template, context)
            
            self.stats['customizations'] += 1
            logger.debug(f"✅ Prompt customized: {question_type} / {model_section}")
            
            return customized_prompt
            
        except Exception as e:
            logger.error(f"❌ Prompt generation failed: {e}")
            return self._get_fallback_prompt(context)
    
    def _load_prompt_template(self, question_type: str, model_section: str) -> Optional[str]:
        """Load prompt template từ file .txt"""
        cache_key = f"{question_type}_{model_section}"
        
        # Check cache first
        if cache_key in self.prompt_cache:
            self.stats['cache_hits'] += 1
            return self.prompt_cache[cache_key]
        
        # Load from file
        file_path = os.path.join(self.prompts_dir, f"{question_type}.txt")
        
        if not os.path.exists(file_path):
            logger.error(f"❌ Prompt file not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract section tương ứng
            prompt_template = self._extract_section(content, model_section)
            
            if prompt_template:
                # Cache lại để lần sau dùng
                self.prompt_cache[cache_key] = prompt_template
                self.stats['prompts_loaded'] += 1
                self.stats['files_loaded'].add(question_type)
                logger.debug(f"✅ Loaded prompt: {question_type} / {model_section}")
                
            return prompt_template
            
        except Exception as e:
            logger.error(f"❌ Error loading prompt file {file_path}: {e}")
            return None
    
    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract section từ file content"""
        try:
            # Pattern để tìm section
            pattern = f"=== {section_name} ===(.*?)(?==== |$)"
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                section_content = match.group(1).strip()
                logger.debug(f"✅ Extracted section: {section_name}")
                return section_content
            else:
                logger.warning(f"⚠️ Section not found: {section_name}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error extracting section {section_name}: {e}")
            return None
    
    def _customize_prompt(self, template: str, context: PromptContext) -> str:
        """Customize prompt template với context data"""
        try:
            # Basic substitutions
            customized = template.format(
                query=context.query,
                content=context.primary_content,
                citation=context.primary_citation,
                procedure_type=context.procedure_type,
                conflict_situation=context.conflict_situation,
                conflict_issue=context.conflict_issue
            )
            
            # Advanced customizations
            if context.conversation_bridge:
                customized = customized.replace(
                    "Chào bạn,", 
                    f"Chào bạn, {context.conversation_bridge},"
                )
            
            # Clean up any remaining placeholders
            customized = re.sub(r'\{[^}]+\}', '[Thông tin chưa có]', customized)
            
            return customized.strip()
            
        except KeyError as e:
            logger.warning(f"⚠️ Missing template variable: {e}")
            # Try partial formatting
            return self._partial_format(template, context)
        except Exception as e:
            logger.error(f"❌ Error customizing prompt: {e}")
            return template
    
    def _partial_format(self, template: str, context: PromptContext) -> str:
        """Partial formatting khi thiếu một số variables"""
        replacements = {
            '{query}': context.query,
            '{content}': context.primary_content,
            '{citation}': context.primary_citation,
            '{procedure_type}': context.procedure_type,
            '{conflict_situation}': context.conflict_situation,
            '{conflict_issue}': context.conflict_issue
        }
        
        result = template
        for placeholder, value in replacements.items():
            if placeholder in result:
                result = result.replace(placeholder, value or '[Chưa có thông tin]')
        
        return result
    
    def _get_fallback_prompt(self, context: PromptContext) -> str:
        """Fallback prompt khi không load được template"""
        return f"""Bạn là cán bộ hướng dẫn pháp luật tại cơ quan xuất nhập cảnh.

Câu hỏi: {context.query}
Căn cứ: {context.primary_citation}
Nội dung: {context.primary_content}

Hãy trả lời một cách chuyên nghiệp và chính xác.

Kết thúc bằng: "Để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"
"""
    
    def classify_question_type(self, query: str, answer_type: str = None) -> str:
        """
        Phân loại câu hỏi để chọn prompt phù hợp
        
        Args:
            query: Câu hỏi của user
            answer_type: Type từ rag_engine (nếu có)
        
        Returns:
            str: question_type để load prompt
        """
        query_lower = query.lower()
        
        # Sử dụng answer_type từ rag_engine nếu có
        if answer_type:
            if answer_type == "procedure":
                return "procedure_guide"
            elif answer_type == "eligibility":
                return "legal_qa"
            elif answer_type == "conflict":
                return "conflict_resolution"
        
        # Fallback classification dựa trên keywords
        procedure_keywords = ['thủ tục', 'làm', 'hồ sơ', 'cách', 'quy trình', 'bước']
        conflict_keywords = ['xung đột', 'khiếu nại', 'khiếu kiện', 'tranh chấp', 'vướng mắc']
        
        if any(keyword in query_lower for keyword in procedure_keywords):
            return "procedure_guide"
        elif any(keyword in query_lower for keyword in conflict_keywords):
            return "conflict_resolution"
        else:
            return "legal_qa"  # Default
    
    def format_response_output(self, response: str) -> str:
        """
        Format response để đảm bảo bold formatting và line breaks đúng
        
        Args:
            response: Raw response từ LLM
            
        Returns:
            str: Formatted response
        """
        try:
            # Ensure proper markdown bold formatting
            formatted = response
            
            # Fix bold formatting nếu cần
            formatted = re.sub(r'\*\*([^*]+)\*\*', r'**\1**', formatted)
            
            # Đảm bảo line breaks đúng format:
            # **Title:**\ncontent (1 break after title)
            formatted = re.sub(r'\*\*([^*]+):\*\*\s*\n\s*', r'**\1:**\n', formatted)
            
            # Ensure proper spacing between sections (2 breaks)
            formatted = re.sub(r'\n\n\n+', '\n\n\n', formatted)  # Max 2 breaks
            
            return formatted.strip()
            
        except Exception as e:
            logger.error(f"❌ Error formatting response: {e}")
            return response
    
    def get_stats(self) -> Dict[str, Any]:
        """Get prompt manager statistics"""
        return {
            'version': 'Prompt Manager v1.0',
            'prompts_dir': self.prompts_dir,
            'performance': {
                'prompts_loaded': self.stats['prompts_loaded'],
                'cache_hits': self.stats['cache_hits'],
                'customizations': self.stats['customizations'],
                'cache_size': len(self.prompt_cache)
            },
            'files_loaded': list(self.stats['files_loaded']),
            'available_question_types': [
                'legal_qa',
                'procedure_guide', 
                'conflict_resolution',
                'system_prompts'
            ],
            'supported_models': [
                'gemini_api',
                'pho_gpt',
                'gemma_2b'
            ]
        }
    
    def clear_cache(self):
        """Clear prompt cache"""
        self.prompt_cache.clear()
        self.stats['cache_hits'] = 0
        logger.info("🧹 Prompt cache cleared")
    
    def preload_prompts(self):
        """Preload tất cả prompts vào cache"""
        question_types = ['legal_qa', 'procedure_guide', 'conflict_resolution', 'system_prompts']
        model_sections = ['API_PHO_GPT', 'GEMMA_2B']
        
        for qt in question_types:
            for ms in model_sections:
                self._load_prompt_template(qt, ms)
        
        logger.info(f"🚀 Preloaded {len(self.prompt_cache)} prompts into cache")