# document_processor.py - Xử lý và load tài liệu
import os
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime


from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
try:
    from langchain.document_loaders import Docx2txtLoader
    DOCX_LOADER = Docx2txtLoader
except ImportError:
    DOCX_LOADER = None
from langchain.schema import Document

from services.vector_rag.config import ChunkingConfig, SystemConfig

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Xử lý tài liệu với khả năng mở rộng cho nhiều định dạng"""
    
    def __init__(self, config: ChunkingConfig = None, system_config: SystemConfig = None):
        self.config = config or ChunkingConfig()
        self.system_config = system_config or SystemConfig()
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=self.config.separators
        )
        
        # Mapping loaders cho các định dạng file
        self.loaders = {
            '.pdf': PyPDFLoader,
            '.txt': TextLoader,
            # Có thể mở rộng thêm
             '.docx': Docx2txtLoader,
            # '.html': HTMLLoader,
        }
    
    def detect_domain(self, file_path: str) -> str:
        """Tự động phát hiện domain từ tên file hoặc nội dung"""
        file_name = Path(file_path).name.lower()
        
        # Detect từ tên file
        for domain_key, domain_name in self.system_config.domains.items():
            keywords = {
                'dich_vu_cong': ['dich_vu', 'thu_tuc', 'hanh_chinh'],
                'luat': ['luat', 'bo_luat'],
                'thong_tu': ['thong_tu', 'huong_dan'],
                'nghi_dinh': ['nghi_dinh', 'quy_dinh']
            }
            
            if domain_key in keywords:
                for keyword in keywords[domain_key]:
                    if keyword in file_name:
                        return domain_key
        
        return 'general'  # Default domain
    
    def load_documents_from_directory(self, data_path: str, domain: str = None) -> List[Document]:
        """Load tài liệu từ thư mục với phân loại domain"""
        documents = []
        
        for file_ext, loader_class in self.loaders.items():
            try:
                # Load files với extension cụ thể
                dir_loader = DirectoryLoader(
                    data_path,
                    glob=f"*{file_ext}",
                    loader_cls=loader_class,
                    show_progress=True
                )
                docs = dir_loader.load()
                
                # Thêm metadata cho domain
                for doc in docs:
                    detected_domain = domain or self.detect_domain(doc.metadata.get('source', ''))
                    doc.metadata['domain'] = detected_domain
                    doc.metadata['file_type'] = file_ext
                    doc.metadata['processed_at'] = str(datetime.now())
                
                documents.extend(docs)
                logger.info(f"Loaded {len(docs)} {file_ext} files")
                
            except Exception as e:
                logger.error(f"Error loading {file_ext} files: {str(e)}")
        
        return documents
    
    def load_single_document(self, file_path: str, domain: str = None) -> List[Document]:
        """Load một tài liệu duy nhất"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext not in self.loaders or self.loaders[file_ext] is None:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        loader_class = self.loaders[file_ext]
        loader = loader_class(file_path)
        docs = loader.load()
        
        # Add metadata
        detected_domain = domain or self.detect_domain(file_path)
        for doc in docs:
            doc.metadata['domain'] = detected_domain
            doc.metadata['file_type'] = file_ext
            doc.metadata['processed_at'] = str(datetime.now())
        
        return docs
    
    def split_documents(self, documents: List[Document], domain: str = None) -> List[Document]:
        """Chia nhỏ tài liệu thành chunks với metadata"""
        chunks = self.text_splitter.split_documents(documents)
        
        # Thêm metadata cho chunks
        for i, chunk in enumerate(chunks):
            chunk.metadata['chunk_id'] = i
            chunk.metadata['chunk_size'] = len(chunk.page_content)
            if domain:
                chunk.metadata['domain'] = domain
        
        return chunks
    
    def process_documents(self, data_path: str, domain: str = None) -> List[Document]:
        """Pipeline xử lý hoàn chỉnh"""
        logger.info(f"Processing documents from {data_path}")
        
        # Load documents
        documents = self.load_documents_from_directory(data_path, domain)
        logger.info(f"Loaded {len(documents)} documents")
        
        if not documents:
            logger.warning("No documents found!")
            return []
        
        # Split documents
        chunks = self.split_documents(documents, domain)
        logger.info(f"Created {len(chunks)} chunks")
        
        return chunks
    
    def get_document_stats(self, documents: List[Document]) -> Dict[str, Any]:
        """Thống kê tài liệu"""
        if not documents:
            return {}
        
        stats = {
            'total_documents': len(documents),
            'domains': {},
            'file_types': {},
            'total_chars': 0,
            'avg_chunk_size': 0
        }
        
        for doc in documents:
            # Domain stats
            domain = doc.metadata.get('domain', 'unknown')
            stats['domains'][domain] = stats['domains'].get(domain, 0) + 1
            
            # File type stats
            file_type = doc.metadata.get('file_type', 'unknown')
            stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1
            
            # Content stats
            stats['total_chars'] += len(doc.page_content)
        
        stats['avg_chunk_size'] = stats['total_chars'] / len(documents) if documents else 0
        
        return stats

# Factory pattern cho việc mở rộng loaders
class LoaderFactory:
    """Factory để tạo loaders cho các định dạng khác nhau"""
    
    @staticmethod
    def create_loader(file_path: str, file_type: str = None):
        """Tạo loader phù hợp cho file"""
        if not file_type:
            file_type = Path(file_path).suffix.lower()
        
        loaders = {
            '.pdf': PyPDFLoader,
            '.txt': TextLoader,
            # Có thể mở rộng
            # '.docx': lambda path: DocxLoader(path),
            # '.html': lambda path: HTMLLoader(path),
            # '.xlsx': lambda path: ExcelLoader(path),
        }
        
        if file_type in loaders:
            return loaders[file_type](file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

# Utility functions
def calculate_file_hash(file_path: str) -> str:
    """Tính hash của file để detect thay đổi"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def should_reprocess_file(file_path: str, cache_path: str) -> bool:
    """Kiểm tra xem file có cần reprocess không"""
    cache_file = Path(cache_path) / f"{Path(file_path).stem}_hash.txt"
    
    if not cache_file.exists():
        return True
    
    try:
        with open(cache_file, 'r') as f:
            cached_hash = f.read().strip()
        
        current_hash = calculate_file_hash(file_path)
        return cached_hash != current_hash
    except:
        return True