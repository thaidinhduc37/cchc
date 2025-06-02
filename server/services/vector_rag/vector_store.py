# vector_store.py - Vector Store chuyên biệt
import os
import logging
from typing import List, Optional, Dict
from langchain.schema import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from .rag_config import CONFIG, DVCRAGConfig

logger = logging.getLogger(__name__)

class OptimizedVectorStore:
    def __init__(self, config: Optional[DVCRAGConfig] = None, domain: str = "default"):
        self.config = config or CONFIG
        self.domain = domain
        self.embeddings = None
        self.vector_store = None
        self.is_loaded = False

        # Path setup
        paths = self.config.get_domain_paths(domain) if domain != "default" else {
            "vector_store_path": self.config.vector_store_path
        }
        self.vector_store_path = paths["vector_store_path"]
        self._init_embeddings()

    def _init_embeddings(self):
        if self.embeddings is None:
            logger.info(f"Loading embedding: {self.config.embedding_model}")
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.config.embedding_model,
                model_kwargs={"device": self.config.device, "trust_remote_code": True},
                encode_kwargs={"normalize_embeddings": True, "batch_size": 32}
            )

    def create_vector_store(self, documents: List[Document]) -> bool:
        if not documents:
            logger.error("No documents for vector store")
            return False
        valid_docs = [doc for doc in documents if doc.page_content.strip()]
        if not valid_docs:
            logger.error("No valid documents after filtering")
            return False
        self.vector_store = FAISS.from_documents(valid_docs, self.embeddings)
        if self.save_vector_store():
            self.is_loaded = True
            logger.info(f"Vector store created: {len(valid_docs)} docs")
            return True
        return False

    def load_vector_store(self) -> bool:
        if not os.path.exists(self.vector_store_path):
            logger.warning(f"Vector store path not found: {self.vector_store_path}")
            return False
        self._init_embeddings()
        self.vector_store = FAISS.load_local(
            self.vector_store_path,
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        self.is_loaded = True
        logger.info("Vector store loaded")
        return True

    def save_vector_store(self) -> bool:
        if not self.vector_store:
            return False
        os.makedirs(os.path.dirname(self.vector_store_path), exist_ok=True)
        self.vector_store.save_local(self.vector_store_path)
        return True

    def search(self, query: str, k: int = None) -> List[Document]:
        """Tối ưu tìm kiếm với pre-filtering"""
        if not self.is_ready():
            logger.warning("Vector store not ready")
            return []
        
        k = k or self.config.top_k
        
        # Tăng k để có nhiều lựa chọn, sau đó filter
        search_k = min(k * 3, 15)
        
        try:
            results = self.vector_store.similarity_search_with_score(query, k=search_k)
            
            # Filter và sort theo relevance
            filtered = []
            for doc, score in results:
                similarity = 1 / (1 + score)
                
                if similarity >= self.config.score_threshold:
                    doc.metadata['similarity_score'] = similarity
                    
                    # Bonus cho nội dung có cấu trúc pháp lý
                    content_lower = doc.page_content.lower()
                    if any(keyword in content_lower for keyword in ['điều', 'khoản', 'điểm', 'chương']):
                        doc.metadata['similarity_score'] += 0.1
                    
                    filtered.append(doc)
            
            # Sort theo similarity score
            filtered.sort(key=lambda x: x.metadata.get('similarity_score', 0), reverse=True)
            
            result = filtered[:k]
            logger.info(f"Found {len(result)}/{len(results)} relevant docs")
            return result
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def is_ready(self) -> bool:
        return self.is_loaded and self.vector_store is not None
