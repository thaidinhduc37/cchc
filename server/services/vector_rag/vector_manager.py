# vector_manager.py - Quản lý Vector Store với multi-domain
import os
import json
import pickle
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime


from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document

from services.vector_rag.config import EmbeddingConfig, SystemConfig, RetrievalConfig

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Quản lý vector store với hỗ trợ multi-domain"""
    
    def __init__(self, 
                 embedding_config: EmbeddingConfig = None,
                 system_config: SystemConfig = None,
                 retrieval_config: RetrievalConfig = None):
        
        self.embedding_config = embedding_config or EmbeddingConfig()
        self.system_config = system_config or SystemConfig()
        self.retrieval_config = retrieval_config or RetrievalConfig()
        
        # Setup embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_config.model_name,
            model_kwargs={'device': self.embedding_config.device},
            encode_kwargs={'normalize_embeddings': self.embedding_config.normalize_embeddings}
        )
        
        # Vector stores cho từng domain
        self.vector_stores: Dict[str, FAISS] = {}
        self.domain_metadata: Dict[str, Dict] = {}
    
    def create_domain_vector_store(self, 
                                   documents: List[Document], 
                                   domain: str,
                                   save_path: str = None) -> FAISS:
        """Tạo vector store cho một domain cụ thể"""
        if not documents:
            logger.warning(f"No documents provided for domain {domain}")
            return None
        
        logger.info(f"Creating vector store for domain: {domain}")
        
        # Filter documents by domain
        domain_docs = [doc for doc in documents 
                      if doc.metadata.get('domain') == domain or domain == 'all']
        
        if not domain_docs:
            logger.warning(f"No documents found for domain {domain}")
            return None
        
        # Create vector store
        vector_store = FAISS.from_documents(
            documents=domain_docs,
            embedding=self.embeddings
        )
        
        # Save vector store
        if not save_path:
            save_path = os.path.join(self.system_config.vector_store_path, f"{domain}_vectorstore")
        
        vector_store.save_local(save_path)
        
        # Save metadata
        metadata = {
            'domain': domain,
            'num_documents': len(domain_docs),
            'created_at': str(datetime.now()),
            'save_path': save_path,
            'embedding_model': self.embedding_config.model_name
        }
        
        self.vector_stores[domain] = vector_store
        self.domain_metadata[domain] = metadata
        
        # Save metadata to file
        metadata_path = os.path.join(save_path, 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Vector store for {domain} created with {len(domain_docs)} documents")
        return vector_store
    
    def load_domain_vector_store(self, domain: str, load_path: str = None) -> Optional[FAISS]:
        """Load vector store cho domain cụ thể"""
        if not load_path:
            load_path = os.path.join(self.system_config.vector_store_path, f"{domain}_vectorstore")
        
        if not os.path.exists(load_path):
            logger.warning(f"Vector store not found for domain {domain} at {load_path}")
            return None
        
        try:
            logger.info(f"Loading vector store for domain: {domain}")
            vector_store = FAISS.load_local(
                load_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            # Load metadata
            metadata_path = os.path.join(load_path, 'metadata.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                self.domain_metadata[domain] = metadata
            
            self.vector_stores[domain] = vector_store
            logger.info(f"Successfully loaded vector store for domain: {domain}")
            return vector_store
            
        except Exception as e:
            logger.error(f"Error loading vector store for domain {domain}: {str(e)}")
            return None
    
    def create_multi_domain_stores(self, documents: List[Document]) -> Dict[str, FAISS]:
        """Tạo vector stores cho tất cả domains"""
        # Phân loại documents theo domain
        domain_docs = {}
        for doc in documents:
            domain = doc.metadata.get('domain', 'general')
            if domain not in domain_docs:
                domain_docs[domain] = []
            domain_docs[domain].append(doc)
        
        # Tạo vector store cho mỗi domain
        created_stores = {}
        for domain, docs in domain_docs.items():
            store = self.create_domain_vector_store(docs, domain)
            if store:
                created_stores[domain] = store
        
        logger.info(f"Created vector stores for domains: {list(created_stores.keys())}")
        return created_stores
    
    def load_all_domain_stores(self) -> Dict[str, FAISS]:
        """Load tất cả vector stores có sẵn"""
        vector_store_dir = Path(self.system_config.vector_store_path)
        if not vector_store_dir.exists():
            logger.warning("Vector store directory not found")
            return {}
        
        loaded_stores = {}
        for item in vector_store_dir.iterdir():
            if item.is_dir() and item.name.endswith('_vectorstore'):
                domain = item.name.replace('_vectorstore', '')
                store = self.load_domain_vector_store(domain, str(item))
                if store:
                    loaded_stores[domain] = store
        
        logger.info(f"Loaded vector stores for domains: {list(loaded_stores.keys())}")
        return loaded_stores
    
    def get_retriever(self, domain: str = None, k: int = None):
        """Tạo retriever cho domain cụ thể hoặc tất cả domains"""
        k = k or self.retrieval_config.k
        
        if domain and domain in self.vector_stores:
            # Single domain retriever
            return self.vector_stores[domain].as_retriever(
                search_type=self.retrieval_config.search_type,
                search_kwargs={"k": k}
            )
        
        elif not domain and self.vector_stores:
            # Multi-domain retriever - merge tất cả
            return self._create_multi_domain_retriever(k)
        
        else:
            raise ValueError(f"No vector store found for domain: {domain}")
    
    def _create_multi_domain_retriever(self, k: int):
        """Tạo retriever kết hợp nhiều domains"""
        class MultiDomainRetriever:
            def __init__(self, vector_stores, k):
                self.vector_stores = vector_stores
                self.k = k
            
            def get_relevant_documents(self, query):
                all_docs = []
                k_per_domain = max(1, self.k // len(self.vector_stores))
                
                for domain, store in self.vector_stores.items():
                    try:
                        docs = store.similarity_search(query, k=k_per_domain)
                        # Thêm domain info vào metadata
                        for doc in docs:
                            doc.metadata['search_domain'] = domain
                        all_docs.extend(docs)
                    except Exception as e:
                        logger.error(f"Error searching in domain {domain}: {str(e)}")
                
                # Sort by relevance score if available
                return all_docs[:self.k]
        
        return MultiDomainRetriever(self.vector_stores, k)
    
    def search_by_domain(self, query: str, domain: str, k: int = None) -> List[Document]:
        """Tìm kiếm trong domain cụ thể"""
        k = k or self.retrieval_config.k
        
        if domain not in self.vector_stores:
            logger.warning(f"Domain {domain} not found in vector stores")
            return []
        
        try:
            docs = self.vector_stores[domain].similarity_search_with_score(query, k=k)
            
            # Filter by score threshold if configured
            if self.retrieval_config.score_threshold:
                docs = [(doc, score) for doc, score in docs 
                       if score >= self.retrieval_config.score_threshold]
            
            return [doc for doc, score in docs]
        except Exception as e:
            logger.error(f"Error searching in domain {domain}: {str(e)}")
            return []
    
    def search_all_domains(self, query: str, k: int = None) -> Dict[str, List[Document]]:
        """Tìm kiếm trong tất cả domains"""
        k = k or self.retrieval_config.k
        results = {}
        
        for domain in self.vector_stores.keys():
            docs = self.search_by_domain(query, domain, k)
            if docs:
                results[domain] = docs
        
        return results
    
    def get_domain_stats(self) -> Dict[str, Any]:
        """Thống kê các domains"""
        stats = {
            'total_domains': len(self.vector_stores),
            'domains': {},
            'total_vectors': 0
        }
        
        for domain, metadata in self.domain_metadata.items():
            domain_stats = {
                'num_documents': metadata.get('num_documents', 0),
                'created_at': metadata.get('created_at'),
                'embedding_model': metadata.get('embedding_model')
            }
            
            # Get vector count if available
            if domain in self.vector_stores:
                try:
                    vector_count = self.vector_stores[domain].index.ntotal
                    domain_stats['vector_count'] = vector_count
                    stats['total_vectors'] += vector_count
                except:
                    pass
            
            stats['domains'][domain] = domain_stats
        
        return stats
    
    def add_documents_to_domain(self, documents: List[Document], domain: str):
        """Thêm documents vào domain hiện có"""
        if domain not in self.vector_stores:
            logger.warning(f"Domain {domain} not found. Creating new vector store.")
            return self.create_domain_vector_store(documents, domain)
        
        # Add to existing vector store
        self.vector_stores[domain].add_documents(documents)
        
        # Update metadata
        if domain in self.domain_metadata:
            self.domain_metadata[domain]['num_documents'] += len(documents)
            self.domain_metadata[domain]['updated_at'] = str(datetime.now())
        
        logger.info(f"Added {len(documents)} documents to domain {domain}")
    
    def delete_domain_store(self, domain: str):
        """Xóa vector store của domain"""
        if domain in self.vector_stores:
            del self.vector_stores[domain]
        
        if domain in self.domain_metadata:
            del self.domain_metadata[domain]
        
        # Xóa files
        store_path = os.path.join(self.system_config.vector_store_path, f"{domain}_vectorstore")
        if os.path.exists(store_path):
            import shutil
            shutil.rmtree(store_path)
        
        logger.info(f"Deleted vector store for domain: {domain}")

# Utility class cho hybrid search (để scale lên sau)
class HybridRetriever:
    """Retriever kết hợp semantic + keyword search"""
    
    def __init__(self, vector_store, bm25_retriever=None):
        self.vector_store = vector_store
        self.bm25_retriever = bm25_retriever
    
    def get_relevant_documents(self, query: str, k: int = 5):
        """Kết hợp semantic và keyword search"""
        # Semantic search
        semantic_docs = self.vector_store.similarity_search(query, k=k)
        
        # Keyword search (nếu có)
        if self.bm25_retriever:
            keyword_docs = self.bm25_retriever.get_relevant_documents(query)
            # Merge và deduplicate
            all_docs = semantic_docs + keyword_docs
            # Remove duplicates based on content
            seen = set()
            unique_docs = []
            for doc in all_docs:
                if doc.page_content not in seen:
                    seen.add(doc.page_content)
                    unique_docs.append(doc)
            return unique_docs[:k]
        
        return semantic_docs