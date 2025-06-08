# server/services/vector_rag/document_processor.py
"""
Document processor - SỬA LOGIC: Chunking theo cấu trúc Điều-Khoản-Điểm
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
    """Document processor với legal chunking"""
    
    def __init__(self):
        # SỬA LOGIC: Enhanced legal patterns cho chunking
        self.legal_patterns = {
            'chapter': r'(?:^|\n)\s*Chương\s+([IVX\d]+)\s*[.:]?\s*([^\n]*)',
            'article': r'(?:^|\n)\s*Điều\s+(\d+[a-z]?)\s*[.:]?\s*([^\n]*)',
            'paragraph': r'(?:^|\n)\s*(\d+)\.\s+([^\n]+)',
            'point': r'(?:^|\n)\s*([a-z]+)\)\s+([^\n]+)',
            'legal_doc': r'(Luật|Nghị định|Thông tư)\s+số\s+\d+[^\n]*'
        }
        
        # Supported formats
        self.supported_formats = ['.pdf', '.txt', '.docx']
        
        # SỬA LOGIC: Chunking settings for legal structure
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap
        self.min_chunk_size = 150
        self.max_article_length = 1200  # Max length for single article
        
        logger.info(f"🔧 DocumentProcessor với legal chunking")
    
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
        """Detect document type"""
        file_name = Path(file_path).name.lower()
        content_lower = content.lower()
        
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
        
        for doc_type, config_item in doc_types.items():
            score = 0
            
            if any(kw in file_name for kw in config_item['file_keywords']):
                score += 0.5
            
            if any(kw in content_lower for kw in config_item['content_keywords']):
                score += 0.5
            
            if score > best_score:
                best_score = score
                best_type = doc_type
        
        has_legal_structure = self._has_legal_structure(content)
        
        return {
            'primary_type': best_type,
            'confidence': best_score,
            'legal_level': doc_types.get(best_type, {}).get('legal_level', 'unknown'),
            'has_legal_structure': has_legal_structure
        }
    
    def _has_legal_structure(self, content: str) -> bool:
        """Check for legal structure"""
        dieu_matches = len(re.findall(self.legal_patterns['article'], content, re.IGNORECASE))
        khoan_matches = len(re.findall(self.legal_patterns['paragraph'], content, re.IGNORECASE))
        
        return dieu_matches >= 2 or khoan_matches >= 5
    
    def chunk_content(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """SỬA LOGIC: Chunking theo cấu trúc pháp luật"""
        if not content.strip():
            return []
        
        # Try legal structure chunking first
        if metadata.get('has_legal_structure', False):
            chunks = self._chunk_by_legal_structure(content, metadata)
            if chunks and len(chunks) > 1:
                logger.info(f"✅ Chunked by legal structure: {len(chunks)} chunks")
                return chunks
        
        # Fallback to simple chunking
        logger.info("📄 Using simple chunking (no legal structure)")
        return self._simple_chunk(content)
    
    def _chunk_by_legal_structure(self, content: str, metadata: Dict[str, Any]) -> List[str]:
        """SỬA LOGIC: Chunk theo cấu trúc Điều-Khoản-Điểm"""
        chunks = []
        
        # Find all articles (Điều)
        article_matches = list(re.finditer(self.legal_patterns['article'], content, re.IGNORECASE))
        
        if len(article_matches) < 2:
            return []
        
        for i, match in enumerate(article_matches):
            start_pos = match.start()
            
            # Determine end position
            if i + 1 < len(article_matches):
                end_pos = article_matches[i + 1].start()
            else:
                end_pos = len(content)
            
            article_content = content[start_pos:end_pos].strip()
            article_num = match.group(1)
            article_title = match.group(2).strip() if match.group(2) else ""
            
            # SỬA LOGIC: Create proper legal chunk with header
            if len(article_content) >= self.min_chunk_size:
                if len(article_content) <= self.max_article_length:
                    # Single chunk for this article
                    formatted_chunk = self._format_legal_chunk(
                        article_content, article_num, article_title, metadata
                    )
                    chunks.append(formatted_chunk)
                else:
                    # Split long article by paragraphs (Khoản)
                    sub_chunks = self._split_long_article(
                        article_content, article_num, article_title, metadata
                    )
                    chunks.extend(sub_chunks)
        
        return chunks
    
    def _format_legal_chunk(self, content: str, article_num: str, article_title: str, metadata: Dict[str, Any]) -> str:
        """SỬA LOGIC: Format chunk với legal header chuẩn"""
        # Create proper legal reference header
        doc_name = metadata.get('file_name', 'Văn bản pháp luật')
        legal_level = metadata.get('legal_level', 'unknown')
        
        # Build header with full reference
        header_parts = []
        
        # Document reference
        if legal_level != 'unknown':
            header_parts.append(f"[{doc_name} - {legal_level.upper()}]")
        else:
            header_parts.append(f"[{doc_name}]")
        
        # Article reference
        if article_title:
            header_parts.append(f"Điều {article_num}. {article_title}")
        else:
            header_parts.append(f"Điều {article_num}")
        
        # Combine header + content
        header = '\n'.join(header_parts)
        
        return f"{header}\n\n{content}"
    
    def _split_long_article(self, article_content: str, article_num: str, article_title: str, metadata: Dict[str, Any]) -> List[str]:
        """SỬA LOGIC: Split long article by paragraphs"""
        chunks = []
        
        # Find paragraphs (Khoản) within this article
        paragraph_matches = list(re.finditer(self.legal_patterns['paragraph'], article_content, re.IGNORECASE))
        
        if len(paragraph_matches) >= 2:
            # Split by paragraphs
            for i, match in enumerate(paragraph_matches):
                start_pos = match.start()
                
                if i + 1 < len(paragraph_matches):
                    end_pos = paragraph_matches[i + 1].start()
                else:
                    end_pos = len(article_content)
                
                paragraph_content = article_content[start_pos:end_pos].strip()
                paragraph_num = match.group(1)
                
                if len(paragraph_content) >= self.min_chunk_size:
                    # Format with full reference: Điều X, Khoản Y
                    formatted_chunk = self._format_legal_chunk_with_paragraph(
                        paragraph_content, article_num, article_title, paragraph_num, metadata
                    )
                    chunks.append(formatted_chunk)
        else:
            # Split by simple overlap if no clear paragraphs
            simple_chunks = self._simple_chunk(article_content)
            for i, chunk in enumerate(simple_chunks):
                formatted_chunk = self._format_legal_chunk(
                    chunk, f"{article_num}.{i+1}", article_title, metadata
                )
                chunks.append(formatted_chunk)
        
        return chunks
    
    def _format_legal_chunk_with_paragraph(self, content: str, article_num: str, article_title: str, paragraph_num: str, metadata: Dict[str, Any]) -> str:
        """Format chunk với paragraph reference"""
        doc_name = metadata.get('file_name', 'Văn bản pháp luật')
        legal_level = metadata.get('legal_level', 'unknown')
        
        # Build full legal reference
        header_parts = []
        
        if legal_level != 'unknown':
            header_parts.append(f"[{doc_name} - {legal_level.upper()}]")
        else:
            header_parts.append(f"[{doc_name}]")
        
        # Full reference: Điều X, Khoản Y
        if article_title:
            header_parts.append(f"Điều {article_num}. {article_title}")
            header_parts.append(f"Khoản {paragraph_num}")
        else:
            header_parts.append(f"Điều {article_num}, Khoản {paragraph_num}")
        
        header = '\n'.join(header_parts)
        return f"{header}\n\n{content}"
    
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
        for match in re.finditer(self.legal_patterns['article'], content, re.IGNORECASE):
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
        """Process single file với enhanced metadata"""
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
        
        # SỬA LOGIC: Chunk with enhanced legal structure
        chunks = self.chunk_content(content, doc_metadata)
        
        if not chunks:
            logger.warning(f"No valid chunks: {file_name}")
            return []
        
        # Create documents with enhanced metadata
        documents = []
        for i, chunk in enumerate(chunks):
            # SỬA LOGIC: Enhanced metadata với legal structure info
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
                'chunk_size': len(chunk),
                
                # SỬA LOGIC: Thêm legal reference info
                'legal_reference': self._extract_chunk_legal_reference(chunk),
                'contains_articles': self._count_articles_in_chunk(chunk),
                'contains_paragraphs': self._count_paragraphs_in_chunk(chunk)
            }
            
            documents.append(Document(content=chunk, metadata=metadata))
        
        logger.info(f"✅ Created {len(documents)} chunks from {file_name}")
        return documents
    
    def _extract_chunk_legal_reference(self, chunk: str) -> str:
        """SỬA LOGIC: Extract legal reference from chunk"""
        # Look for legal reference in header
        lines = chunk.split('\n')
        
        # Check first few lines for legal reference
        for i, line in enumerate(lines[:5]):
            line = line.strip()
            
            # Check for Điều reference
            article_match = re.search(r'Điều\s+(\d+[a-z]?)', line, re.IGNORECASE)
            if article_match:
                article_num = article_match.group(1)
                
                # Check for Khoản reference in same or next line
                paragraph_match = re.search(r'Khoản\s+(\d+)', line, re.IGNORECASE)
                if paragraph_match:
                    return f"Điều {article_num}, Khoản {paragraph_match.group(1)}"
                
                # Check next line for Khoản
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    paragraph_match = re.search(r'Khoản\s+(\d+)', next_line, re.IGNORECASE)
                    if paragraph_match:
                        return f"Điều {article_num}, Khoản {paragraph_match.group(1)}"
                
                return f"Điều {article_num}"
        
        return "General"
    
    def _count_articles_in_chunk(self, chunk: str) -> int:
        """Count articles in chunk"""
        return len(re.findall(self.legal_patterns['article'], chunk, re.IGNORECASE))
    
    def _count_paragraphs_in_chunk(self, chunk: str) -> int:
        """Count paragraphs in chunk"""
        return len(re.findall(self.legal_patterns['paragraph'], chunk, re.IGNORECASE))
    
    def process_directory(self, directory_path: str = None) -> List[Document]:
        """Process directory với enhanced stats"""
        if directory_path is None:
            directory_path = config.documents_path
        
        if not os.path.exists(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return []
        
        logger.info(f"📁 Processing documents from: {directory_path}")
        
        all_documents = []
        stats = {
            'processed': 0, 
            'failed': 0, 
            'total_chunks': 0,
            'legal_chunks': 0,
            'articles_found': 0
        }
        
        for file_path in Path(directory_path).rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                try:
                    docs = self.process_file(str(file_path))
                    if docs:
                        all_documents.extend(docs)
                        stats['processed'] += 1
                        stats['total_chunks'] += len(docs)
                        
                        # Count legal structure chunks
                        legal_chunks = sum(1 for d in docs if d.metadata.get('has_legal_structure', False))
                        articles_found = sum(d.metadata.get('contains_articles', 0) for d in docs)
                        
                        stats['legal_chunks'] += legal_chunks
                        stats['articles_found'] += articles_found
                    else:
                        stats['failed'] += 1
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    stats['failed'] += 1
        
        logger.info(f"✅ Processing complete:")
        logger.info(f"   📄 Files: {stats['processed']} processed, {stats['failed']} failed")
        logger.info(f"   📝 Total chunks: {stats['total_chunks']}")
        logger.info(f"   ⚖️ Legal chunks: {stats['legal_chunks']}")
        logger.info(f"   📜 Articles found: {stats['articles_found']}")
        
        return all_documents