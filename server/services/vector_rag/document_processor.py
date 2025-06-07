# server/services/vector_rag/document_processor.py
"""
Document processor - OPTIMIZED & CONCISE
"""
import os
import re
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
import logging

# Import libraries with fallbacks
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

from services.vector_rag.rag_config import config

logger = logging.getLogger(__name__)

class Document:
    """Document class"""
    def __init__(self, content: str, metadata: Dict[str, Any] = None):
        self.content = content
        self.metadata = metadata or {}

class DocumentProcessor:
    """Optimized Document processor"""
    
    def __init__(self):
        # Core patterns only
        self.legal_patterns = {
            'dieu': r'Điều\s+(\d+[a-z]?)\s*[.:]?\s*([^\n]*)',
            'khoan': r'(\d+)\.\s+([^\n]+)',
            'legal_doc': r'(Luật|Nghị định|Thông tư)\s+số\s+\d+[^\n]*'
        }
        
        # Supported formats
        self.supported_formats = ['.pdf', '.txt', '.docx']
        
        # Chunking settings
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap
        self.min_chunk_size = 150
        
        logger.info(f"🔧 DocumentProcessor initialized")
    
    def load_text_file(self, file_path: str) -> str:
        """Load text file"""
        encodings = ['utf-8', 'utf-8-sig', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                break
        
        return ""
    
    def load_pdf_file(self, file_path: str) -> str:
        """Load PDF file"""
        if not PDF_AVAILABLE:
            logger.warning(f"PyPDF2 not available, skipping {file_path}")
            return ""
        
        try:
            text_parts = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            # Clean up
                            cleaned = re.sub(r'\s+', ' ', page_text)
                            text_parts.append(cleaned)
                    except Exception:
                        continue
                        
            return '\n\n'.join(text_parts)
        except Exception as e:
            logger.error(f"PDF load failed {file_path}: {e}")
            return ""
    
    def load_docx_file(self, file_path: str) -> str:
        """Load DOCX file"""
        if not DOCX_AVAILABLE:
            logger.warning(f"python-docx not available, skipping {file_path}")
            return ""
        
        try:
            doc = docx.Document(file_path)
            paragraphs = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    paragraphs.append(paragraph.text)
            
            return '\n\n'.join(paragraphs)
        except Exception as e:
            logger.error(f"DOCX load failed {file_path}: {e}")
            return ""
    
    def detect_document_type(self, file_path: str, content: str) -> Dict[str, Any]:
        """Simple document type detection"""
        file_name = Path(file_path).name.lower()
        content_lower = content.lower()
        
        # Document type scoring
        doc_types = {
            'luat': {
                'file_keywords': ['luat', 'law'],
                'content_keywords': ['luật số', 'quốc hội'],
                'legal_level': 'luật'
            },
            'nghidinh': {
                'file_keywords': ['nghidinh', 'decree'],
                'content_keywords': ['nghị định số', 'thủ tướng'],
                'legal_level': 'nghị_định'
            },
            'thongtu': {
                'file_keywords': ['thongtu', 'circular'],
                'content_keywords': ['thông tư số', 'bộ trưởng'],
                'legal_level': 'thông_tư'
            }
        }
        
        best_type = 'general'
        best_score = 0
        
        for doc_type, config in doc_types.items():
            score = 0
            
            # File name scoring
            if any(kw in file_name for kw in config['file_keywords']):
                score += 0.5
            
            # Content scoring
            if any(kw in content_lower for kw in config['content_keywords']):
                score += 0.5
            
            if score > best_score:
                best_score = score
                best_type = doc_type
        
        # Legal structure detection
        has_legal_structure = self._has_legal_structure(content)
        
        return {
            'primary_type': best_type,
            'confidence': best_score,
            'legal_level': doc_types.get(best_type, {}).get('legal_level', 'unknown'),
            'has_legal_structure': has_legal_structure
        }
    
    def _has_legal_structure(self, content: str) -> bool:
        """Check for legal structure"""
        dieu_matches = len(re.findall(self.legal_patterns['dieu'], content, re.IGNORECASE))
        khoan_matches = len(re.findall(self.legal_patterns['khoan'], content, re.IGNORECASE))
        
        return dieu_matches >= 2 or khoan_matches >= 5
    
    def chunk_content(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """Optimized chunking"""
        if not content.strip():
            return []
        
        # Try legal structure chunking first
        if metadata.get('has_legal_structure', False):
            chunks = self._chunk_by_articles(content)
            if chunks and len(chunks) > 1:
                return chunks
        
        # Fallback to simple chunking
        return self._simple_chunk(content)
    
    def _chunk_by_articles(self, content: str) -> List[str]:
        """Chunk by legal articles"""
        chunks = []
        dieu_pattern = self.legal_patterns['dieu']
        
        # Find all articles
        matches = list(re.finditer(dieu_pattern, content, re.IGNORECASE))
        
        if len(matches) < 2:
            return []
        
        for i, match in enumerate(matches):
            start_pos = match.start()
            
            # Determine end position
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(content)
            
            chunk_content = content[start_pos:end_pos].strip()
            
            if len(chunk_content) >= self.min_chunk_size:
                if len(chunk_content) <= self.chunk_size:
                    chunks.append(chunk_content)
                else:
                    # Split long article
                    sub_chunks = self._simple_chunk(chunk_content)
                    chunks.extend(sub_chunks)
        
        return chunks
    
    def _simple_chunk(self, content: str) -> List[str]:
        """Simple overlap chunking"""
        chunks = []
        
        for i in range(0, len(content), self.chunk_size - self.chunk_overlap):
            chunk = content[i:i + self.chunk_size]
            
            # Find good break point
            if i + self.chunk_size < len(content):
                # Try to break at sentence end
                last_sentence = chunk.rfind('. ')
                if last_sentence > len(chunk) * 0.7:
                    chunk = chunk[:last_sentence + 1]
            
            if chunk.strip() and len(chunk.strip()) >= self.min_chunk_size:
                chunks.append(chunk.strip())
        
        return chunks
    
    def extract_legal_info(self, content: str) -> Dict[str, Any]:
        """Extract basic legal information"""
        info = {
            'articles': [],
            'legal_docs': [],
            'content_stats': {}
        }
        
        # Extract articles
        for match in re.finditer(self.legal_patterns['dieu'], content, re.IGNORECASE):
            info['articles'].append({
                'number': match.group(1),
                'title': match.group(2).strip() if match.group(2) else "",
                'position': match.start()
            })
        
        # Extract legal documents
        for match in re.finditer(self.legal_patterns['legal_doc'], content, re.IGNORECASE):
            info['legal_docs'].append(match.group(0))
        
        # Content stats
        info['content_stats'] = {
            'total_length': len(content),
            'articles_count': len(info['articles']),
            'legal_docs_count': len(info['legal_docs'])
        }
        
        return info
    
    def process_file(self, file_path: str) -> List[Document]:
        """Process single file"""
        file_ext = Path(file_path).suffix.lower()
        file_name = Path(file_path).name
        
        if file_ext not in self.supported_formats:
            logger.warning(f"Unsupported format: {file_ext}")
            return []
        
        logger.info(f"📄 Processing: {file_name}")
        
        # Load content
        content = ""
        if file_ext == '.txt':
            content = self.load_text_file(file_path)
        elif file_ext == '.pdf':
            content = self.load_pdf_file(file_path)
        elif file_ext == '.docx':
            content = self.load_docx_file(file_path)
        
        if not content.strip():
            logger.warning(f"Empty content: {file_name}")
            return []
        
        # Analyze document
        doc_metadata = self.detect_document_type(file_path, content)
        legal_info = self.extract_legal_info(content)
        
        # Chunk content
        chunks = self.chunk_content(content, doc_metadata)
        
        if not chunks:
            logger.warning(f"No valid chunks: {file_name}")
            return []
        
        # Create documents
        documents = []
        for i, chunk in enumerate(chunks):
            metadata = {
                'source': file_path,
                'file_name': file_name,
                'file_type': file_ext,
                'chunk_id': i,
                'total_chunks': len(chunks),
                'doc_type': doc_metadata['primary_type'],
                'legal_level': doc_metadata['legal_level'],
                'has_legal_structure': doc_metadata['has_legal_structure'],
                'processed_at': datetime.now().isoformat(),
                'content_type': 'legal_document',
                'chunk_size': len(chunk)
            }
            
            documents.append(Document(content=chunk, metadata=metadata))
        
        logger.info(f"✅ Created {len(documents)} chunks from {file_name}")
        return documents
    
    def process_directory(self, directory_path: str = None) -> List[Document]:
        """Process directory"""
        if directory_path is None:
            directory_path = config.documents_path
        
        if not os.path.exists(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return []
        
        logger.info(f"📁 Processing documents from: {directory_path}")
        
        all_documents = []
        stats = {'processed': 0, 'failed': 0, 'total_chunks': 0}
        
        for file_path in Path(directory_path).rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                try:
                    docs = self.process_file(str(file_path))
                    if docs:
                        all_documents.extend(docs)
                        stats['processed'] += 1
                        stats['total_chunks'] += len(docs)
                    else:
                        stats['failed'] += 1
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    stats['failed'] += 1
        
        logger.info(f"✅ Processing complete:")
        logger.info(f"   📄 Files: {stats['processed']} processed, {stats['failed']} failed")
        logger.info(f"   📝 Total chunks: {stats['total_chunks']}")
        
        return all_documents