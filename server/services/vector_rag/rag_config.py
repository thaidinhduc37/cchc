# server/services/vector_rag/rag_config.py
"""
RAG Config - CẬP NHẬT: Switch to best embedding model
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, using os.getenv only")
except Exception as e:
    print(f"⚠️ Failed to load .env: {e}")

# CẬP NHẬT: VIETNAMESE EMBEDDING MODELS - Fixed order
VIETNAMESE_EMBEDDING_MODELS = {
    # CẬP NHẬT: Best choice first
    'e5_base': 'intfloat/multilingual-e5-base',        # RECOMMENDED - Most reliable
    
    # Backup options
    'minilm': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',  # Lightweight
    'e5_large': 'intfloat/multilingual-e5-large',      # High accuracy (if have GPU)
    
    # Vietnamese-specific (test only)
    'keepitreal': 'keepitreal/vietnamese-sbert',        # Test only
    
    # CẬP NHẬT: REMOVED - Known issues
    # 'dangvantuan': 'dangvantuan/vietnamese-embedding'  # ❌ REMOVED due to outlier issues
}

@dataclass
class RAGConfig:
    """Cấu hình chính - CẬP NHẬT embedding model"""
    
    # Paths
    domain: str = "xuatnhapcanh"
    data_path: str = "./dataset"
    documents_path: str = "./dataset/xuatnhapcanh/documents"
    vector_store_path: str = "./dataset/xuatnhapcanh/vector_store"
    web_cache_path: str = "./dataset/xuatnhapcanh/web_cache"
    
    # Vector Store - CẬP NHẬT: Switch to best embedding model
    vector_collection_name: str = "xuatnhapcanh_docs"
    embedding_model: str = VIETNAMESE_EMBEDDING_MODELS['e5_base']  # ✅ FIXED: Use e5-base
    
    # CẬP NHẬT: Enhanced chunking for legal documents
    chunk_size: int = 800        
    chunk_overlap: int = 100     
    search_k: int = 8           
    
    # CẬP NHẬT: Adjusted thresholds for e5-base
    min_similarity_threshold: float = 0.15  
    vector_search_threshold: float = 0.1    
    
    # LLM Settings
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma:2b"
    temperature: float = 0.1
    max_tokens: int = 1000
    
    # Web Settings
    web_base_url: str = "https://dichvucong.bocongan.gov.vn"
    web_cache_ttl: int = 7200
    request_timeout: int = 25
    web_priority: bool = True
    force_web_crawl: bool = True
    
    def __post_init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        # Tạo thư mục
        for path in [self.documents_path, self.vector_store_path, self.web_cache_path]:
            os.makedirs(path, exist_ok=True)

    def switch_embedding_model(self, model_key: str):
        """CẬP NHẬT: Switch embedding model"""
        if model_key in VIETNAMESE_EMBEDDING_MODELS:
            old_model = self.embedding_model
            self.embedding_model = VIETNAMESE_EMBEDDING_MODELS[model_key]
            print(f"🔄 Switched embedding model:")
            print(f"   From: {old_model}")
            print(f"   To:   {self.embedding_model}")
            
            # CẬP NHẬT: Adjust thresholds for different models
            if model_key == 'e5_base':
                self.min_similarity_threshold = 0.15
                self.vector_search_threshold = 0.1
            elif model_key == 'minilm':
                self.min_similarity_threshold = 0.2
                self.vector_search_threshold = 0.15
            elif model_key == 'e5_large':
                self.min_similarity_threshold = 0.1
                self.vector_search_threshold = 0.05
            
            print(f"   Thresholds: sim={self.min_similarity_threshold}, search={self.vector_search_threshold}")
            return True
        else:
            print(f"❌ Unknown model key: {model_key}")
            print(f"✅ Available models: {list(VIETNAMESE_EMBEDDING_MODELS.keys())}")
            return False

# Document Config (unchanged)
@dataclass  
class DocumentConfig:
    """Cấu hình xử lý văn bản"""
    
    supported_formats: List[str] = None
    vietnamese_legal_patterns: Dict[str, str] = None
    legal_document_indicators: List[str] = None
    section_priority_order: List[str] = None
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['.pdf', '.txt', '.docx']
        
        if self.vietnamese_legal_patterns is None:
            self.vietnamese_legal_patterns = {
                'chuong': r'(?:^|\n)\s*Chương\s+([IVX\d]+)\s*[.:]?\s*([^\n]*)',
                'dieu': r'(?:^|\n)\s*Điều\s+(\d+[a-z]?)\s*[.:]?\s*([^\n]*)', 
                'khoan': r'(?:^|\n)\s*(\d+)\.\s+([^\n]+)',
                'diem': r'(?:^|\n)\s*([a-z]+)\)\s+([^\n]+)',
                'legal_reference': r'(Luật|Nghị định|Thông tư|Quyết định)\s+số\s+\d+[^\n]*',
                'article_full': r'Điều\s+(\d+[a-z]?)\s+([^\n]+?)(?=\n|$)',
                'section_header': r'(?:^|\n)((?:Mục|Phần|Tiết)\s+[IVX\d]+[^\n]*)',
            }
        
        if self.legal_document_indicators is None:
            self.legal_document_indicators = [
                'luật số', 'nghị định số', 'thông tư số', 'quyết định số',
                'quốc hội', 'thủ tướng chính phủ', 'bộ trưởng',
                'có hiệu lực', 'ban hành', 'quy định chi tiết'
            ]
        
        if self.section_priority_order is None:
            self.section_priority_order = [
                'chuong', 'dieu', 'khoan', 'diem'
            ]

# Web Config (unchanged)
@dataclass
class WebConfig:
    """Cấu hình xử lý dữ liệu web"""
    
    important_sections: List[str] = None
    section_aliases: Dict[str, List[str]] = None
    extraction_patterns: Dict[str, str] = None
    procedure_section_mapping: Dict[str, List[str]] = None
    section_extraction_order: List[str] = None
    
    def __post_init__(self):
        if self.important_sections is None:
            self.important_sections = [
                "Mã thủ tục", "Tên thủ tục", "Cơ quan thực hiện",
                "Yêu cầu - điều kiện", "Thành phần hồ sơ", 
                "Trình tự thực hiện", "Cách thức thực hiện",
                "Thời hạn giải quyết", "Phí", "Lệ Phí",
                "Căn cứ pháp lý", "Kết quả thực hiện", "Biểu mẫu"
            ]
        
        if self.section_aliases is None:
            self.section_aliases = {
                "Mã thủ tục": ["Mã số thủ tục", "Mã TTHC", "Số thủ tục"],
                "Tên thủ tục": ["Tên", "Tiêu đề", "Thủ tục"],
                "Cơ quan thực hiện": ["Cơ quan có thẩm quyền", "Nơi thực hiện", "Cơ quan giải quyết"],
                "Yêu cầu - điều kiện": ["Điều kiện", "Yêu cầu", "Đối tượng áp dụng", "Điều kiện thực hiện"],
                "Thành phần hồ sơ": ["Hồ sơ", "Giấy tờ cần thiết", "Tài liệu cần có", "Thành phần", "Hồ sơ gồm"],
                "Trình tự thực hiện": ["Quy trình thực hiện", "Các bước thực hiện", "Trình tự", "Quy trình"],
                "Cách thức thực hiện": ["Phương thức thực hiện", "Hình thức thực hiện", "Cách thực hiện"],
                "Thời hạn giải quyết": ["Thời gian giải quyết", "Thời hạn", "Thời gian xử lý"],
                "Phí": ["Chi phí", "Mức phí", "Phí dịch vụ"],
                "Lệ Phí": ["Lệ phí", "Phí lệ phí"],
                "Căn cứ pháp lý": ["Cơ sở pháp lý", "Văn bản quy định", "Theo quy định", "Căn cứ"],
                "Kết quả thực hiện": ["Kết quả", "Sản phẩm", "Được cấp gì", "Thành quả"],
                "Biểu mẫu": ["Mẫu đơn", "Form", "Các biểu mẫu", "Mẫu"]
            }
        
        if self.extraction_patterns is None:
            self.extraction_patterns = {
                'section_header': r'(?:^|\n)\s*({section_name})\s*:?\s*\n',
                'section_content': r'({section_name})\s*:?\s*\n\s*(.*?)(?=\n\s*[A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]{{3,}}|\n\s*$|$)',
                'numbered_list': r'(\d+\.\s*[^\n]+)',
                'bullet_list': r'([-+*]\s*[^\n]+)',
                'money_pattern': r'(\d+(?:,\d+)*(?:\.\d+)?\s*(?:đồng|VNĐ|vnđ))',
                'time_pattern': r'(\d+\s*(?:ngày|tháng|năm|tuần|giờ|phút))',
                'legal_reference_pattern': r'((?:Luật|Nghị định|Thông tư|Quyết định)\s+số\s+\d+[^\n.;]*)',
                'procedure_step_pattern': r'(?:Bước|Giai đoạn)\s*\d+[^\n]*',
                'requirement_pattern': r'(?:Điều kiện|Yêu cầu|Đối tượng)[^\n:]*:([^\n]+)',
            }
        
        if self.procedure_section_mapping is None:
            self.procedure_section_mapping = {
                'hồ sơ': ['Thành phần hồ sơ', 'Yêu cầu - điều kiện'],
                'thời gian': ['Thời hạn giải quyết'],
                'lệ phí': ['Phí', 'Lệ Phí'],
                'quy trình': ['Trình tự thực hiện', 'Cách thức thực hiện'],
                'điều kiện': ['Yêu cầu - điều kiện'],
                'thủ tục': ['Tên thủ tục', 'Mã thủ tục'],
                'cơ quan': ['Cơ quan thực hiện'],
                'kết quả': ['Kết quả thực hiện'],
                'biểu mẫu': ['Biểu mẫu'],
                'pháp lý': ['Căn cứ pháp lý']
            }
        
        if self.section_extraction_order is None:
            self.section_extraction_order = [
                "Mã thủ tục", "Tên thủ tục", 
                "Yêu cầu - điều kiện", "Thành phần hồ sơ",
                "Trình tự thực hiện", "Thời hạn giải quyết",
                "Phí", "Lệ Phí", "Cơ quan thực hiện",
                "Căn cứ pháp lý", "Kết quả thực hiện", "Biểu mẫu"
            ]

# Web procedures (unchanged)
XUATNHAPCANH_WEB_PROCEDURES = {
    "Cấp hộ chiếu phổ thông ở trong nước (thực hiện tại cấp tỉnh)": "29497",
    "Gia hạn tạm trú cho người đã được cấp giấy miễn thị thực tại Phòng Quản lý xuất nhập cảnh Công an tỉnh": "35700",
    "Thủ tục cấp giấy phép xuất nhập cảnh cho người không quốc tịch cư trú tại Việt Nam": "35699", 
    "Trình báo mất giấy thông hành (thực hiện tại cấp tỉnh)": "35694",
    "Trình báo mất hộ chiếu phổ thông (thực hiện tại cấp tỉnh)": "35714",
    "Cấp thẻ tạm trú cho người nước ngoài tại Việt Nam tại Công an cấp tỉnh": "52392",
    "Cấp thị thực cho người nước ngoài tại Việt Nam (thực hiện tại cấp tỉnh)": "35697",
    "Gia hạn tạm trú cho người nước ngoài tại Việt Nam (thực hiện tại cấp tỉnh)": "35696",
    "Khôi phục giá trị sử dụng hộ chiếu phổ thông (thực hiện tại cấp tỉnh)": "35692",
    "Cấp thẻ thường trú cho người nước ngoài tại Việt Nam (thực hiện tại cấp tỉnh)": "54873",
    "Trình báo mất thẻ ABTC (thực hiện tại cấp tỉnh)": "54713"
}

# Keywords (unchanged)
XUATNHAPCANH_KEYWORDS = {
    'passport': {
        'main': ['hộ chiếu', 'passport'],
        'types': ['phổ thông', 'ngoại giao', 'công vụ'],
        'actions': ['cấp', 'gia hạn', 'đổi', 'cấp lại', 'trình báo mất', 'khôi phục']
    },
    'visa': {
        'main': ['thị thực', 'visa'],
        'types': ['du lịch', 'công tác', 'định cư', 'học tập'],
        'actions': ['cấp', 'gia hạn', 'miễn thị thực']
    },
    'residence': {
        'main': ['tạm trú', 'thường trú', 'cư trú'],
        'documents': ['thẻ tạm trú', 'thẻ thường trú', 'giấy phép cư trú']
    },
    'entry_exit': {
        'main': ['xuất cảnh', 'nhập cảnh', 'xuất nhập cảnh'],
        'documents': ['giấy thông hành', 'thẻ ABTC']
    },
    'legal_structure': {
        'levels': ['điều', 'khoản', 'điểm', 'chương'],
        'documents': ['luật', 'nghị định', 'thông tư', 'quyết định']
    }
}

# CẬP NHẬT: Enhanced prompts cho 3 context types
LEGAL_DOMINANT_PROMPT = """Bạn là chuyên gia PHÁP LUẬT xuất nhập cảnh Việt Nam.

NGUYÊN TẮC TRẢ LỜI (LEGAL FOCUS):
✅ Ưu tiên trích dẫn CHÍNH XÁC từ văn bản pháp luật
✅ Nêu rõ Điều, Khoản, Điểm cụ thể
✅ Ghi rõ tên văn bản và năm ban hành
✅ Giải thích ý nghĩa pháp lý

THÔNG TIN PHÁP LUẬT:
{context}

CÂU HỎI: {question}

YÊU CẦU: Trả lời dựa trên VĂN BẢN PHÁP LUẬT, trích dẫn chính xác điều khoản.

TRẢ LỜI:"""

PROCEDURE_DOMINANT_PROMPT = """Bạn là chuyên viên THỦ TỤC HÀNH CHÍNH xuất nhập cảnh.

NGUYÊN TẮC TRẢ LỜI (PROCEDURE FOCUS):
✅ Hướng dẫn cụ thể từng bước thực hiện
✅ Nêu rõ hồ sơ, lệ phí, thời gian, địa điểm
✅ Thông tin thực tế từ Cổng dịch vụ công
✅ Tư vấn thực tiễn cho người dân

THÔNG TIN THỦ TỤC:
{context}

CÂU HỎI: {question}

YÊU CẦU: Hướng dẫn cụ thể thủ tục thực hiện, nêu rõ các bước.

TRẢ LỜI:"""

MIXED_CONTEXT_PROMPT = """Bạn là chuyên gia TƯ VẤN PHÁP LUẬT và THỦ TỤC xuất nhập cảnh.

NGUYÊN TẮC TRẢ LỜI (MIXED):
✅ Kết hợp căn cứ pháp lý + hướng dẫn thực tiễn
✅ Trích dẫn điều luật + giải thích thủ tục
✅ Đảm bảo tính chính xác và thực tiễn
✅ Phân biệt rõ "quy định pháp luật" vs "thủ tục thực hiện"

THÔNG TIN THAM KHẢO:
{context}

CÂU HỎI: {question}

YÊU CẦU: Trả lời đầy đủ cả khía cạnh pháp lý và thủ tục thực hiện.

TRẢ LỜI:"""

# Global instances
config = RAGConfig()
doc_config = DocumentConfig()
web_config = WebConfig()

# Helper functions (unchanged except embedding model)
def get_procedure_code_enhanced(query: str) -> Optional[str]:
    """Tìm mã thủ tục từ query"""
    query_lower = query.lower()
    
    best_match = None
    best_score = 0
    
    for procedure_name, code in XUATNHAPCANH_WEB_PROCEDURES.items():
        procedure_words = set(procedure_name.lower().split())
        query_words = set(query_lower.split())
        
        intersection = procedure_words & query_words
        if len(intersection) > 0:
            jaccard_score = len(intersection) / len(query_words | procedure_words)
            word_coverage = len(intersection) / len(procedure_words)
            score = (jaccard_score + word_coverage) / 2
            
            if score > best_score and score > 0.3:
                best_score = score
                best_match = code
    
    if best_match:
        return best_match
    
    keyword_mapping = {
        'hộ chiếu': ["29497", "35714", "35692"],
        'visa': ["35697"],
        'thị thực': ["35697", "35700"],
        'tạm trú': ["52392", "35696"],
        'thường trú': ["54873"],
        'xuất nhập cảnh': ["35699"],
        'thẻ abtc': ["54713"],
        'giấy thông hành': ["35694"]
    }
    
    for keyword, codes in keyword_mapping.items():
        if keyword in query_lower:
            return codes[0]
    
    return None

def get_config_summary_enhanced() -> dict:
    """Enhanced config summary"""
    return {
        'domain': config.domain,
        'embedding_model': config.embedding_model,
        'available_models': list(VIETNAMESE_EMBEDDING_MODELS.keys()),
        'recommended_model': 'e5_base',
        'chunk_size': config.chunk_size,
        'chunk_overlap': config.chunk_overlap,
        'search_k': config.search_k,
        'min_similarity_threshold': config.min_similarity_threshold,
        'total_procedures': len(XUATNHAPCANH_WEB_PROCEDURES),
        'important_sections': len(web_config.important_sections),
        'legal_patterns': len(doc_config.vietnamese_legal_patterns),
        'has_gemini_key': bool(config.gemini_api_key),
        'enhanced_features': [
            'e5_base_embedding_model',
            'entity_reranking_support',
            'query_normalization',
            'separated_context_building',
            'smart_prompt_templates',
            'legal_structure_chunking'
        ]
    }

def switch_to_best_vietnamese_model():
    """CẬP NHẬT: Quick switch to best model"""
    config.switch_embedding_model('e5_base')
    return config.embedding_model

# CẬP NHẬT: New function for model testing
def test_embedding_model(model_key: str) -> Dict[str, Any]:
    """Test embedding model with sample queries"""
    if model_key not in VIETNAMESE_EMBEDDING_MODELS:
        return {'success': False, 'error': f'Unknown model: {model_key}'}
    
    test_queries = [
        "Điều kiện cấp hộ chiếu phổ thông",
        "Thủ tục làm thị thực du lịch",
        "Lệ phí gia hạn tạm trú"
    ]
    
    return {
        'success': True,
        'model': VIETNAMESE_EMBEDDING_MODELS[model_key],
        'test_queries': test_queries,
        'recommendation': 'Run actual embedding test with these queries'
    }