import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Core libraries
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import ollama

# Document processing
import PyPDF2
from docx import Document
import re
from dataclasses import dataclass

# LangChain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document as LangchainDocument
from langchain.vectorstores.base import VectorStore
from langchain.embeddings.base import Embeddings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Lưu trữ thông tin chunk văn bản"""
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None

class VietnameseLegalTextSplitter:
    """Text splitter tối ưu cho văn bản pháp lý Việt Nam"""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Patterns cho văn bản pháp lý VN
        self.legal_patterns = [
            r"Điều \d+\.?",
            r"Khoản \d+\.?", 
            r"Điểm [a-z]+\)",
            r"Chương [IVX]+\.?",
            r"Mục \d+\.?",
            r"Phần [IVX]+\.?"
        ]
    
    def split_text(self, text: str, metadata: Dict = None) -> List[DocumentChunk]:
        """Chia văn bản thành các chunk phù hợp"""
        chunks = []
        
        # Tách theo cấu trúc pháp lý trước
        sections = self._split_by_legal_structure(text)
        
        for section in sections:
            if len(section) <= self.chunk_size:
                chunks.append(DocumentChunk(
                    content=section.strip(),
                    metadata=metadata or {}
                ))
            else:
                # Chia nhỏ hơn nếu section quá dài
                sub_chunks = self._split_long_section(section)
                for chunk in sub_chunks:
                    chunks.append(DocumentChunk(
                        content=chunk.strip(),
                        metadata=metadata or {}
                    ))
        
        return chunks
    
    def _split_by_legal_structure(self, text: str) -> List[str]:
        """Chia theo cấu trúc pháp lý"""
        sections = []
        current_section = ""
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Kiểm tra có phải đầu mục mới không
            is_new_section = any(re.match(pattern, line) for pattern in self.legal_patterns)
            
            if is_new_section and current_section:
                sections.append(current_section)
                current_section = line
            else:
                current_section += "\n" + line if current_section else line
        
        if current_section:
            sections.append(current_section)
            
        return sections
    
    def _split_long_section(self, text: str) -> List[str]:
        """Chia section dài thành các chunk nhỏ hơn"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", ", ", " "]
        )
        return splitter.split_text(text)

class FastEmbeddings:
    """Wrapper cho sentence-transformers tối ưu tốc độ"""
    
    def __init__(self, model_name: str = "keepitreal/vietnamese-sbert"):
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.model.max_seq_length = 512  # Giới hạn độ dài để tăng tốc
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embedding batch documents"""
        embeddings = self.model.encode(
            texts, 
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        """Embedding single query"""
        embedding = self.model.encode([text], convert_to_numpy=True)
        return embedding[0].tolist()

class FastFAISSVectorStore:
    """FAISS vector store tối ưu cho truy xuất nhanh"""
    
    def __init__(self, embeddings: FastEmbeddings, dimension: int = 768):
        self.embeddings = embeddings
        self.dimension = dimension
        
        # Sử dụng IndexFlatIP cho độ chính xác cao và tốc độ tốt
        self.index = faiss.IndexFlatIP(dimension)
        self.documents: List[DocumentChunk] = []
        
    def add_documents(self, documents: List[DocumentChunk]) -> None:
        """Thêm documents vào vector store"""
        logger.info(f"Adding {len(documents)} documents to vector store")
        
        # Batch embedding để tăng tốc
        texts = [doc.content for doc in documents]
        embeddings = self.embeddings.embed_documents(texts)
        
        # Chuẩn hóa embeddings cho cosine similarity
        embeddings_array = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(embeddings_array)
        
        # Thêm vào FAISS index
        self.index.add(embeddings_array)
        
        # Lưu documents với embeddings
        for doc, emb in zip(documents, embeddings_array):
            doc.embedding = emb
            self.documents.append(doc)
        
        logger.info(f"Vector store now contains {len(self.documents)} documents")
    
    def similarity_search(self, query: str, k: int = 5) -> List[DocumentChunk]:
        """Tìm kiếm tương tự nhanh"""
        if not self.documents:
            return []
        
        # Embed query
        query_embedding = np.array([self.embeddings.embed_query(query)], dtype=np.float32)
        faiss.normalize_L2(query_embedding)
        
        # Tìm kiếm với FAISS
        scores, indices = self.index.search(query_embedding, min(k, len(self.documents)))
        
        # Trả về documents theo thứ tự relevance
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:  # FAISS trả về -1 nếu không đủ results
                doc = self.documents[idx]
                results.append(doc)
        
        return results

class DocumentProcessor:
    """Xử lý các loại văn bản khác nhau"""
    
    @staticmethod
    def process_pdf(file_path: str) -> str:
        """Xử lý file PDF"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
        return text
    
    @staticmethod
    def process_docx(file_path: str) -> str:
        """Xử lý file DOCX"""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            logger.error(f"Error processing DOCX {file_path}: {e}")
        return text
    
    @staticmethod
    def process_txt(file_path: str) -> str:
        """Xử lý file TXT"""
        text = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()
        except Exception as e:
            logger.error(f"Error processing TXT {file_path}: {e}")
        return text

class GemmaLLM:
    """Wrapper cho Gemma 2B qua Ollama"""
    
    def __init__(self, model_name: str = "gemma:2b"):
        self.model_name = model_name
        self._ensure_model_available()
    
    def _ensure_model_available(self):
        """Đảm bảo model có sẵn"""
        try:
            # Kiểm tra model có sẵn không
            models = ollama.list()
            available_models = [model['name'] for model in models['models']]
            
            if self.model_name not in available_models:
                logger.info(f"Pulling model {self.model_name}...")
                ollama.pull(self.model_name)
                
        except Exception as e:
            logger.error(f"Error with Ollama model: {e}")
            raise
    
    def generate(self, prompt: str, max_tokens: int = 512) -> str:
        """Generate response từ Gemma"""
        try:
            response = ollama.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    'temperature': 0.1,
                    'top_p': 0.9,
                    'num_predict': max_tokens,
                }
            )
            return response['response']
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Xin lỗi, có lỗi xảy ra khi tạo phản hồi."

class LightweightRAGSystem:
    """Hệ thống RAG chính"""
    
    def __init__(self, 
                 embedding_model: str = "keepitreal/vietnamese-sbert",
                 llm_model: str = "gemma:2b"):
        
        logger.info("Initializing Lightweight RAG System...")
        
        # Khởi tạo components
        self.embeddings = FastEmbeddings(embedding_model)
        self.vector_store = FastFAISSVectorStore(self.embeddings)
        self.text_splitter = VietnameseLegalTextSplitter()
        self.document_processor = DocumentProcessor()
        self.llm = GemmaLLM(llm_model)
        
        # Thread pool cho xử lý song song
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("RAG System initialized successfully!")
    
    def load_documents(self, document_paths: List[str]) -> None:
        """Load và xử lý documents"""
        logger.info(f"Loading {len(document_paths)} documents...")
        
        all_chunks = []
        
        for path in document_paths:
            try:
                file_path = Path(path)
                if not file_path.exists():
                    logger.warning(f"File not found: {path}")
                    continue
                
                # Xử lý theo loại file
                if file_path.suffix.lower() == '.pdf':
                    text = self.document_processor.process_pdf(path)
                elif file_path.suffix.lower() in ['.docx', '.doc']:
                    text = self.document_processor.process_docx(path)
                elif file_path.suffix.lower() == '.txt':
                    text = self.document_processor.process_txt(path)
                else:
                    logger.warning(f"Unsupported file type: {path}")
                    continue
                
                if not text.strip():
                    logger.warning(f"No text extracted from: {path}")
                    continue
                
                # Chia thành chunks
                metadata = {
                    'source': str(file_path),
                    'filename': file_path.name,
                    'file_type': file_path.suffix
                }
                
                chunks = self.text_splitter.split_text(text, metadata)
                all_chunks.extend(chunks)
                
                logger.info(f"Processed {file_path.name}: {len(chunks)} chunks")
                
            except Exception as e:
                logger.error(f"Error processing {path}: {e}")
        
        # Thêm vào vector store
        if all_chunks:
            self.vector_store.add_documents(all_chunks)
            logger.info(f"Successfully loaded {len(all_chunks)} chunks total")
        else:
            logger.warning("No documents were successfully processed")
    
    def _create_context_prompt(self, query: str, relevant_docs: List[DocumentChunk]) -> str:
        """Tạo prompt với context"""
        context_parts = []
        
        for i, doc in enumerate(relevant_docs, 1):
            source = doc.metadata.get('filename', 'Unknown')
            context_parts.append(f"[Tài liệu {i} - {source}]\n{doc.content}")
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""Dựa trên các tài liệu pháp lý sau, hãy trả lời câu hỏi một cách chính xác và chi tiết:

NGỮ CẢNH:
{context}

CÂU HỎI: {query}

HƯỚNG DẪN:
- Trả lời dựa trên thông tin trong tài liệu được cung cấp
- Trích dẫn cụ thể điều, khoản, điểm liên quan
- Nếu không có thông tin đủ, hãy nói rõ
- Trả lời bằng tiếng Việt, rõ ràng và súc tích

TRẢ LỜI:"""

        return prompt
    
    def query(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """Truy vấn hệ thống RAG"""
        logger.info(f"Processing query: {question}")
        
        try:
            # Tìm kiếm documents liên quan
            relevant_docs = self.vector_store.similarity_search(question, k=top_k)
            
            if not relevant_docs:
                return {
                    'answer': "Xin lỗi, tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu.",
                    'sources': [],
                    'confidence': 0.0
                }
            
            # Tạo prompt với context
            prompt = self._create_context_prompt(question, relevant_docs)
            
            # Generate answer
            answer = self.llm.generate(prompt, max_tokens=800)
            
            # Chuẩn bị sources
            sources = []
            for doc in relevant_docs:
                sources.append({
                    'filename': doc.metadata.get('filename', 'Unknown'),
                    'content_preview': doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
                })
            
            return {
                'answer': answer,
                'sources': sources,
                'confidence': 1.0 if relevant_docs else 0.0,
                'num_sources': len(relevant_docs)
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'answer': f"Có lỗi xảy ra khi xử lý câu hỏi: {str(e)}",
                'sources': [],
                'confidence': 0.0
            }
    
    def batch_query(self, questions: List[str]) -> List[Dict[str, Any]]:
        """Xử lý nhiều câu hỏi song song"""
        logger.info(f"Processing {len(questions)} queries in batch")
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(self.query, questions))
        
        return results

# Hàm demo và testing
def demo_rag_system():
    """Demo hệ thống RAG"""
    # Khởi tạo hệ thống
    rag = LightweightRAGSystem()
    
    # Load documents (thay đổi paths theo thực tế)
    document_paths = [
        "data/luat_doanh_nghiep.pdf",
        "data/nghi_dinh_123.docx", 
        "data/thong_tu_45.txt"
    ]
    
    # Load documents
    rag.load_documents(document_paths)
    
    # Test queries
    test_questions = [
        "Thủ tục thành lập doanh nghiệp cần những giấy tờ gì?",
        "Điều kiện để được cấp giấy phép kinh doanh?",
        "Quy trình đăng ký thuế cho doanh nghiệp mới?",
        "Các loại hình doanh nghiệp được pháp luật cho phép?"
    ]
    
    print("🤖 Demo Hệ thống RAG Pháp lý")
    print("=" * 50)
    
    for question in test_questions:
        print(f"\n❓ Câu hỏi: {question}")
        print("-" * 30)
        
        result = rag.query(question)
        print(f"✅ Trả lời: {result['answer']}")
        print(f"📚 Số nguồn tham khảo: {result['num_sources']}")
        
        if result['sources']:
            print("📖 Nguồn:")
            for i, source in enumerate(result['sources'][:2], 1):
                print(f"  {i}. {source['filename']}")

