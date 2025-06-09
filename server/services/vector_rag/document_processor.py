# server/services/vector_rag/document_processor.py
"""
Document processor - SỬA LOGIC: Chunking theo cấu trúc Điều-Khoản-Điểm + Document Linking
"""
import os
import re
import json
from typing import List, Dict, Any, Optional, Set
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
    """Document processor với legal chunking + document linking"""
    
    def __init__(self):
        # SỬA LOGIC: Enhanced legal patterns cho chunking
        self.legal_patterns = {
            'chapter': r'(?:^|\n)\s*Chương\s+([IVX\d]+)\s*[.:]?\s*([^\n]*)',
            'article': r'(?:^|\n)\s*Điều\s+(\d+[a-z]?)\s*[.:]?\s*([^\n]*)',
            'paragraph': r'(?:^|\n)\s*(\d+)\.\s+([^\n]+)',
            'point': r'(?:^|\n)\s*([a-z]+)\)\s+([^\n]+)',
            'legal_doc': r'(Luật|Nghị định|Thông tư)\s+số\s+\d+[^\n]*'
        }
        
        # THÊM: Document reference patterns để detect links
        self.doc_reference_patterns = [
            # "Nghị định 76/2020/NĐ-CP" → "76-2020-NĐ-CP"
            r'nghị\s*định\s*(?:số\s*)?(\d+)\/(\d{4})\/nđ[-\/]cp',
            
            # "Thông tư 32/2020/TT-BCA" → "32-2020-TT-BCA"  
            r'thông\s*tư\s*(?:số\s*)?(\d+)\/(\d{4})\/tt[-\/](\w+)',
            
            # "Luật số 47/2019" → "47-2019-L"
            r'luật\s*(?:số\s*)?(\d+)\/(\d{4})',
            
            # "theo quy định tại điều X"
            r'theo\s+quy\s+định\s+tại\s+điều\s+(\d+[a-z]?)',
            
            # "bổ sung/sửa đổi" patterns
            r'(?:bổ\s+sung|sửa\s+đổi|thay\s+thế)',
        ]
        
        # Supported formats
        self.supported_formats = ['.pdf', '.txt', '.docx']
        
        # SỬA LOGIC: Chunking settings for legal structure
        self.chunk_size = config.chunk_size
        self.chunk_overlap = config.chunk_overlap
        self.min_chunk_size = 150
        self.max_article_length = 1200  # Max length for single article
        
        # THÊM: Document registry và links
        self.document_registry = {}  # {doc_id: metadata}
        self.document_links = {}     # {source_doc: [target_docs]}
        self.links_file = os.path.join(config.data_path, config.domain, "document_links.json")
        
        self._load_document_links()
        
        logger.info(f"🔧 DocumentProcessor với legal chunking + document linking")
    
    def _load_document_links(self):
        """Load document links từ file"""
        try:
            if os.path.exists(self.links_file):
                with open(self.links_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.document_registry = data.get('registry', {})
                    self.document_links = data.get('links', {})
                logger.info(f"📂 Loaded {len(self.document_registry)} docs, {len(self.document_links)} link sets")
        except Exception as e:
            logger.warning(f"Load links failed: {e}")
            self.document_registry = {}
            self.document_links = {}
    
    def _save_document_links(self):
        """Save document links to file"""
        try:
            os.makedirs(os.path.dirname(self.links_file), exist_ok=True)
            data = {
                'registry': self.document_registry,
                'links': self.document_links,
                'saved_at': datetime.now().isoformat()
            }
            with open(self.links_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Save links failed: {e}")
    
    def _extract_doc_id_from_filename(self, filename: str) -> Optional[str]:
        """Extract document ID từ filename"""
        # Remove extensions
        base_name = filename.replace('.pdf', '').replace('.txt', '').replace('.docx', '')
        
        # Check if follows standard format: "77-2020-NĐ-CP"
        if re.match(r'\d+-\d{4}-[A-ZĐ-]+', base_name):
            return base_name
        
        # Try to extract from filename patterns
        patterns = [
            r'(?:nghị.?định|nd).?(\d+).?(\d{4})',  # "Nghi-dinh-77-2020.pdf"
            r'(?:thông.?tư|tt).?(\d+).?(\d{4})',    # "Thong-tu-32-2020.pdf"
            r'(?:luật|luat).?(\d+).?(\d{4})',       # "Luat-47-2019.pdf"
        ]
        
        filename_lower = filename.lower()
        
        for pattern in patterns:
            match = re.search(pattern, filename_lower)
            if match:
                number, year = match.groups()
                
                if 'nghị' in filename_lower or 'nd' in filename_lower:
                    return f"{number}-{year}-NĐ-CP"
                elif 'thông' in filename_lower or 'tt' in filename_lower:
                    return f"{number}-{year}-TT"
                elif 'luật' in filename_lower or 'luat' in filename_lower:
                    return f"{number}-{year}-L"
        
        return None
    
    def _extract_title_from_content(self, content: str) -> str:
        """Extract title từ content"""
        lines = content.split('\n')[:10]  # First 10 lines
        
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:
                # Look for title patterns
                if any(keyword in line.lower() for keyword in ['nghị định', 'thông tư', 'luật số']):
                    return line
        
        # Fallback
        return "Văn bản pháp luật"
    
    def _extract_document_references(self, content: str) -> List[Dict[str, Any]]:
        """THÊM: Extract references đến documents khác"""
        references = []
        content_lower = content.lower()
        
        for pattern in self.doc_reference_patterns:
            matches = re.finditer(pattern, content_lower, re.IGNORECASE)
            
            for match in matches:
                # Determine reference type and target doc_id
                ref_info = self._parse_reference_match(match, pattern, content)
                if ref_info:
                    references.append(ref_info)
        
        return references
    
    def _parse_reference_match(self, match, pattern, content: str) -> Optional[Dict[str, Any]]:
        """Parse reference match thành structured info"""
        try:
            # Get surrounding context
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end].strip()
            
            # Determine target doc_id based on pattern
            groups = match.groups()
            
            if 'nghị.*định' in pattern:
                if len(groups) >= 2:
                    target_doc_id = f"{groups[0]}-{groups[1]}-NĐ-CP"
                    return {
                        'target_doc_id': target_doc_id,
                        'ref_type': 'implements',
                        'context': context,
                        'confidence': 0.9
                    }
            
            elif 'thông.*tư' in pattern:
                if len(groups) >= 3:
                    target_doc_id = f"{groups[0]}-{groups[1]}-TT-{groups[2].upper()}"
                    return {
                        'target_doc_id': target_doc_id,
                        'ref_type': 'implements', 
                        'context': context,
                        'confidence': 0.9
                    }
            
            elif 'luật' in pattern:
                if len(groups) >= 2:
                    target_doc_id = f"{groups[0]}-{groups[1]}-L"
                    return {
                        'target_doc_id': target_doc_id,
                        'ref_type': 'references',
                        'context': context,
                        'confidence': 0.8
                    }
            
            elif 'theo.*quy.*định' in pattern:
                # Article reference - need to find which document
                article_num = groups[0] if groups else None
                if article_num:
                    return {
                        'target_doc_id': 'unknown',  # Will be resolved later
                        'ref_type': 'article_reference',
                        'article_ref': f"Điều {article_num}",
                        'context': context,
                        'confidence': 0.7
                    }
            
            elif 'bổ.*sung' in pattern:
                return {
                    'target_doc_id': 'unknown',  # Need more context
                    'ref_type': 'amends',
                    'context': context,
                    'confidence': 0.6
                }
        
        except Exception as e:
            logger.debug(f"Parse reference error: {e}")
        
        return None
    
    def _register_document(self, doc_id: str, title: str, content: str, file_path: str, doc_type: str):
        """THÊM: Register document và extract links"""
        try:
            # Store document metadata
            self.document_registry[doc_id] = {
                'title': title,
                'doc_type': doc_type,
                'file_path': file_path,
                'content_length': len(content),
                'registered_at': datetime.now().isoformat()
            }
            
            # Extract references
            references = self._extract_document_references(content)
            
            if references:
                # Store links
                self.document_links[doc_id] = []
                
                for ref in references:
                    if ref['target_doc_id'] != 'unknown':
                        self.document_links[doc_id].append({
                            'target': ref['target_doc_id'],
                            'type': ref['ref_type'],
                            'article': ref.get('article_ref'),
                            'context': ref['context'][:100] + "..." if len(ref['context']) > 100 else ref['context']
                        })
                
                logger.info(f"🔗 Found {len(self.document_links[doc_id])} references in {doc_id}")
            
            # Save links
            self._save_document_links()
            
        except Exception as e:
            logger.warning(f"Document registration failed for {doc_id}: {e}")
    
    def get_document_links(self, doc_id: str) -> Dict[str, Any]:
        """THÊM: Get all links for a document"""
        result = {
            'outgoing': [],  # Documents mà doc_id tham chiếu đến
            'incoming': []   # Documents tham chiếu đến doc_id
        }
        
        # Outgoing links
        if doc_id in self.document_links:
            for link in self.document_links[doc_id]:
                target_id = link['target']
                link_info = {
                    'target_doc_id': target_id,
                    'target_exists': target_id in self.document_registry,
                    'ref_type': link['type'],
                    'article_ref': link.get('article'),
                    'context': link['context']
                }
                
                # Add target document info if exists
                if target_id in self.document_registry:
                    target_doc = self.document_registry[target_id]
                    link_info['target_title'] = target_doc['title']
                    link_info['target_type'] = target_doc['doc_type']
                
                result['outgoing'].append(link_info)
        
        # Incoming links (documents that reference this doc)
        for source_doc, links in self.document_links.items():
            if source_doc != doc_id:
                for link in links:
                    if link['target'] == doc_id:
                        if source_doc in self.document_registry:
                            source_info = {
                                'source_doc_id': source_doc,
                                'source_title': self.document_registry[source_doc]['title'],
                                'source_type': self.document_registry[source_doc]['doc_type'],
                                'ref_type': link['type'],
                                'article_ref': link.get('article'),
                                'context': link['context']
                            }
                            result['incoming'].append(source_info)
        
        return result
    
    def get_related_documents(self, doc_id: str, max_depth: int = 2) -> List[str]:
        """THÊM: Get related documents by following links"""
        related = set()
        to_visit = {doc_id}
        visited = set()
        
        for depth in range(max_depth):
            current_level = to_visit - visited
            if not current_level:
                break
            
            visited.update(current_level)
            next_level = set()
            
            for current_doc in current_level:
                if current_doc != doc_id:
                    related.add(current_doc)
                
                # Add outgoing links
                if current_doc in self.document_links:
                    for link in self.document_links[current_doc]:
                        target = link['target']
                        if target in self.document_registry:
                            next_level.add(target)
                
                # Add incoming links
                for source_doc, links in self.document_links.items():
                    for link in links:
                        if link['target'] == current_doc and source_doc in self.document_registry:
                            next_level.add(source_doc)
            
            to_visit = next_level
        
        return list(related)
    
    # Các method khác giữ nguyên từ code gốc...
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
        """Process single file với enhanced metadata + document linking"""
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
        
        # THÊM: Extract doc_id và register document
        doc_id = self._extract_doc_id_from_filename(file_name)
        title = self._extract_title_from_content(content)
        
        if doc_id:
            self._register_document(doc_id, title, content, file_path, doc_metadata['primary_type'])
        
        # SỬA LOGIC: Chunk with enhanced legal structure
        chunks = self.chunk_content(content, doc_metadata)
        
        if not chunks:
            logger.warning(f"No valid chunks: {file_name}")
            return []
        
        # Create documents with enhanced metadata
        documents = []
        for i, chunk in enumerate(chunks):
            # SỬA LOGIC: Enhanced metadata với legal structure info + document linking
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
                'contains_paragraphs': self._count_paragraphs_in_chunk(chunk),
                
                # THÊM: Document linking metadata
                'doc_id': doc_id,
                'document_title': title,
                'has_document_links': doc_id in self.document_links if doc_id else False,
                'linked_documents_count': len(self.document_links.get(doc_id, [])) if doc_id else 0
            }
            
            documents.append(Document(content=chunk, metadata=metadata))
        
        logger.info(f"✅ Created {len(documents)} chunks from {file_name}")
        if doc_id and doc_id in self.document_links:
            logger.info(f"🔗 Document has {len(self.document_links[doc_id])} references")
        
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
        """Process directory với enhanced stats + document linking"""
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
            'articles_found': 0,
            'documents_with_links': 0,
            'total_references': 0
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
                        
                        # Count document links
                        doc_id = docs[0].metadata.get('doc_id') if docs else None
                        if doc_id and doc_id in self.document_links:
                            stats['documents_with_links'] += 1
                            stats['total_references'] += len(self.document_links[doc_id])
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
        logger.info(f"   🔗 Documents with links: {stats['documents_with_links']}")
        logger.info(f"   📎 Total references: {stats['total_references']}")
        
        return all_documents
    
    def get_linking_stats(self) -> Dict[str, Any]:
        """THÊM: Get document linking statistics"""
        total_docs = len(self.document_registry)
        docs_with_links = len(self.document_links)
        total_refs = sum(len(links) for links in self.document_links.values())
        
        # Count by document type
        type_stats = {}
        for doc_id, doc_info in self.document_registry.items():
            doc_type = doc_info['doc_type']
            if doc_type not in type_stats:
                type_stats[doc_type] = {'count': 0, 'with_links': 0}
            type_stats[doc_type]['count'] += 1
            if doc_id in self.document_links:
                type_stats[doc_type]['with_links'] += 1
        
        return {
            'total_documents': total_docs,
            'documents_with_links': docs_with_links,
            'total_references': total_refs,
            'avg_refs_per_doc': total_refs / max(docs_with_links, 1),
            'link_coverage': docs_with_links / max(total_docs, 1),
            'type_breakdown': type_stats,
            'top_referenced': self._get_most_referenced_documents(5)
        }
    
    def _get_most_referenced_documents(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most referenced documents"""
        # Count incoming references
        ref_counts = {}
        for source_doc, links in self.document_links.items():
            for link in links:
                target = link['target']
                if target not in ref_counts:
                    ref_counts[target] = 0
                ref_counts[target] += 1
        
        # Sort and get top N
        sorted_refs = sorted(ref_counts.items(), key=lambda x: x[1], reverse=True)
        
        result = []
        for doc_id, count in sorted_refs[:limit]:
            doc_info = self.document_registry.get(doc_id, {})
            result.append({
                'doc_id': doc_id,
                'title': doc_info.get('title', 'Unknown'),
                'reference_count': count,
                'exists': doc_id in self.document_registry
            })
        
        return result
    
    def find_related_content_for_context(self, doc_id: str, max_results: int = 3) -> List[Dict[str, Any]]:
        """THÊM: Find related content for context building"""
        if doc_id not in self.document_registry:
            return []
        
        related_info = []
        
        # Get direct links
        links = self.get_document_links(doc_id)
        
        # Priority: outgoing links (documents this one references)
        for link in links['outgoing'][:max_results]:
            if link['target_exists']:
                related_info.append({
                    'doc_id': link['target_doc_id'],
                    'title': link['target_title'],
                    'relationship': f"references_{link['ref_type']}",
                    'article_ref': link.get('article_ref'),
                    'priority': 1
                })
        
        # Add incoming links if we have space
        remaining = max_results - len(related_info)
        if remaining > 0:
            for link in links['incoming'][:remaining]:
                related_info.append({
                    'doc_id': link['source_doc_id'],
                    'title': link['source_title'],
                    'relationship': f"referenced_by_{link['ref_type']}",
                    'article_ref': link.get('article_ref'),
                    'priority': 2
                })
        
        return related_info