# config.py - Cấu hình tập trung cho hệ thống RAG
from dataclasses import dataclass
from typing import Dict, List
import os

@dataclass
class EmbeddingConfig:
    """Cấu hình embedding"""
    model_name: str = "keepitreal/vietnamese-sbert"
    device: str = "cpu"
    normalize_embeddings: bool = True
    
@dataclass 
class ChunkingConfig:
    """Cấu hình chia chunk"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    separators: List[str] = None
    
    def __post_init__(self):
        if self.separators is None:
            self.separators = ["\n\n", "\n", ".", "!", "?", ",", " ", ""]

@dataclass
class RetrievalConfig:
    """Cấu hình retrieval"""
    search_type: str = "similarity"
    k: int = 3
    score_threshold: float = 0.5
    
@dataclass
class LLMConfig:
    """Cấu hình LLM"""
    temperature: float = 0.1
    max_tokens: int = 1000
    top_p: float = 0.9
    n_ctx: int = 2048
    n_threads: int = 4
    
@dataclass
class SystemConfig:
    """Cấu hình hệ thống tổng thể"""
    # Đường dẫn
    data_path: str = "./dataset"  # <-- Trỏ tới gốc dataset (KHÔNG trỏ vào legal_documents nữa!)
    vector_store_path: str = "./vectorstore"
    cache_path: str = "./vectorstore/cache"
    logs_path: str = "./vectorstore/logs"
    
    # Domain mapping
    domains: Dict[str, str] = None
    
    # Cache settings
    enable_cache: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    def __post_init__(self):
        if self.domains is None:
            self.domains = {
                "dich_vu_cong": "Dịch vụ công",
                "hanh_chinh": "Thủ tục hành chính", 
                "luat": "Luật",
                "thong_tu": "Thông tư",
                "nghi_dinh": "Nghị định"
            }
        
        # Tạo thư mục nếu chưa có
        for path in [self.data_path, self.vector_store_path, self.cache_path, self.logs_path]:
            os.makedirs(path, exist_ok=True)

# Khởi tạo cấu hình mặc định
DEFAULT_CONFIG = SystemConfig()
EMBEDDING_CONFIG = EmbeddingConfig()
CHUNKING_CONFIG = ChunkingConfig()
RETRIEVAL_CONFIG = RetrievalConfig()
LLM_CONFIG = LLMConfig()

# Prompt templates
LEGAL_PROMPT_TEMPLATE = """
Bạn là chuyên gia tư vấn về dịch vụ công và các văn bản pháp lý của Việt Nam.
Hãy trả lời câu hỏi dựa trên thông tin được cung cấp một cách chính xác và chi tiết.

Ngữ cảnh từ văn bản pháp lý:
{context}

Câu hỏi: {question}

Hướng dẫn trả lời:
- Trả lời bằng tiếng Việt
- Dựa vào thông tin có trong ngữ cảnh
- Nêu rõ điều khoản, khoản, điểm liên quan
- Nếu liên quan đến thủ tục, nêu rõ các bước thực hiện
- Nếu không có thông tin, hãy nói rõ
- Trả lời ngắn gọn, rõ ràng

Trả lời:
"""

DOMAIN_PROMPTS = {
    "dich_vu_cong": """
Bạn là chuyên gia tư vấn dịch vụ công. Hãy tập trung vào:
- Thủ tục hành chính
- Giấy tờ cần thiết
- Thời gian xử lý
- Phí, lệ phí
- Nơi tiếp nhận hồ sơ

Ngữ cảnh: {context}
Câu hỏi: {question}
Trả lời:
""",
    
    "luat": """
Bạn là chuyên gia pháp lý. Hãy tập trung vào:
- Điều khoản cụ thể của luật
- Quyền và nghĩa vụ
- Chế tài xử phạt
- Hiệu lực thi hành

Ngữ cảnh: {context}
Câu hỏi: {question}
Trả lời:
"""
}