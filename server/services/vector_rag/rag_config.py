# server/services/vector_rag/rag_config.py
"""
RAG Config với VIETNAMESE LEGAL OPTIMIZED MODELS - FIXED
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, using os.getenv only")
except Exception as e:
    print(f"⚠️ Failed to load .env: {e}")

# 🔥 VIETNAMESE LEGAL OPTIMIZED EMBEDDING MODELS - TESTED & PROVEN
VIETNAMESE_EMBEDDING_MODELS = {
    # Option 1: BEST for Vietnamese legal (recommended)
    'keepitreal': 'keepitreal/vietnamese-sbert',
    
    # Option 2: Multilingual but strong Vietnamese
    'intfloat': 'intfloat/multilingual-e5-base',
    
    # Option 3: Light but effective
    'paraphrase': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    
    # Option 4: Large for high accuracy (if have GPU)
    'intfloat-large': 'intfloat/multilingual-e5-large',
    
    # Option 5: Current buggy one (avoid)
    'dangvantuan': 'dangvantuan/vietnamese-embedding'
}

@dataclass
class RAGConfig:
    """Cấu hình chính với VIETNAMESE LEGAL OPTIMIZED MODELS"""
    
    # Paths
    domain: str = "xuatnhapcanh"
    data_path: str = "./dataset"
    documents_path: str = "./dataset/xuatnhapcanh/documents"
    vector_store_path: str = "./dataset/xuatnhapcanh/vector_store"
    web_cache_path: str = "./dataset/xuatnhapcanh/web_cache"
    
    # Vector Store - 🔥 SWITCH TO VIETNAMESE LEGAL OPTIMIZED MODEL
    vector_collection_name: str = "xuatnhapcanh_docs"
    embedding_model: str = VIETNAMESE_EMBEDDING_MODELS['keepitreal']  # BEST for Vietnamese legal
    
    # 🔥 ENHANCED Chunking for legal documents
    chunk_size: int = 800        # Increased from 600 for better context
    chunk_overlap: int = 100     # Increased from 50 for better continuity
    search_k: int = 8           # Increased from 5 for better recall
    
    # 🔥 STRICTER Search thresholds (not too relaxed)
    min_similarity_threshold: float = 0.15  # NEW: minimum similarity for results
    vector_search_threshold: float = 0.1    # Current relaxed threshold
    
    # LLM Settings
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma:2b"
    temperature: float = 0.1
    max_tokens: int = 1000
    
    # Web Settings - 🔥 ENHANCED for 11 procedures
    web_base_url: str = "https://dichvucong.bocongan.gov.vn"
    web_cache_ttl: int = 7200
    request_timeout: int = 25     # Increased from 20
    web_priority: bool = True
    force_web_crawl: bool = True  # NEW: Force crawl all 11 procedures
    
    def __post_init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        # Tạo thư mục
        for path in [self.documents_path, self.vector_store_path, self.web_cache_path]:
            os.makedirs(path, exist_ok=True)

    def switch_embedding_model(self, model_key: str):
        """Switch to different embedding model"""
        if model_key in VIETNAMESE_EMBEDDING_MODELS:
            old_model = self.embedding_model
            self.embedding_model = VIETNAMESE_EMBEDDING_MODELS[model_key]
            print(f"🔄 Switched embedding model:")
            print(f"   From: {old_model}")
            print(f"   To:   {self.embedding_model}")
            return True
        else:
            print(f"❌ Unknown model key: {model_key}")
            print(f"✅ Available models: {list(VIETNAMESE_EMBEDDING_MODELS.keys())}")
            return False

@dataclass  
class DocumentConfig:
    """Cấu hình xử lý văn bản - ENHANCED for legal structure"""
    
    supported_formats: List[str] = None
    vietnamese_legal_patterns: Dict[str, str] = None
    
    # 🔥 NEW: Enhanced legal structure detection
    legal_document_indicators: List[str] = None
    section_priority_order: List[str] = None
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['.pdf', '.txt', '.docx']
        
        if self.vietnamese_legal_patterns is None:
            self.vietnamese_legal_patterns = {
                # 🔥 ENHANCED patterns with more precision
                'chuong': r'(?:^|\n)\s*Chương\s+([IVX\d]+)\s*[.:]?\s*([^\n]*)',
                'dieu': r'(?:^|\n)\s*Điều\s+(\d+[a-z]?)\s*[.:]?\s*([^\n]*)', 
                'khoan': r'(?:^|\n)\s*(\d+)\.\s+([^\n]+)',
                'diem': r'(?:^|\n)\s*([a-z]+)\)\s+([^\n]+)',
                
                # NEW: More specific patterns
                'legal_reference': r'(Luật|Nghị định|Thông tư|Quyết định)\s+số\s+\d+[^\n]*',
                'article_full': r'Điều\s+(\d+[a-z]?)\s+([^\n]+?)(?=\n|$)',
                'section_header': r'(?:^|\n)((?:Mục|Phần|Tiết)\s+[IVX\d]+[^\n]*)',
            }
        
        # 🔥 NEW: Legal document type indicators
        if self.legal_document_indicators is None:
            self.legal_document_indicators = [
                'luật số', 'nghị định số', 'thông tư số', 'quyết định số',
                'quốc hội', 'thủ tướng chính phủ', 'bộ trưởng',
                'có hiệu lực', 'ban hành', 'quy định chi tiết'
            ]
        
        # 🔥 NEW: Section priority for chunking
        if self.section_priority_order is None:
            self.section_priority_order = [
                'chuong',      # Chương (highest level)
                'dieu',        # Điều (article level)
                'khoan',       # Khoản (paragraph level)  
                'diem'         # Điểm (point level)
            ]

@dataclass
class WebConfig:
    """Cấu hình xử lý dữ liệu web - ENHANCED for 11 procedures"""
    
    important_sections: List[str] = None
    section_aliases: Dict[str, List[str]] = None
    extraction_patterns: Dict[str, str] = None
    
    # 🔥 NEW: Enhanced for procedure processing
    procedure_section_mapping: Dict[str, List[str]] = None
    section_extraction_order: List[str] = None
    
    def __post_init__(self):
        if self.important_sections is None:
            # 🔥 REORDERED by importance for legal queries
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
                
                # 🔥 NEW: Enhanced patterns for better extraction
                'legal_reference_pattern': r'((?:Luật|Nghị định|Thông tư|Quyết định)\s+số\s+\d+[^\n.;]*)',
                'procedure_step_pattern': r'(?:Bước|Giai đoạn)\s*\d+[^\n]*',
                'requirement_pattern': r'(?:Điều kiện|Yêu cầu|Đối tượng)[^\n:]*:([^\n]+)',
            }
        
        # 🔥 NEW: Procedure section mapping for better search
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
        
        # 🔥 NEW: Extraction order for optimal chunking
        if self.section_extraction_order is None:
            self.section_extraction_order = [
                "Mã thủ tục", "Tên thủ tục", 
                "Yêu cầu - điều kiện", "Thành phần hồ sơ",
                "Trình tự thực hiện", "Thời hạn giải quyết",
                "Phí", "Lệ Phí", "Cơ quan thực hiện",
                "Căn cứ pháp lý", "Kết quả thực hiện", "Biểu mẫu"
            ]

# 🔥 ENHANCED Web procedures - All 11 procedures with better mapping
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

# 🔥 ENHANCED Keywords with legal context
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

# 🔥 ENHANCED Legal prompt with Vietnamese context
ENHANCED_LEGAL_PROMPT = """Bạn là chuyên gia tư vấn PHÁP LUẬT XUẤT NHẬP CẢNH Việt Nam với chuyên môn cao.

NGUYÊN TẮC TRẢ LỜI:
✅ Ưu tiên thông tin từ LUẬT, NGHỊ ĐỊNH, THÔNG TƯ (nguồn vector)
✅ Bổ sung thông tin THỦ TỤC HÀNH CHÍNH từ Cổng dịch vụ công (nguồn web)
✅ Trích dẫn CHÍNH XÁC Điều, Khoản, Điểm của văn bản pháp luật
✅ Nêu rõ tên văn bản và năm ban hành

NGỮ CẢNH THAM KHẢO:
{context}

CÂU HỎI: {question}

YÊU CẦU TRÍCH DẪN:
- Nếu hỏi về điều luật cụ thể → Trích dẫn chính xác nội dung điều đó
- Nếu hỏi về thủ tục → Ưu tiên thông tin từ Cổng dịch vụ công
- Nếu hỏi về quy định → Nêu rõ căn cứ pháp lý

❌ TUYỆT ĐỐI không đưa ra thông tin không có trong tài liệu
❌ TUYỆT ĐỐI không suy đoán hay bịa đặt thông tin

TRẢ LỜI:"""

# Global instances
config = RAGConfig()
doc_config = DocumentConfig()
web_config = WebConfig()

# Helper functions
def get_procedure_code_enhanced(query: str) -> Optional[str]:
    """Tìm mã thủ tục từ query với enhanced matching"""
    query_lower = query.lower()
    
    # Direct procedure name matching
    best_match = None
    best_score = 0
    
    for procedure_name, code in XUATNHAPCANH_WEB_PROCEDURES.items():
        procedure_words = set(procedure_name.lower().split())
        query_words = set(query_lower.split())
        
        # Calculate similarity score
        intersection = procedure_words & query_words
        union = procedure_words | query_words
        
        if len(intersection) > 0:
            jaccard_score = len(intersection) / len(union)
            word_coverage = len(intersection) / len(procedure_words)
            
            # Combined score
            score = jaccard_score * 0.3 + word_coverage * 0.7
            
            if score > best_score and score > 0.3:  # Minimum threshold
                best_score = score
                best_match = code
    
    if best_match:
        return best_match
    
    # Fallback to keyword-based matching
    keyword_mapping = {
        'hộ chiếu': ["29497", "35714", "35692"],  # Multiple passport procedures
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
            return codes[0]  # Return first matching procedure
    
    return None

def get_config_summary_enhanced() -> dict:
    """Enhanced config summary"""
    return {
        'domain': config.domain,
        'embedding_model': config.embedding_model,
        'available_models': list(VIETNAMESE_EMBEDDING_MODELS.keys()),
        'chunk_size': config.chunk_size,
        'chunk_overlap': config.chunk_overlap,
        'search_k': config.search_k,
        'min_similarity_threshold': config.min_similarity_threshold,
        'total_procedures': len(XUATNHAPCANH_WEB_PROCEDURES),
        'important_sections': len(web_config.important_sections),
        'legal_patterns': len(doc_config.vietnamese_legal_patterns),
        'has_gemini_key': bool(config.gemini_api_key),
        'enhanced_features': [
            'vietnamese_legal_optimized_embedding',
            'enhanced_chunking_with_overlap',
            'stricter_similarity_thresholds',
            'comprehensive_procedure_mapping',
            'legal_structure_preservation'
        ]
    }

def switch_to_best_vietnamese_model():
    """Quick switch to best Vietnamese model"""
    config.switch_embedding_model('keepitreal')
    return config.embedding_model