# app/server/services/vector_rag/rag_config.py - UPDATED FOR DOCX Q&A
"""
RAG Config - UPDATED: Approach "Legal Article Extraction + DOCX Q&A"
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

# Legal patterns - giữ nguyên
SIMPLE_LEGAL_PATTERNS = {
    'article': r'Điều\s+(\d+[a-z]?)\s*[.:]?\s*([^\n]*)',
    'doc_number_law': r'Luật\s+số\s+(\d+/\d{4}/QH\d+)',
    'doc_number_decree': r'Nghị\s+định\s+số\s+(\d+/\d{4}/NĐ-CP)',
    'doc_number_circular': r'Thông\s+tư\s+số\s+(\d+/\d{4}/TT-[\w]+)',
}

# Keywords - giữ nguyên
VIETNAMESE_KEYWORDS = {
    'passport': ['hộ chiếu', 'passport'],
    'visa': ['thị thực', 'visa'],
    'exit_entry': ['xuất cảnh', 'nhập cảnh'],
    'children': ['trẻ em', 'dưới 14 tuổi'],
    'procedure': ['thủ tục', 'quy trình'],
    'documents': ['hồ sơ', 'giấy tờ'],
    'fee': ['lệ phí', 'phí'],
    'timeline': ['thời hạn', 'thời gian']
}

# UPDATED: Doc types cho DOCX Q&A
SIMPLE_DOC_TYPES = {
    'law': {'priority': 1.0, 'prefix': 'L'},
    'decree': {'priority': 0.9, 'prefix': 'NĐ'},
    'circular': {'priority': 0.8, 'prefix': 'TT'},
    'docx_qa': {'priority': 1.2, 'prefix': 'QA'}  # UPDATED: DOCX Q&A có priority cao nhất
}

@dataclass
class RAGConfig:
    """UPDATED: Config cho Legal Article Extraction + DOCX Q&A"""
    
    # Paths - giữ nguyên
    domain: str = "xuatnhapcanh"
    data_path: str = "./dataset"
    documents_path: str = "./dataset/xuatnhapcanh/documents"
    vector_store_path: str = "./dataset/xuatnhapcanh/vector_store"
    
    # Vector store - giữ nguyên
    vector_collection_name: str = "xuatnhapcanh_docs"
    embedding_model: str = "truro7/vn-law-embedding"
    chunk_size: int = 800
    chunk_overlap: int = 100
    search_k: int = 5
    
    # Search thresholds - giữ nguyên
    min_similarity_threshold: float = 0.15
    vector_search_threshold: float = 0.08
    confidence_threshold: float = 0.7
    
    # UPDATED: Features cho DOCX Q&A approach
    enable_docx_qa: bool = True             # UPDATED: Enable DOCX Q&A processing
    docx_qa_priority: float = 1.5           # UPDATED: DOCX Q&A gets higher priority
    simple_article_extraction: bool = True  # Giữ nguyên
    
    # Disabled features - giữ nguyên
    vietnamese_legal_processing: bool = False
    legal_hierarchy_awareness: bool = False
    cross_reference_extraction: bool = False
    authority_ranking_enabled: bool = False
    
    # Performance - giữ nguyên
    enable_response_caching: bool = True
    cache_size: int = 3000
    lazy_model_loading: bool = True
    max_concurrent_requests: int = 50
    request_timeout: int = 30
    
    # LLM settings - giữ nguyên
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.5-flash"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma:2b"
    gemma_conversation_analysis: bool = True
    gemma_timeout: int = 10
    gemma_cache_size: int = 100
    temperature: float = 0.1
    max_tokens: int = 600
    api_first_mode: bool = True
    
    # Quality control - giữ nguyên
    response_validation_enabled: bool = True
    single_strategy_mode: bool = True
    max_context_length: int = 3000
    
    # Monitoring - giữ nguyên
    enable_monitoring: bool = True
    log_response_quality: bool = True
    track_performance_metrics: bool = True

    def __post_init__(self):
        """Simplified initialization"""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Create directories
        for path in [self.documents_path, self.vector_store_path]:
            os.makedirs(path, exist_ok=True)
        
        # Validate config
        self._validate_simple_config()
    
    def _validate_simple_config(self):
        """Simple validation"""
        if not SIMPLE_LEGAL_PATTERNS:
            raise ValueError("Simple legal patterns not configured")
        
        if not VIETNAMESE_KEYWORDS:
            raise ValueError("Vietnamese keywords not configured")
            
        if self.min_similarity_threshold > 0.3:
            print("⚠️ Warning: High similarity threshold may reduce recall")
        
        print("✅ Simple RAG config validated")
    
    # Methods - giữ nguyên
    def get_legal_pattern(self, pattern_name: str) -> Optional[str]:
        """Get simple legal pattern"""
        return SIMPLE_LEGAL_PATTERNS.get(pattern_name)
    
    def get_keywords(self, category: str) -> List[str]:
        """Get Vietnamese keywords by category"""
        return VIETNAMESE_KEYWORDS.get(category, [])
    
    def get_doc_priority(self, doc_type: str) -> float:
        """Get document type priority"""
        return SIMPLE_DOC_TYPES.get(doc_type, {}).get('priority', 0.5)
    
    def enable_quality_mode(self):
        """Simple quality mode"""
        self.confidence_threshold = 0.8
        self.min_similarity_threshold = 0.2
        self.search_k = 3
        print("🛡️ Quality mode enabled")
    
    def enable_performance_mode(self):
        """Simple performance mode"""
        self.confidence_threshold = 0.6
        self.min_similarity_threshold = 0.1
        self.search_k = 8
        self.enable_response_caching = True
        print("⚡ Performance mode enabled")

@dataclass  
class DocumentConfig:
    """Simple document processing config"""
    
    supported_formats: List[str] = None
    simple_patterns: Dict[str, str] = None
    doc_types: Dict[str, Dict] = None
    
    def __post_init__(self):
        if self.supported_formats is None:
            # UPDATED: Remove .json, only .docx for Q&A
            self.supported_formats = ['.docx', '.txt']
        
        if self.simple_patterns is None:
            self.simple_patterns = SIMPLE_LEGAL_PATTERNS.copy()
        
        if self.doc_types is None:
            self.doc_types = SIMPLE_DOC_TYPES.copy()

# Global instances
config = RAGConfig()
doc_config = DocumentConfig()

# UPDATED: Helper functions
def get_simple_config_summary() -> dict:
    """UPDATED: Config summary cho DOCX Q&A"""
    return {
        'approach': 'Legal Article Extraction + DOCX Q&A',  # UPDATED
        'domain': config.domain,
        'embedding_model': config.embedding_model,
        'chunk_size': config.chunk_size,
        'search_k': config.search_k,
        'features': {
            'docx_qa_enabled': config.enable_docx_qa,       # UPDATED
            'simple_article_extraction': config.simple_article_extraction,
            'complex_processing_disabled': not config.vietnamese_legal_processing
        },
        'thresholds': {
            'min_similarity': config.min_similarity_threshold,
            'vector_search': config.vector_search_threshold,
            'confidence': config.confidence_threshold
        },
        'supported_formats': doc_config.supported_formats,
        'doc_types': list(SIMPLE_DOC_TYPES.keys())
    }

def configure_for_simple_mode():
    """UPDATED: Configure for DOCX Q&A approach"""
    config.simple_article_extraction = True
    config.enable_docx_qa = True                    # UPDATED
    config.vietnamese_legal_processing = False
    config.legal_hierarchy_awareness = False
    config.cross_reference_extraction = False
    config.authority_ranking_enabled = False
    
    # Adjust thresholds for quality with DOCX Q&A backup
    config.min_similarity_threshold = 0.15
    config.vector_search_threshold = 0.08
    config.confidence_threshold = 0.7
    
    print("🎯 Configured for simple approach: Legal Article Extraction + DOCX Q&A")  # UPDATED

def validate_simple_config() -> Dict[str, Any]:
    """UPDATED: Config validation cho DOCX approach"""
    issues = []
    warnings = []
    
    # Check paths
    if not os.path.exists(config.documents_path):
        warnings.append(f"Documents path not found: {config.documents_path}")
    
    # Check model
    if not config.embedding_model:
        issues.append("No embedding model specified")
    
    # UPDATED: Check DOCX Q&A
    if not config.enable_docx_qa:
        warnings.append("DOCX Q&A disabled - may reduce answer quality")
    
    # Check thresholds
    if config.min_similarity_threshold < 0.1:
        warnings.append("Low similarity threshold may return irrelevant results")
    
    score = max(0, 1.0 - len(issues) * 0.3 - len(warnings) * 0.1)
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'warnings': warnings,
        'score': score,
        'approach': 'Legal Article Extraction + DOCX Q&A',  # UPDATED
        'recommendations': [
            "Enable DOCX Q&A for better coverage",          # UPDATED
            "Use article extraction for legal documents", 
            "Keep thresholds moderate (0.1-0.2)",
            "Process .docx files with CÂU HỎI/TRẢ LỜI format"  # UPDATED
        ]
    }