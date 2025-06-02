"""
⚙️ Configuration Module - System settings và environment config
"""

import os
from typing import Dict, Any, List
from pathlib import Path
import yaml
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Main application settings"""
    
    # App settings
    app_name: str = "DVC RAG System"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # Data paths
    data_path: str = Field(default="data", env="DATA_PATH")
    cache_path: str = Field(default="data/shared/cache", env="CACHE_PATH")
    
    # Database settings (for future use)
    database_url: str = Field(default="sqlite:///dvc_system.db", env="DATABASE_URL")
    
    # LLM settings
    primary_llm_provider: str = Field(default="ollama_local", env="PRIMARY_LLM_PROVIDER")
    ollama_url: str = Field(default="http://localhost:11434", env="OLLAMA_URL")
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    
    # Search settings
    excel_exact_threshold: float = 0.95
    excel_fuzzy_threshold: float = 0.75
    vector_similarity_threshold: float = 0.7
    
    # Context settings
    max_conversation_history: int = 50
    session_timeout_seconds: int = 3600
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 1800
    max_concurrent_requests: int = 100
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()

def get_settings() -> Settings:
    """Get application settings"""
    return settings

def load_prompts() -> Dict[str, str]:
    """Load system prompts from YAML file"""
    
    prompts_file = Path("config/prompts.yaml")
    default_prompts = {
        "legal_qa": """Bạn là trợ lý AI chuyên về pháp luật Việt Nam. 
Trả lời chính xác dựa trên ngữ cảnh được cung cấp. 
Sử dụng ngôn ngữ dễ hiểu, thân thiện.""",
        
        "flow_guidance": """Bạn là trợ lý hướng dẫn thủ tục hành chính.
Động viên và hỗ trợ người dân hiểu rõ từng bước thực hiện.""",
        
        "intent_classification": """Phân loại intent từ câu hỏi người dùng:
- FLOW: yêu cầu hướng dẫn, thủ tục
- RAG: hỏi thông tin, quy định, phí"""
    }
    
    if prompts_file.exists():
        try:
            with open(prompts_file, 'r', encoding='utf-8') as f:
                loaded_prompts = yaml.safe_load(f)
                default_prompts.update(loaded_prompts.get("prompts", {}))
        except Exception as e:
            print(f"Warning: Could not load prompts file: {e}")
    
    return default_prompts

def get_domain_config() -> Dict[str, Any]:
    """Get domain-specific configuration"""
    
    return {
        "xuatnhapcanh": {
            "name": "Xuất nhập cảnh",
            "description": "Hộ chiếu, visa, xuất nhập cảnh",
            "keywords": ["hộ chiếu", "passport", "visa", "xuất cảnh", "nhập cảnh"],
            "enabled": True
        },
        "cancuoc": {
            "name": "Căn cước công dân", 
            "description": "CCCD, chứng minh thư, định danh",
            "keywords": ["căn cước", "cccd", "chứng minh", "cmnd"],
            "enabled": True
        }
    }

def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration"""
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
            }
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "standard"
            },
            "file": {
                "level": "DEBUG",
                "class": "logging.FileHandler",
                "filename": "logs/dvc_system.log",
                "formatter": "detailed"
            }
        },
        "loggers": {
            "": {
                "handlers": ["console", "file"],
                "level": "INFO"
            }
        }
    }