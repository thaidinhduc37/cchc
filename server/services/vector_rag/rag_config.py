# config.py - Cấu hình tối ưu cho RAG system
import os
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class DVCRAGConfig:
    """Cấu hình tối ưu cho DVC RAG system"""
    
    # Core paths - relative to project root
    base_path: str = "server"
    data_path: str = "dataset"
    vector_store_path: str = "vector_store"
    
    # Embedding settings - Vietnamese optimized
    embedding_model: str = "keepitreal/vietnamese-sbert"
    device: str = "cpu"
    max_seq_length: int = 512
    
    # Chunking strategy optimized for legal documents
    chunk_size: int = 800  # Giảm từ 1000
    chunk_overlap: int = 100  # Giảm từ 200
    separators: list = None
    
    # Retrieval settings
    top_k: int = 3
    score_threshold: float = 0.5  # Tăng từ 0.4 để lọc kết quả tốt hơn
    max_context_length: int = 2000  # Giảm từ 4000
    
    # Ollama LLM settings
    ollama_url: str = "http://localhost:11434"
    model_name: str = "gemma:2b"
    temperature: float = 0.05  # Giảm để câu trả lời ổn định hơn
    max_tokens: int = 800  # Giảm từ 1500
    timeout: int = 60
    
    def __post_init__(self):
        """Khởi tạo các thư mục cần thiết"""
        # Set default separators for legal documents
        if self.separators is None:
            self.separators = [
                "\n\nĐiều ", "\n\nKhoản ", "\n\nĐiểm ",
                "\n\nChương ", "\n\nMục ", "\n\n", "\n", ". ", " "
            ]
        
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.vector_store_path, exist_ok=True)
    
    def get_domain_paths(self, domain: str) -> Dict[str, str]:
        """Lấy đường dẫn cho domain cụ thể"""
        return {
            'data_path': os.path.join(self.data_path, domain),
            'vector_store_path': os.path.join(self.vector_store_path, f"{domain}_vectorstore")
        }

# Global config instance
CONFIG = DVCRAGConfig()

# Legal-specific prompt template - Tối ưu cho văn bản pháp luật Việt Nam
LEGAL_PROMPT_TEMPLATE = """Bạn là chuyên gia tư vấn pháp luật DVC Việt Nam. Trả lời ngắn gọn, chính xác dựa trên thông tin sau:

THÔNG TIN PHÁP LÝ:
{context}

CÂU HỎI: {question}

YÊU CẦU:
- Trả lời bằng tiếng Việt, tối đa 200 từ
- Trích dẫn điều/khoản/điểm cụ thể
- Nếu không có thông tin: "Tôi sẽ cập nhật thông tin và trả lời cho bạn sớm nhất"

TRẢ LỜI:"""

# System prompts for different domains
DOMAIN_PROMPTS = {
    'xuatnhapcanh': """Bạn là chuyên gia về thủ tục xuất nhập cảnh Việt Nam. Tập trung vào:
- Thủ tục visa, hộ chiếu
- Quy định xuất nhập cảnh
- Thủ tục cho người nước ngoài
- Các trường hợp đặc biệt""",
    
    'doanhnghiep': """Bạn là chuyên gia pháp luật doanh nghiệp. Tập trung vào:
- Thành lập, giải thể doanh nghiệp
- Quyền và nghĩa vụ doanh nghiệp
- Thủ tục đăng ký kinh doanh
- Quản trị doanh nghiệp""",
    
    'default': LEGAL_PROMPT_TEMPLATE
}