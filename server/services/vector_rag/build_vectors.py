#!/usr/bin/env python3
"""
Script xây dựng vector database cho hệ thống RAG
Chạy: python build_vectors.py --data_dir ./documents --output_dir ./vector_db
"""

import os
import sys
import time
import argparse
import pickle
import json
from pathlib import Path
from typing import List, Dict, Any
import logging

# Import hệ thống RAG
from rag_system import (
    LightweightRAGSystem, 
    FastEmbeddings, 
    FastFAISSVectorStore,
    VietnameseLegalTextSplitter,
    DocumentProcessor,
    DocumentChunk
)

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('build_vectors.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class VectorDatabaseBuilder:
    """Class chính để xây dựng vector database"""
    
    def __init__(self, 
                 embedding_model: str = "keepitreal/vietnamese-sbert",
                 chunk_size: int = 800,
                 chunk_overlap: int = 100):
        
        logger.info("🚀 Khởi tạo Vector Database Builder...")
        
        self.embeddings = FastEmbeddings(embedding_model)
        self.text_splitter = VietnameseLegalTextSplitter(chunk_size, chunk_overlap)
        self.document_processor = DocumentProcessor()
        
        # Statistics
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_chunks': 0,
            'processing_time': 0,
            'file_types': {}
        }
        
        logger.info("✅ Vector Database Builder initialized!")
    
    def find_documents(self, data_dir: str) -> List[str]:
        """Tìm tất cả documents trong thư mục"""
        supported_extensions = ['.pdf', '.docx', '.doc', '.txt']
        document_paths = []
        
        data_path = Path(data_dir)
        if not data_path.exists():
            raise ValueError(f"Data directory không tồn tại: {data_dir}")
        
        logger.info(f"🔍 Tìm kiếm documents trong: {data_dir}")
        
        for ext in supported_extensions:
            files = list(data_path.rglob(f"*{ext}"))
            document_paths.extend([str(f) for f in files])
            self.stats['file_types'][ext] = len(files)
            logger.info(f"  Tìm thấy {len(files)} file {ext}")
        
        self.stats['total_files'] = len(document_paths)
        logger.info(f"📊 Tổng cộng: {len(document_paths)} documents")
        
        return document_paths
    
    def process_single_document(self, file_path: str) -> List[DocumentChunk]:
        """Xử lý một document thành chunks"""
        try:
            file_path_obj = Path(file_path)
            extension = file_path_obj.suffix.lower()
            
            logger.info(f"📄 Xử lý: {file_path_obj.name}")
            
            # Xử lý theo loại file
            if extension == '.pdf':
                text = self.document_processor.process_pdf(file_path)
            elif extension in ['.docx', '.doc']:
                text = self.document_processor.process_docx(file_path)
            elif extension == '.txt':
                text = self.document_processor.process_txt(file_path)
            else:
                logger.warning(f"⚠️ Loại file không hỗ trợ: {extension}")
                return []
            
            if not text.strip():
                logger.warning(f"⚠️ Không trích xuất được text từ: {file_path_obj.name}")
                return []
            
            # Metadata cho document
            metadata = {
                'source': str(file_path_obj),
                'filename': file_path_obj.name,
                'file_type': extension,
                'file_size': file_path_obj.stat().st_size,
                'processed_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Chia thành chunks
            chunks = self.text_splitter.split_text(text, metadata)
            
            logger.info(f"✅ Hoàn thành: {file_path_obj.name} -> {len(chunks)} chunks")
            self.stats['processed_files'] += 1
            self.stats['total_chunks'] += len(chunks)
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Lỗi xử lý {file_path}: {e}")
            self.stats['failed_files'] += 1
            return []
    
    def build_vector_database(self, 
                             data_dir: str, 
                             output_dir: str,
                             batch_size: int = 100) -> None:
        """Xây dựng vector database"""
        
        start_time = time.time()
        
        logger.info("🏗️ Bắt đầu xây dựng Vector Database")
        logger.info("=" * 60)
        
        # Tạo output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Tìm documents
        document_paths = self.find_documents(data_dir)
        if not document_paths:
            logger.error("❌ Không tìm thấy documents nào!")
            return
        
        # Khởi tạo vector store
        vector_store = FastFAISSVectorStore(self.embeddings)
        all_chunks = []
        
        # Xử lý từng document
        logger.info(f"📋 Bắt đầu xử lý {len(document_paths)} documents...")
        
        for i, doc_path in enumerate(document_paths, 1):
            logger.info(f"📊 Progress: {i}/{len(document_paths)}")
            
            chunks = self.process_single_document(doc_path)
            all_chunks.extend(chunks)
            
            # Xử lý theo batch để tiết kiệm memory
            if len(all_chunks) >= batch_size:
                logger.info(f"💾 Xử lý batch {len(all_chunks)} chunks...")
                vector_store.add_documents(all_chunks)
                all_chunks = []  # Clear memory
        
        # Xử lý chunks còn lại
        if all_chunks:
            logger.info(f"💾 Xử lý batch cuối {len(all_chunks)} chunks...")
            vector_store.add_documents(all_chunks)
        
        # Lưu vector database
        self._save_vector_database(vector_store, output_path)
        
        # Lưu metadata và statistics
        self._save_metadata(output_path)
        
        # Tính thời gian
        self.stats['processing_time'] = time.time() - start_time
        
        # In báo cáo
        self._print_summary()
        
        logger.info("🎉 Hoàn thành xây dựng Vector Database!")
    
    def _save_vector_database(self, vector_store: FastFAISSVectorStore, output_path: Path):
        """Lưu vector database"""
        logger.info("💾 Lưu Vector Database...")
        
        # Lưu FAISS index
        faiss_path = output_path / "faiss_index.index"
        import faiss
        faiss.write_index(vector_store.index, str(faiss_path))
        
        # Lưu documents (không bao gồm embeddings để tiết kiệm dung lượng)
        documents_data = []
        for doc in vector_store.documents:
            doc_data = {
                'content': doc.content,
                'metadata': doc.metadata
            }
            documents_data.append(doc_data)
        
        documents_path = output_path / "documents.pkl"
        with open(documents_path, 'wb') as f:
            pickle.dump(documents_data, f)
        
        logger.info(f"✅ Đã lưu FAISS index: {faiss_path}")
        logger.info(f"✅ Đã lưu documents: {documents_path}")
    
    def _save_metadata(self, output_path: Path):
        """Lưu metadata và cấu hình"""
        metadata = {
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'embedding_model': 'keepitreal/vietnamese-sbert',
            'chunk_size': self.text_splitter.chunk_size,
            'chunk_overlap': self.text_splitter.chunk_overlap,
            'statistics': self.stats,
            'version': '1.0'
        }
        
        metadata_path = output_path / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Đã lưu metadata: {metadata_path}")
    
    def _print_summary(self):
        """In báo cáo tổng kết"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 BÁO CÁO TỔNG KẾT")
        logger.info("=" * 60)
        logger.info(f"📁 Tổng số files: {self.stats['total_files']}")
        logger.info(f"✅ Files xử lý thành công: {self.stats['processed_files']}")
        logger.info(f"❌ Files lỗi: {self.stats['failed_files']}")
        logger.info(f"📄 Tổng số chunks: {self.stats['total_chunks']}")
        logger.info(f"⏱️ Thời gian xử lý: {self.stats['processing_time']:.2f}s")
        
        logger.info("\n📋 Chi tiết theo loại file:")
        for ext, count in self.stats['file_types'].items():
            logger.info(f"  {ext}: {count} files")
        
        if self.stats['total_chunks'] > 0:
            avg_chunks = self.stats['total_chunks'] / max(self.stats['processed_files'], 1)
            logger.info(f"📈 Trung bình chunks/file: {avg_chunks:.1f}")
        
        logger.info("=" * 60)

def load_vector_database(vector_db_path: str) -> FastFAISSVectorStore:
    """Load vector database đã được build"""
    logger.info(f"📂 Loading vector database từ: {vector_db_path}")
    
    db_path = Path(vector_db_path)
    if not db_path.exists():
        raise ValueError(f"Vector database không tồn tại: {vector_db_path}")
    
    # Load metadata
    metadata_path = db_path / "metadata.json"
    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    logger.info(f"📊 Database info: {metadata['statistics']['total_chunks']} chunks")
    
    # Khởi tạo embeddings
    embeddings = FastEmbeddings(metadata['embedding_model'])
    
    # Load FAISS index
    import faiss
    faiss_path = db_path / "faiss_index.index"
    index = faiss.read_index(str(faiss_path))
    
    # Load documents
    documents_path = db_path / "documents.pkl"
    with open(documents_path, 'rb') as f:
        documents_data = pickle.load(f)
    
    # Recreate DocumentChunk objects
    documents = []
    for doc_data in documents_data:
        chunk = DocumentChunk(
            content=doc_data['content'],
            metadata=doc_data['metadata']
        )
        documents.append(chunk)
    
    # Recreate vector store
    vector_store = FastFAISSVectorStore(embeddings)
    vector_store.index = index
    vector_store.documents = documents
    
    logger.info("✅ Vector database loaded successfully!")
    return vector_store

def main():
    """Hàm main"""
    parser = argparse.ArgumentParser(description="Xây dựng Vector Database cho RAG system")
    
    parser.add_argument(
        "--data_dir", 
        type=str, 
        required=True,
        help="Thư mục chứa documents (PDF, DOCX, TXT)"
    )
    
    parser.add_argument(
        "--output_dir", 
        type=str, 
        default="./vector_db",
        help="Thư mục output cho vector database (default: ./vector_db)"
    )
    
    parser.add_argument(
        "--embedding_model", 
        type=str, 
        default="keepitreal/vietnamese-sbert",
        help="Model embedding (default: keepitreal/vietnamese-sbert)"
    )
    
    parser.add_argument(
        "--chunk_size", 
        type=int, 
        default=800,
        help="Kích thước chunk (default: 800)"
    )
    
    parser.add_argument(
        "--chunk_overlap", 
        type=int, 
        default=100,
        help="Overlap giữa các chunk (default: 100)"
    )
    
    parser.add_argument(
        "--batch_size", 
        type=int, 
        default=100,
        help="Batch size cho xử lý (default: 100)"
    )
    
    args = parser.parse_args()
    
    try:
        # Khởi tạo builder
        builder = VectorDatabaseBuilder(
            embedding_model=args.embedding_model,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap
        )
        
        # Build vector database
        builder.build_vector_database(
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            batch_size=args.batch_size
        )
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Quá trình bị ngắt bởi người dùng")
    except Exception as e:
        logger.error(f"❌ Lỗi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()