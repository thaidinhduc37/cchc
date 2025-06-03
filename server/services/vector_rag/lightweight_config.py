# server/services/vector_rag/lightweight_config.py
"""
Cấu hình siêu nhẹ cho hệ thống RAG xuất nhập cảnh
Thay thế config.py cũ với version tối ưu hiệu năng
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

# Fix import cho load_dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file
except ImportError:
    print("⚠️ python-dotenv not installed. Using os.environ only.")
    def load_dotenv():
        pass

@dataclass
class LightweightEmbeddingConfig:
    """Cấu hình embedding nhẹ"""
    # Thay thế keepitreal/vietnamese-sbert bằng model nhẹ hơn
    model_name: str = "all-MiniLM-L6-v2"  # Chỉ 23MB thay vì 500MB+
    device: str = "cpu"
    max_length: int = 512
    batch_size: int = 32
    cache_embeddings: bool = True
    
    def get(self, key, default=None):
        """Dict-like get method"""
        return getattr(self, key, default)

@dataclass 
class LightweightChunkingConfig:
    """Cấu hình chunking tối ưu cho văn bản pháp lý"""
    chunk_size: int = 800  # Giảm từ 1000 để tiết kiệm RAM
    chunk_overlap: int = 100  # Giảm từ 200
    # Separators tối ưu cho văn bản pháp lý VN
    separators: List[str] = None
    
    def get(self, key, default=None):
        """Dict-like get method"""
        return getattr(self, key, default)
    
    def __post_init__(self):
        if self.separators is None:
            self.separators = [
                "\n\nĐiều ",  # Ưu tiên điều luật
                "\n\nKhoản ",  # Ưu tiên khoản
                "\n\n", "\n", 
                ". ", "! ", "? ",
                ", ", " ", ""
            ]

@dataclass
class LightweightVectorConfig:
    """Cấu hình vector store nhẹ"""
    store_type: str = "chromadb"  # chromadb thay vì FAISS
    collection_name: str = "xuatnhapcanh"
    persist_directory: str = "./dataset/xuatnhapcanh/process/vectorstore"  # ← Fixed path
    search_type: str = "similarity"
    k: int = 3
    score_threshold: float = 0.7

@dataclass
class LightweightLLMConfig:
    """Cấu hình LLM với multi-provider"""
    # Primary: Gemini API (nhanh, chính xác)
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-pro"
    
    # Backup: Ollama Gemma:2b (local, miễn phí)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma:2b"
    
    # Generation params
    temperature: float = 0.1
    max_tokens: int = 800
    timeout: int = 30
    
    def __post_init__(self):
        # Load API key from environment
        if self.gemini_api_key is None:
            self.gemini_api_key = os.getenv("GEMINI_API_KEY")

@dataclass
class LightweightSystemConfig:
    """Cấu hình hệ thống tổng thể"""
    # Paths theo cấu trúc thực tế (fixed paths)
    data_path: str = "./dataset"
    domain: str = "xuatnhapcanh"
    documents_path: str = "./dataset/xuatnhapcanh/documents"
    process_path: str = "./dataset/xuatnhapcanh/process"
    vector_store_path: str = "./dataset/xuatnhapcanh/process/vectorstore"
    cache_path: str = "./dataset/xuatnhapcanh/process/cache"
    logs_path: str = "./dataset/xuatnhapcanh/process/logs"
    
    # Cache settings - tối ưu memory
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1 hour
    max_cache_size: int = 1000  # Giới hạn cache entries
    
    # Domain-specific settings
    supported_formats: List[str] = None
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['.pdf', '.txt', '.docx']
        
        # Tạo thư mục nếu chưa có
        for path in [
            self.documents_path, self.process_path, 
            self.vector_store_path, self.cache_path, self.logs_path
        ]:
            os.makedirs(path, exist_ok=True)

# Khởi tạo configs mặc định
EMBEDDING_CONFIG = LightweightEmbeddingConfig()
CHUNKING_CONFIG = LightweightChunkingConfig()
VECTOR_CONFIG = LightweightVectorConfig()
LLM_CONFIG = LightweightLLMConfig()
SYSTEM_CONFIG = LightweightSystemConfig()

# Prompt templates tối ưu cho xuất nhập cảnh
XUATNHAPCANH_PROMPT_TEMPLATE = """
Bạn là chuyên gia tư vấn XUẤT NHẬP CẢNH của Việt Nam. 
Hãy trả lời câu hỏi dựa trên thông tin pháp lý được cung cấp.

NGỮ CẢNH PHÁP LÝ:
{context}

CÂU HỎI: {question}

HƯỚNG DẪN TRẢ LỜI:
✅ Trả lời bằng tiếng Việt, chính xác và chi tiết
✅ Nêu rõ điều luật, nghị định, thông tư liên quan  
✅ Hướng dẫn từng bước thủ tục cụ thể
✅ Chỉ rõ thời gian xử lý, phí lệ phí (nếu có)
✅ Nêu địa điểm tiếp nhận hồ sơ
❌ Nếu không có thông tin, nói rõ "không có trong quy định hiện tại"

TRẢ LỜI:
"""

# Keywords để detect câu hỏi xuất nhập cảnh
XUATNHAPCANH_KEYWORDS = {
    'visa': ['visa', 'thị thực', 'miễn thị'],
    'passport': ['hộ chiếu', 'passport', 'hộ tịch'],
    'residence': ['cư trú', 'tạm trú', 'thường trú', 'tạm vắng'],
    'work': ['lao động', 'làm việc', 'work permit', 'giấy phép lao động'],
    'entry': ['nhập cảnh', 'xuất cảnh', 'entry', 'exit'],
    'procedure': ['thủ tục', 'hồ sơ', 'giấy tờ', 'đăng ký'],
    'border': ['biên giới', 'cửa khẩu', 'border', 'checkpoint'],
    'immigration': ['di cư', 'immigration', 'định cư']
}

# Legal document types mapping
DOCUMENT_TYPES = {
    'luat': 'Luật',
    'nghidinh': 'Nghị định', 
    'thongtu': 'Thông tư',
    'quyetdinh': 'Quyết định',
    'huongdan': 'Hướng dẫn'
}

def get_config_summary() -> Dict:
    """Lấy tóm tắt cấu hình hệ thống"""
    return {
        'embedding_model': EMBEDDING_CONFIG.model_name,
        'chunk_size': CHUNKING_CONFIG.chunk_size,
        'vector_store': VECTOR_CONFIG.store_type,
        'domain': SYSTEM_CONFIG.domain,
        'llm_providers': ['gemini-api', 'ollama-gemma'],
        'cache_enabled': SYSTEM_CONFIG.enable_cache,
        'supported_formats': SYSTEM_CONFIG.supported_formats
    }