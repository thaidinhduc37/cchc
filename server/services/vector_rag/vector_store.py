from services.vector_rag.rag_config import config
from services.vector_rag.document_processor import Document
from services.vector_rag.embeddings import VietnameseEmbeddingModel# server/services/vector_rag/vector_store.py
"""
Vector Store - OPTIMIZED with FAISS
"""
import os
import json
import pickle
import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import numpy as np

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

logger = logging.getLogger(__name__)

class VectorStore:
    """Optimized Vector Store with FAISS"""
    
    def __init__(self):
        self.config = config
        self.embedding_model = VietnameseEmbeddingModel()
        
        # FAISS index
        self.index = None
        
        # Document storage
        self.documents = []
        self.metadatas = []
        self.dimension = self.embedding_model.dimension
        
        # File paths
        self.vector_store_path = config.vector_store_path
        self.index_file = os.path.join(self.vector_store_path, "faiss_index.bin")
        self.docs_file = os.path.join(self.vector_store_path, "documents.pkl")
        self.meta_file = os.path.join(self.vector_store_path, "metadata.pkl")
        
        # Settings
        self.similarity_threshold = config.min_similarity_threshold
        
        # Stats
        self.stats = {
            'total_documents': 0,
            'last_updated': None,
            'embedding_model': config.embedding_model
        }
        
        self._init_faiss()
        
    def _init_faiss(self):
        """Initialize FAISS"""
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS not installed. Run: pip install faiss-cpu")
        
        try:
            # Load existing index
            if os.path.exists(self.index_file):
                self._load_index()
                logger.info(f"📂 Loaded vector store: {len(self.documents)} documents")
            else:
                # Create new index
                self._create_new_index()
                logger.info("✨ Created new FAISS index")
                
        except Exception as e:
            logger.error(f"FAISS init failed: {e}")
            self._create_new_index()
    
    def _create_new_index(self):
        """Create new FAISS index"""
        # Use IndexFlatIP for cosine similarity
        self.index = faiss.IndexFlatIP(self.dimension)
        self.documents = []
        self.metadatas = []
        logger.info(f"✨ Created FAISS index (dim: {self.dimension})")
    
    def _load_index(self):
        """Load FAISS index and documents"""
        try:
            # Load index
            self.index = faiss.read_index(self.index_file)
            
            # Load documents
            if os.path.exists(self.docs_file):
                with open(self.docs_file, 'rb') as f:
                    self.documents = pickle.load(f)
            
            # Load metadata
            if os.path.exists(self.meta_file):
                with open(self.meta_file, 'rb') as f:
                    self.metadatas = pickle.load(f)
            
            self._update_stats()
            
        except Exception as e:
            logger.error(f"Load index failed: {e}")
            self._create_new_index()
    
    def _save_index(self):
        """Save FAISS index and documents"""
        try:
            os.makedirs(self.vector_store_path, exist_ok=True)
            
            # Save index
            faiss.write_index(self.index, self.index_file)
            
            # Save documents
            with open(self.docs_file, 'wb') as f:
                pickle.dump(self.documents, f)
            
            # Save metadata
            with open(self.meta_file, 'wb') as f:
                pickle.dump(self.metadatas, f)
            
            self._update_stats()
            logger.info(f"💾 Saved vector store: {len(self.documents)} documents")
            
        except Exception as e:
            logger.error(f"Save index failed: {e}")
    
    def _update_stats(self):
        """Update statistics"""
        self.stats.update({
            'total_documents': len(self.documents),
            'last_updated': datetime.now().isoformat()
        })
    
    async def initialize(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Initialize vector store"""
        try:
            if force_rebuild:
                logger.info("🗑️ Force rebuilding vector store...")
                self._create_new_index()
                self._save_index()
            
            return {
                'success': True,
                'message': f"Vector store initialized: {len(self.documents)} documents",
                'stats': self.stats
            }
            
        except Exception as e:
            logger.error(f"Initialize failed: {e}")
            return {
                'success': False,
                'message': f"Initialize failed: {e}"
            }
    
    async def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to vector store"""
        if not documents:
            return False
        
        try:
            logger.info(f"Adding {len(documents)} documents...")
            
            # Extract content and metadata
            texts = []
            doc_metadatas = []
            
            for doc in documents:
                if doc.content.strip():
                    texts.append(doc.content)
                    doc_metadatas.append(doc.metadata)
            
            if not texts:
                logger.warning("No valid texts to add")
                return False
            
            # Generate embeddings
            logger.info("🧮 Generating embeddings...")
            embeddings = self.embedding_model.embed_documents(texts)
            
            if not embeddings or len(embeddings) != len(texts):
                logger.error("❌ Embedding generation failed")
                return False
            
            # Convert to FAISS format
            embeddings_array = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings_array)  # Normalize for cosine similarity
            
            # Add to index
            self.index.add(embeddings_array)
            
            # Store documents and metadata
            self.documents.extend(texts)
            self.metadatas.extend(doc_metadatas)
            
            # Save
            self._save_index()
            
            logger.info(f"✅ Added {len(texts)} documents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Add documents failed: {e}")
            return False
    
    async def search(self, query: str, k: int = None, 
                    search_type: str = "normal",
                    filter_metadata: Dict = None) -> List[Dict]:
        """Search with legal optimization"""
        k = k or config.search_k
        
        try:
            if self.index.ntotal == 0:
                logger.warning("Vector store is empty")
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model.embed_query(query)
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Exact legal search for specific articles
            if search_type == "exact_legal" and self._is_exact_legal_query(query):
                return await self._exact_legal_search(query, query_embedding, k)
            
            # Normal semantic search
            return await self._semantic_search(query_embedding, k, filter_metadata)
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def _is_exact_legal_query(self, query: str) -> bool:
        """Check if query asks for exact legal article"""
        import re
        
        exact_patterns = [
            r'điều\s+\d+[a-z]?\s+(luật|nghị\s*định|thông\s*tư)',
            r'khoản\s+\d+\s+điều\s+\d+',
            r'điểm\s+[a-z]+\s+khoản\s+\d+'
        ]
        
        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in exact_patterns)
    
    async def _exact_legal_search(self, query: str, query_embedding: List[float], k: int) -> List[Dict]:
        """Exact legal article search"""
        import re
        
        # Extract legal reference
        query_lower = query.lower()
        
        # Find article number
        article_match = re.search(r'điều\s+(\d+[a-z]?)', query_lower)
        article_num = article_match.group(1) if article_match else None
        
        # Do semantic search first to get candidates
        candidates = await self._semantic_search(query_embedding, k * 2)
        
        # Filter and boost exact matches
        exact_matches = []
        partial_matches = []
        
        for candidate in candidates:
            content = candidate['content'].lower()
            metadata = candidate.get('metadata', {})
            
            # Check for exact article match
            article_score = 0
            if article_num and f'điều {article_num}' in content:
                article_score = 2.0
            elif article_num and f'điều{article_num}' in content:
                article_score = 1.5
            
            # Boost score
            enhanced_score = candidate['score'] + article_score
            
            enhanced_candidate = candidate.copy()
            enhanced_candidate['enhanced_score'] = enhanced_score
            enhanced_candidate['article_match'] = article_score > 0
            
            if article_score >= 1.5:
                exact_matches.append(enhanced_candidate)
            else:
                partial_matches.append(enhanced_candidate)
        
        # Sort and combine
        exact_matches.sort(key=lambda x: x['enhanced_score'], reverse=True)
        partial_matches.sort(key=lambda x: x['enhanced_score'], reverse=True)
        
        results = exact_matches[:k//2] + partial_matches[:k//2]
        return results[:k]
    
    async def _semantic_search(self, query_embedding: List[float], k: int, 
                              filter_metadata: Dict = None) -> List[Dict]:
        """Standard semantic search"""
        try:
            # Convert to numpy
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            # Search
            similarities, indices = self.index.search(query_vector, k)
            
            results = []
            for i, (similarity, doc_idx) in enumerate(zip(similarities[0], indices[0])):
                if doc_idx >= len(self.documents):
                    continue
                
                # Apply similarity threshold
                if similarity < self.similarity_threshold:
                    continue
                
                # Get document and metadata
                content = self.documents[doc_idx]
                metadata = self.metadatas[doc_idx] if doc_idx < len(self.metadatas) else {}
                
                # Apply metadata filter if provided
                if filter_metadata:
                    if not self._match_metadata_filter(metadata, filter_metadata):
                        continue
                
                result = {
                    'content': content,
                    'metadata': metadata,
                    'score': float(similarity),
                    'index': int(doc_idx)
                }
                
                results.append(result)
            
            logger.info(f"✅ Semantic search: {len(results)} results (threshold: {self.similarity_threshold})")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _match_metadata_filter(self, metadata: Dict, filter_criteria: Dict) -> bool:
        """Check if metadata matches filter criteria"""
        for key, value in filter_criteria.items():
            if key not in metadata:
                return False
            
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            else:
                if metadata[key] != value:
                    return False
        
        return True
    
    async def similarity_search_with_threshold(self, query: str, threshold: float = None) -> List[Dict]:
        """Search with custom similarity threshold"""
        original_threshold = self.similarity_threshold
        
        if threshold is not None:
            self.similarity_threshold = threshold
        
        try:
            results = await self.search(query)
            return results
        finally:
            self.similarity_threshold = original_threshold
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        index_size_mb = 0
        if os.path.exists(self.index_file):
            index_size_mb = os.path.getsize(self.index_file) / (1024 * 1024)
        
        return {
            'total_documents': len(self.documents),
            'embedding_model': self.stats['embedding_model'],
            'dimension': self.dimension,
            'similarity_threshold': self.similarity_threshold,
            'index_size_mb': round(index_size_mb, 2),
            'last_updated': self.stats.get('last_updated'),
            'faiss_index_type': str(type(self.index).__name__) if self.index else 'None'
        }
    
    def clear_store(self):
        """Clear vector store"""
        self._create_new_index()
        
        # Remove files
        for file_path in [self.index_file, self.docs_file, self.meta_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        logger.info("🗑️ Vector store cleared")
    
    async def update_document(self, doc_index: int, new_document: Document) -> bool:
        """Update a specific document (requires rebuild)"""
        if doc_index >= len(self.documents):
            return False
        
        try:
            # Update document content and metadata
            self.documents[doc_index] = new_document.content
            self.metadatas[doc_index] = new_document.metadata
            
            # Note: FAISS doesn't support in-place updates
            # Would need to rebuild index for embedding changes
            logger.warning("Document updated but embeddings not regenerated. Consider rebuilding index.")
            
            self._save_index()
            return True
            
        except Exception as e:
            logger.error(f"Update document failed: {e}")
            return False