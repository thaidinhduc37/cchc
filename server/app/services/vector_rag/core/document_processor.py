# app/server/services/vector_rag/core/document_processor.py
"""
Document Processor for Legal RAG Chatbot - TXT VERSION
Optimized for pre-processed .txt legal documents (e.g., 47-2019-QH14.txt) where each semantic unit (Điều, Khoản, Điểm) is one line.
Handles varying article lengths by improving chunking logic.
"""
import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from app.services.vector_rag.rag_config import config

@dataclass
class Document:
    """Document data structure"""
    content: str
    metadata: Dict[str, Any]

class DocumentProcessor:
    """Document Processor for Legal RAG Chatbot - TXT Version"""
    
    def __init__(self):
        self.documents_path = config.documents_path
        # Legal document patterns
        self.legal_patterns = {
            'law_number': re.compile(r'(?:Luật\s+số\s*:?\s*)?(\d+/\d{4}/QH\d+)', re.IGNORECASE),
            'decree_number': re.compile(r'(?:Nghị\s+định\s+số\s*:?\s*)?(\d+/\d{4}/NĐ-CP)', re.IGNORECASE),
            'circular_number': re.compile(r'(?:Thông\s+tư\s+số\s*:?\s*)?(\d+/\d{4}/TT-[\w]+)', re.IGNORECASE),
            'doc_title': re.compile(r'(?:LUẬT|NGHỊ ĐỊNH|THÔNG TƯ)\s+(.+?)(?:\n|$)', re.IGNORECASE),
            'article_line': re.compile(r'^\s*Điều\s+(\d+[a-z]?)\s*[.:]?\s*(.*?)$', re.IGNORECASE),
            'paragraph_line': re.compile(r'^\s*(\d+)\.\s+(.*?)$'),
            'point_line': re.compile(r'^\s*([a-z]|đ)\)\s+(.*?)$', re.IGNORECASE),
            'chapter_line': re.compile(r'^\s*Chương\s+([IVX]+|\d+)\s*(.*)$', re.IGNORECASE),
            'section_line': re.compile(r'^\s*Mục\s+(\d+)\s*[.:]?\s*(.*?)$', re.IGNORECASE)
        }
        
        self.qa_patterns = {
            'qa_pair': re.compile(r'(?:>\s*)?\*\*Hỏi:\s*(.*?)\*\*\s*(?:>\s*)?\*\*Đáp:\*\*(.*?)(?=(?:>\s*)?\*\*Hỏi:|\Z)', re.DOTALL | re.IGNORECASE),
            'simple_qa': re.compile(r'(?:>\s*)?(?:CÂU\s+)?Hỏi:\s*(.*?)(?:>\s*)?(?:TRẢ\s+LỜI|Đáp):\s*(.*?)(?=(?:>\s*)?(?:CÂU\s+)?Hỏi:|\Z)', re.DOTALL | re.IGNORECASE),
            'question_line': re.compile(r'^\s*(?:CÂU\s+)?HỎI:\s*(.*?)$', re.IGNORECASE),
            'answer_line': re.compile(r'^\s*(?:TRẢ\s+LỜI|ĐÁP):\s*(.*?)$', re.IGNORECASE)
        }
    
    def process_file(self, file_path: str) -> List[Document]:
        """Process a .txt file with enhanced classification"""
        if not file_path.endswith('.txt'):
            return []
        
        if not os.path.exists(file_path):
            return []
        
        try:
            # Extract content from TXT
            content = self._extract_txt_content(file_path)
            if not content or len(content) < 100:
                print(f"⚠️ {file_path} is too short or empty.")
                return []
            
            # Classify document with filename context
            doc_type = self._classify_document(content, file_path)
            
            if doc_type == 'legal':
                return self._process_legal_document(content, file_path)
            elif doc_type == 'qa':
                return self._process_qa_document(content, file_path)
            else:
                # Fallback processing
                print(f"⚠️ {file_path} using fallback line-by-line processing")
                return self._process_fallback_document(content, file_path)
                
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []
    
    def process_directory(self, documents_path: str) -> List[Document]:
        """Process all .txt files with statistics"""
        if documents_path is None:
            documents_path = self.documents_path
            
        all_documents = []
        processed_files = 0
        failed_files = 0
        
        if not os.path.exists(documents_path):
            print(f"❌ Documents path not found: {documents_path}")
            return []
        
        # Find all .txt files
        txt_files = list(Path(documents_path).rglob('*.txt'))
        print(f"📁 Found {len(txt_files)} .txt files")
        
        for file_path in txt_files:
            documents = self.process_file(str(file_path))
            if documents:
                all_documents.extend(documents)
                processed_files += 1
                print(f"✅ {os.path.basename(file_path)}: {len(documents)} chunks")
            else:
                failed_files += 1
                print(f"❌ {os.path.basename(file_path)}: no chunks extracted")
        
        print(f"📊 Processing summary: {processed_files} successful, {failed_files} failed")
        return all_documents
    
    def _extract_txt_content(self, file_path: str) -> str:
        """Extract content from TXT with encoding handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                return content
            except:
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
                    return content
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    return ""
    
    def _classify_document(self, content: str, file_path: str = "") -> str:
        """Enhanced document classification with better Q&A detection"""
        lines = content.split('\n')
        
        # Count legal structure lines
        article_lines = sum(1 for line in lines if self.legal_patterns['article_line'].match(line.strip()))
        paragraph_lines = sum(1 for line in lines if self.legal_patterns['paragraph_line'].match(line.strip()))
        point_lines = sum(1 for line in lines if self.legal_patterns['point_line'].match(line.strip()))
        
        # Enhanced Q&A detection
        question_lines = sum(1 for line in lines if self.qa_patterns['question_line'].match(line.strip()))
        answer_lines = sum(1 for line in lines if self.qa_patterns['answer_line'].match(line.strip()))
        
        # Additional Q&A indicators
        qa_indicators = 0
        qa_keywords = ['hỏi đáp', 'câu hỏi', 'thắc mắc', 'tư vấn', 'giải đáp']
        for line in lines[:10]:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in qa_keywords):
                qa_indicators += 1
        
        # Check for balanced Q&A pairs
        qa_balance_score = 0
        if question_lines > 0 and answer_lines > 0:
            qa_balance_score = min(question_lines, answer_lines) * 2
        
        # Filename indicators
        filename_qa_score = 0
        if file_path:
            filename_lower = file_path.lower()
            if any(keyword in filename_lower for keyword in ['hoi_dap', 'qa', 'questions', 'answers', 'tru_van']):
                filename_qa_score = 5
        
        # Calculate legal score
        legal_score = article_lines * 3 + paragraph_lines * 2 + point_lines * 1
        
        # Enhanced Q&A scoring
        qa_score = qa_balance_score + qa_indicators * 2 + filename_qa_score
        
        # Legal keywords
        legal_keywords = ['luật', 'nghị định', 'thông tư', 'quy định', 'điều kiện', 'thủ tục', 'trách nhiệm']
        legal_keyword_score = sum(1 for line in lines[:10] for keyword in legal_keywords if keyword in line.lower())
        legal_score += legal_keyword_score
        
        print(f"DEBUG: Legal score: {legal_score} (Điều: {article_lines}, Khoản: {paragraph_lines}, Điểm: {point_lines}, Keywords: {legal_keyword_score})")
        print(f"DEBUG: Q&A score: {qa_score} (Hỏi: {question_lines}, Đáp: {answer_lines}, Balance: {qa_balance_score}, Indicators: {qa_indicators}, Filename: {filename_qa_score})")
        
        # Improved classification logic
        if qa_score >= 10 and question_lines >= 2 and answer_lines >= 2:
            return 'qa'
        elif qa_score >= 6 and (question_lines > 0 or answer_lines > 0):
            return 'qa'
        elif legal_score >= 8 or (article_lines >= 2 and legal_keyword_score >= 2):
            return 'legal'
        elif legal_score >= 3 or article_lines >= 1:
            return 'legal'
        else:
            return 'unknown'
    
    def _process_legal_document(self, content: str, file_path: str) -> List[Document]:
        """Process legal document line-by-line with improved chunking for varying article lengths"""
        documents = []
        file_name = os.path.basename(file_path)
        lines = content.split('\n')
        
        # Extract document metadata
        doc_info = self._extract_legal_metadata(content, file_name)
        
        chunk_id = 0
        current_chapter = ""
        current_section = ""
        current_article = ""
        current_article_title = ""
        article_buffer = []  # Buffer to collect multi-line article content
        
        # Process line by line
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 10:
                continue
            
            # Check line type
            chapter_match = self.legal_patterns['chapter_line'].match(line)
            section_match = self.legal_patterns['section_line'].match(line)
            article_match = self.legal_patterns['article_line'].match(line)
            paragraph_match = self.legal_patterns['paragraph_line'].match(line)
            point_match = self.legal_patterns['point_line'].match(line)
            
            if chapter_match:
                # Flush previous article buffer if exists
                if article_buffer:
                    documents.extend(self._flush_article_buffer(doc_info, file_name, current_chapter, current_section, current_article, current_article_title, article_buffer, chunk_id))
                    chunk_id += len(article_buffer)
                    article_buffer = []
                
                current_chapter = f"Chương {chapter_match.group(1)}"
                current_section = ""
                current_article = ""
                
                chapter_title = chapter_match.group(2).strip() if chapter_match.group(2) else ""
                if chapter_title:
                    chunk_content = self._format_legal_chunk(
                        doc_info, current_chapter, "", "", 
                        chapter_title, f"{current_chapter} {chapter_title}", 'chapter'
                    )
                    
                    chunk_metadata = self._create_legal_metadata(
                        doc_info, file_name, current_chapter, chunk_id,
                        current_chapter, "", 'chapter'
                    )
                    
                    documents.append(Document(chunk_content, chunk_metadata))
                    chunk_id += 1
                
                continue
                
            elif section_match:
                # Flush previous article buffer if exists
                if article_buffer:
                    documents.extend(self._flush_article_buffer(doc_info, file_name, current_chapter, current_section, current_article, current_article_title, article_buffer, chunk_id))
                    chunk_id += len(article_buffer)
                    article_buffer = []
                
                current_section = f"Mục {section_match.group(1)}"
                current_article = ""
                
                section_title = section_match.group(2).strip() if section_match.group(2) else ""
                if section_title:
                    chunk_content = self._format_legal_chunk(
                        doc_info, current_chapter, current_section, "", 
                        section_title, f"{current_section} {section_title}", 'section'
                    )
                    
                    chunk_metadata = self._create_legal_metadata(
                        doc_info, file_name, current_section, chunk_id,
                        current_chapter, current_section, 'section'
                    )
                    
                    documents.append(Document(chunk_content, chunk_metadata))
                    chunk_id += 1
                
                continue
                
            elif article_match:
                # Flush previous article buffer if exists
                if article_buffer:
                    documents.extend(self._flush_article_buffer(doc_info, file_name, current_chapter, current_section, current_article, current_article_title, article_buffer, chunk_id))
                    chunk_id += len(article_buffer)
                
                current_article = f"Điều {article_match.group(1)}"
                current_article_title = article_match.group(2).strip()
                article_buffer = [line]  # Start new article buffer
                
            elif paragraph_match or point_match:
                # Add to article buffer
                article_buffer.append(line)
                
            else:
                # General content line
                if len(line) > 10:
                    article_buffer.append(line)
        
        # Flush final article buffer
        if article_buffer:
            documents.extend(self._flush_article_buffer(doc_info, file_name, current_chapter, current_section, current_article, current_article_title, article_buffer, chunk_id))
            chunk_id += len(article_buffer)
        
        # Update total chunks
        for doc in documents:
            doc.metadata['total_chunks'] = len(documents)
        
        print(f"📦 Extracted {len(documents)} chunks from legal document")
        return documents
    

    def _flush_article_buffer(self, doc_info: Dict, file_name: str, chapter: str, section: str, 
                            article: str, article_title: str, buffer: List[str], chunk_id: int) -> List[Document]:
        """Flush article buffer and create chunks - FIXED: Thêm main article summary"""
        documents = []
        
        if not buffer:
            return documents

        
        if article and len(buffer) > 1:  # Có article và nhiều content
            # Aggregate all content từ buffer
            all_content_parts = []
            article_number = ""
            
            for line in buffer:
                line = line.strip()
                if not line:
                    continue
                    
                # Extract article number từ first line
                if not article_number:
                    article_match = self.legal_patterns['article_line'].match(line)
                    if article_match:
                        article_number = article_match.group(1)  # "15", "19", "36"
                
                all_content_parts.append(line)
            
            if article_number and all_content_parts:
                # Tạo main article summary
                summary_content = "\n".join(all_content_parts)
                
                # Format as main article chunk
                chunk_content = self._format_legal_chunk(
                    doc_info, chapter, section, f"Điều {article_number}", 
                    article_title, summary_content, 'main_article'
                )
                
                
                chunk_metadata = self._create_legal_metadata(
                    doc_info, file_name, article_number,  # ← CHÍNH XÁC: "15", "19", không có "Điều"
                    chunk_id, chapter, section, 'main_article'
                )
                chunk_metadata['confidence_boost'] = 2.0  # Boost main articles
                chunk_metadata['is_main_article'] = True
                chunk_metadata['sub_clauses_count'] = len([l for l in buffer if 
                    self.legal_patterns['paragraph_line'].match(l) or 
                    self.legal_patterns['point_line'].match(l)])
                
                documents.append(Document(chunk_content, chunk_metadata))

        for i, line in enumerate(buffer):
            line = line.strip()
            if not line:
                continue

            article_match = self.legal_patterns['article_line'].match(line)
            paragraph_match = self.legal_patterns['paragraph_line'].match(line)
            point_match = self.legal_patterns['point_line'].match(line)
            
            content_type = 'content'
            law_unit = article or "Nội dung"
            sub_unit = ""
            content = line
            confidence_boost = 1.0
            
            if article_match:
                # Skip tạo chunk cho article line nếu đã có main article
                continue
            elif paragraph_match:
                content_type = 'paragraph'
                sub_unit = f"Khoản {paragraph_match.group(1)}"
                content = paragraph_match.group(2).strip()
                # FIX: law_unit format consistent
                article_num = article.replace("Điều ", "") if article else "K"
                law_unit = f"{article_num}.{paragraph_match.group(1)}"  # "15.2" 
                confidence_boost = 1.3
            elif point_match:
                content_type = 'point'
                sub_unit = f"Điểm {point_match.group(1)})"
                content = point_match.group(2).strip()
                article_num = article.replace("Điều ", "") if article else "D"
                law_unit = f"{article_num}.{point_match.group(1)}"  # "15.a"
                confidence_boost = 1.2
            else:
                # General content
                if len(line) < 30:
                    content_type = 'short_content'
                    confidence_boost = 1.1
            
            # Tạo sub-clause chunks
            chunk_content = self._format_legal_chunk(
                doc_info, chapter, section, article or "Nội dung", sub_unit, content, content_type
            )
            
            chunk_metadata = self._create_legal_metadata(
                doc_info, file_name, law_unit, chunk_id + len(documents), chapter, section, content_type
            )
            chunk_metadata['confidence_boost'] = confidence_boost
            chunk_metadata['line_length'] = len(line)
            
            documents.append(Document(chunk_content, chunk_metadata))
        
        return documents
    
    def _process_qa_document(self, content: str, file_path: str) -> List[Document]:
        """Process Q&A document with advanced parsing"""
        documents = []
        file_name = os.path.basename(file_path)
        lines = content.split('\n')
        
        # Parse Q&A pairs
        qa_pairs = self._parse_qa_pairs(lines)
        
        if qa_pairs:
            for i, qa_pair in enumerate(qa_pairs):
                question = qa_pair['question']
                answer_lines = qa_pair['answer_lines']
                
                answer = '\n'.join(answer_lines)
                
                if len(question) < 10 or len(answer) < 30:
                    continue
                
                qa_content = self._format_qa_content(question, answer, qa_pair.get('legal_refs', []))
                
                qa_metadata = {
                    'content_type': 'qa_entry',
                    'source': file_name,
                    'qa_index': i + 1,
                    'question_length': len(question),
                    'answer_length': len(answer),
                    'answer_lines_count': len(answer_lines),
                    'has_legal_references': len(qa_pair.get('legal_refs', [])) > 0,
                    'has_structured_content': self._has_structured_content(answer_lines),
                    'topic_category': self._classify_qa_topic(question),
                    'processed_at': datetime.now().isoformat()
                }
                
                documents.append(Document(qa_content, qa_metadata))
        
        # Extract additional content
        additional_docs = self._extract_additional_qa_content(lines, file_name)
        documents.extend(additional_docs)
        
        print(f"📋 Q&A processing: {len(documents)} chunks extracted ({len(qa_pairs)} Q&A pairs + {len(additional_docs)} additional content)")
        return documents
    
    def _parse_qa_pairs(self, lines: List[str]) -> List[Dict]:
        """Parse Q&A pairs with multiline support"""
        qa_pairs = []
        current_qa = None
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            
            if line.startswith('Hỏi:'):
                if current_qa:
                    qa_pairs.append(current_qa)
                
                current_qa = {
                    'question': line[4:].strip(),
                    'answer_lines': [],
                    'legal_refs': [],
                    'start_line': line_num
                }
                
            elif line.startswith('Đáp:'):
                if current_qa:
                    answer_start = line[4:].strip()
                    if answer_start:
                        current_qa['answer_lines'].append(answer_start)
                        
            elif current_qa and line:
                if any(ref in line for ref in ['Căn cứ:', 'Điều ', 'Luật ', 'Thông tư ', 'Nghị định ']):
                    current_qa['legal_refs'].append(line)
                    current_qa['answer_lines'].append(line)
                else:
                    current_qa['answer_lines'].append(line)
        
        if current_qa:
            qa_pairs.append(current_qa)
        
        return qa_pairs
    
    def _format_qa_content(self, question: str, answer: str, legal_refs: List[str]) -> str:
        """Format Q&A content"""
        formatted = f"CÂU HỎI: {question}\n\nTRẢ LỜI:\n{answer}"
        
        if legal_refs:
            formatted += f"\n\nCĂN CỨ PHÁP LÝ:\n" + "\n".join(legal_refs)
        
        return formatted
    
    def _has_structured_content(self, answer_lines: List[str]) -> bool:
        """Check if answer has structured content"""
        structured_indicators = ['•', '1.', '2.', '3.', '- ', '+ ', 'Bước ', 'Hồ sơ:', 'Quy trình:']
        return any(any(indicator in line for indicator in structured_indicators) for line in answer_lines)
    
    def _classify_qa_topic(self, question: str) -> str:
        """Classify Q&A topic"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['hộ chiếu', 'passport']):
            return 'passport'
        elif any(word in question_lower for word in ['visa', 'thị thực']):
            return 'visa'
        elif any(word in question_lower for word in ['xuất cảnh', 'nhập cảnh']):
            return 'entry_exit'
        elif any(word in question_lower for word in ['lệ phí', 'thời gian', 'hồ sơ']):
            return 'procedures'
        elif any(word in question_lower for word in ['trẻ em', 'dưới 14', 'under 14']):
            return 'children'
        elif any(word in question_lower for word in ['mất', 'hỏng', 'lost']):
            return 'lost_damaged'
        elif any(word in question_lower for word in ['nước ngoài', 'abroad']):
            return 'overseas'
        else:
            return 'general'
    
    def _extract_additional_qa_content(self, lines: List[str], file_name: str) -> List[Document]:
        """Extract additional Q&A content"""
        additional_docs = []
        
        title_lines = []
        for line in lines[:5]:
            line = line.strip()
            if line and not line.startswith(('Hỏi:', 'Đáp:')):
                if len(line) > 10 and len(line) < 100:
                    title_lines.append(line)
        
        if title_lines:
            title_content = '\n'.join(title_lines)
            title_metadata = {
                'content_type': 'qa_document_header',
                'source': file_name,
                'is_title': True,
                'processed_at': datetime.now().isoformat()
            }
            additional_docs.append(Document(title_content, title_metadata))
        
        standalone_content = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('Hỏi:', 'Đáp:')):
                if any(keyword in line for keyword in ['Lưu ý:', 'Chú ý:', 'Quan trọng:', 'Cập nhật:']):
                    standalone_content.append(line)
        
        if standalone_content:
            notes_content = '\n'.join(standalone_content)
            notes_metadata = {
                'content_type': 'qa_important_notes',
                'source': file_name,
                'note_count': len(standalone_content),
                'processed_at': datetime.now().isoformat()
            }
            additional_docs.append(Document(notes_content, notes_metadata))
        
        return additional_docs
    
    def _process_fallback_document(self, content: str, file_path: str) -> List[Document]:
        """Fallback processing line-by-line"""
        documents = []
        file_name = os.path.basename(file_path)
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            content_type = 'generic_content'
            confidence_boost = 1.0
            
            if re.search(r'(?:Điều|Khoản|Điểm|Chương|Mục)', line, re.IGNORECASE):
                content_type = 'generic_legal'
                confidence_boost = 1.3
            elif re.search(r'[?？]|(?:hỏi|câu hỏi|trả lời|đáp)', line, re.IGNORECASE):
                content_type = 'generic_qa'
                confidence_boost = 1.2
            elif re.search(r'(?:quy định|thủ tục|điều kiện|pháp luật)', line, re.IGNORECASE):
                content_type = 'generic_legal'
                confidence_boost = 1.2
            elif len(line) < 30:
                content_type = 'generic_short'
                confidence_boost = 1.1
            
            metadata = {
                'content_type': content_type,
                'source': file_name,
                'line_number': line_num + 1,
                'line_length': len(line),
                'confidence_boost': confidence_boost,
                'processing_note': 'Line-by-line fallback processing',
                'processed_at': datetime.now().isoformat()
            }
            
            documents.append(Document(line, metadata))
        
        print(f"📄 Fallback processing: {len(documents)} lines extracted")
        return documents
    
    def _extract_legal_metadata(self, content: str, file_name: str) -> Dict[str, Any]:
        """Extract legal document metadata"""
        doc_info = {
            'doc_id': '',
            'doc_type': 'legal_document',
            'name': '',
            'doc_category': 'law'
        }
        
        lines = content.split('\n')[:20]
        content_head = '\n'.join(lines)
        
        law_match = self.legal_patterns['law_number'].search(content_head)
        decree_match = self.legal_patterns['decree_number'].search(content_head)
        circular_match = self.legal_patterns['circular_number'].search(content_head)
        
        if law_match:
            doc_info['doc_id'] = law_match.group(1)
            doc_info['doc_category'] = 'law'
        elif decree_match:
            doc_info['doc_id'] = decree_match.group(1)
            doc_info['doc_category'] = 'decree'
        elif circular_match:
            doc_info['doc_id'] = circular_match.group(1)
            doc_info['doc_category'] = 'circular'
        else:
            doc_info['doc_id'] = file_name.replace('.txt', '')
        
        title_match = self.legal_patterns['doc_title'].search(content_head)
        if title_match:
            doc_info['name'] = title_match.group(1).strip()
        else:
            title_lines = [line.strip() for line in lines[:10] if line.strip()]
            for line in title_lines:
                if any(skip in line.lower() for skip in ['quốc hội', 'cộng hòa', 'độc lập', 'luật số', 'hà nội']):
                    continue
                if len(line) > 20 and len(line) < 100 and not line.startswith(('Điều', 'Chương', 'Mục')):
                    doc_info['name'] = line
                    break
            
            if not doc_info['name']:
                doc_info['name'] = file_name.replace('.txt', '').replace('_', ' ').replace('-', ' ')
        
        return doc_info
    
    def _format_legal_chunk(self, doc_info: Dict, chapter: str, section: str, 
                           article: str, sub_unit: str, content: str, chunk_type: str) -> str:
        """Format legal chunk content"""
        header_parts = [f"[{doc_info['doc_id']} - {doc_info['name']}]"]
        
        if chapter:
            header_parts.append(chapter)
        if section:
            header_parts.append(section)
        if article:
            header_parts.append(article)
        if sub_unit:
            header_parts.append(sub_unit)
        
        header = " ".join(header_parts)
        
        return f"{header}\n\n{content}"
    
    def _create_legal_metadata(self, doc_info: Dict, file_name: str, law_unit: str,
                              chunk_id: int, chapter: str, section: str, chunk_type: str) -> Dict[str, Any]:
        """Create metadata for legal chunk"""
        return {
            'content_type': 'legal_document',
            'doc_type': doc_info['doc_category'],
            'doc_id': doc_info['doc_id'],
            'name': doc_info['name'],
            'law_unit': law_unit,
            'chapter': chapter,
            'section': section,
            'chunk_type': chunk_type,
            'source': file_name,
            'chunk_id': chunk_id,
            'total_chunks': 0,
            'processed_at': datetime.now().isoformat()
        }
    
    def verify_content_preservation(self, original_files: List[str], processed_docs: List[Document]) -> Dict[str, Any]:
        """Verify content preservation ratio"""
        original_total_chars = 0
        original_file_sizes = {}
        
        for file_path in original_files:
            try:
                content = self._extract_txt_content(file_path)
                file_size = len(content)
                original_total_chars += file_size
                original_file_sizes[os.path.basename(file_path)] = file_size
            except:
                continue
        
        core_processed_chars = 0
        header_chars = 0
        
        for doc in processed_docs:
            content = doc.content
            
            if content.startswith('[') and ']\n\n' in content:
                header_end = content.find(']\n\n') + 3
                header_part = content[:header_end]
                core_part = content[header_end:]
                
                header_chars += len(header_part)
                core_processed_chars += len(core_part)
            else:
                core_processed_chars += len(content)
        
        total_processed_chars = core_processed_chars + header_chars
        
        core_preservation_ratio = core_processed_chars / max(original_total_chars, 1)
        total_expansion_ratio = total_processed_chars / max(original_total_chars, 1)
        
        type_counts = {}
        for doc in processed_docs:
            content_type = doc.metadata.get('content_type', 'unknown')
            type_counts[content_type] = type_counts.get(content_type, 0) + 1
        
        status = 'EXCELLENT' if core_preservation_ratio >= 0.95 else 'GOOD' if core_preservation_ratio >= 0.85 else 'ACCEPTABLE' if core_preservation_ratio >= 0.70 else 'POOR'
        
        verification = {
            'original_files': len(original_files),
            'original_total_chars': original_total_chars,
            'processed_chunks': len(processed_docs),
            'core_content_chars': core_processed_chars,
            'header_chars': header_chars,
            'total_processed_chars': total_processed_chars,
            'core_preservation_ratio': round(core_preservation_ratio, 3),
            'total_expansion_ratio': round(total_expansion_ratio, 3),
            'header_overhead_ratio': round(header_chars / max(total_processed_chars, 1), 3),
            'status': status,
            'type_distribution': type_counts,
            'file_sizes': original_file_sizes
        }
        
        print(f"✅ TXT CONTENT PRESERVATION: {core_preservation_ratio:.1%} core content preserved ({status})")
        return verification
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        return {
            'processor_version': '2.1_txt_optimized',
            'supported_formats': ['.txt'],
            'document_types': ['legal', 'qa', 'generic_legal', 'generic_qa', 'generic_content'],
            'processing_method': 'line_by_line_with_article_buffering',
            'optimized_for': 'Pre-processed legal documents with 1-line-per-semantic-unit structure, handling varying article lengths',
            'features': [
                'Line-by-line processing with article buffering',
                'Legal structure recognition (Điều/Khoản/Điểm/Chương/Mục)',
                'Q&A pair extraction from line format',
                'UTF-8 encoding with fallback support',
                'Metadata preservation and enhancement',
                'Content preservation tracking',
                'Improved handling of short and long articles'
            ]
        }

# Factory function
def create_processor() -> DocumentProcessor:
    """Create DocumentProcessor instance for TXT files"""
    return DocumentProcessor()