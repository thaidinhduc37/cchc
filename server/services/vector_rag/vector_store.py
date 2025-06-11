# server/services/vector_rag/vector_store.py  
"""
Vector Store - SỬA LOGIC: Thêm entity reranking
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

from services.vector_rag.rag_config import config
from services.vector_rag.document_processor import Document
from services.vector_rag.embeddings import VietnameseEmbeddingModel

logger = logging.getLogger(__name__)

class VectorStore:
    """Vector Store với entity reranking"""
    
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
        
        # SỬA LOGIC: Entity reranking settings
        self.critical_entities = {
            'hộ chiếu': ['hộ chiếu', 'passport', 'ho chieu'],
            'thị thực': ['thị thực', 'visa', 'thi thuc'],
            'tạm trú': ['tạm trú', 'tam tru'],
            'thường trú': ['thường trú', 'thuong tru'],
            'trẻ em': ['trẻ em', 'tre em', 'children'],
            'lệ phí': ['lệ phí', 'le phi', 'phí'],
            'điều kiện': ['điều kiện', 'dieu kien', 'yêu cầu'],
            'hồ sơ': ['hồ sơ', 'ho so', 'giấy tờ']
        }
        
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
            if os.path.exists(self.index_file):
                self._load_index()
                logger.info(f"📂 Loaded vector store: {len(self.documents)} documents")
            else:
                self._create_new_index()
                logger.info("✨ Created new FAISS index")
                
        except Exception as e:
            logger.error(f"FAISS init failed: {e}")
            self._create_new_index()
    
    def _create_new_index(self):
        """Create new FAISS index"""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.documents = []
        self.metadatas = []
        logger.info(f"✨ Created FAISS index (dim: {self.dimension})")
    
    def _load_index(self):
        """Load FAISS index and documents"""
        try:
            self.index = faiss.read_index(self.index_file)
            
            if os.path.exists(self.docs_file):
                with open(self.docs_file, 'rb') as f:
                    self.documents = pickle.load(f)
            
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
            
            faiss.write_index(self.index, self.index_file)
            
            with open(self.docs_file, 'wb') as f:
                pickle.dump(self.documents, f)
            
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
            
            texts = []
            doc_metadatas = []
            
            for doc in documents:
                if doc.content.strip():
                    texts.append(doc.content)
                    doc_metadatas.append(doc.metadata)
            
            if not texts:
                logger.warning("No valid texts to add")
                return False
            
            logger.info("🧮 Generating embeddings...")
            embeddings = self.embedding_model.embed_documents(texts)
            
            if not embeddings or len(embeddings) != len(texts):
                logger.error("❌ Embedding generation failed")
                return False
            
            embeddings_array = np.array(embeddings, dtype=np.float32)
            faiss.normalize_L2(embeddings_array)
            
            self.index.add(embeddings_array)
            self.documents.extend(texts)
            self.metadatas.extend(doc_metadatas)
            
            self._save_index()
            
            logger.info(f"✅ Added {len(texts)} documents")
            return True
            
        except Exception as e:
            logger.error(f"❌ Add documents failed: {e}")
            return False
    
    async def search(self, query: str, k: int = None, 
                    search_type: str = "normal",
                    filter_metadata: Dict = None,
                    query_entities: List[str] = None) -> List[Dict]:
        """SỬA LOGIC: Search với entity reranking"""
        k = k or config.search_k
        
        try:
            if self.index.ntotal == 0:
                logger.warning("Vector store is empty")
                return []
            
            query_embedding = self.embedding_model.embed_query(query)
            
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Exact legal search for specific articles
            if search_type == "exact_legal" and self._is_exact_legal_query(query):
                return await self._exact_legal_search(query, query_embedding, k)
            
            # Normal semantic search
            results = await self._semantic_search(query_embedding, k * 2, filter_metadata)  # Get more for reranking
            
            # SỬA LOGIC: Apply entity reranking
            if query_entities and results:
                results = self._rerank_by_entities(results, query_entities, query)
            
            return results[:k]  # Return top k after reranking
            
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
        
        query_lower = query.lower()
        
        article_match = re.search(r'điều\s+(\d+[a-z]?)', query_lower)
        article_num = article_match.group(1) if article_match else None
        
        candidates = await self._semantic_search(query_embedding, k * 2)
        
        exact_matches = []
        partial_matches = []
        
        for candidate in candidates:
            content = candidate['content'].lower()
            
            article_score = 0
            if article_num and f'điều {article_num}' in content:
                article_score = 2.0
            elif article_num and f'điều{article_num}' in content:
                article_score = 1.5
            
            enhanced_score = candidate['score'] + article_score
            
            enhanced_candidate = candidate.copy()
            enhanced_candidate['enhanced_score'] = enhanced_score
            enhanced_candidate['article_match'] = article_score > 0
            
            if article_score >= 1.5:
                exact_matches.append(enhanced_candidate)
            else:
                partial_matches.append(enhanced_candidate)
        
        exact_matches.sort(key=lambda x: x['enhanced_score'], reverse=True)
        partial_matches.sort(key=lambda x: x['enhanced_score'], reverse=True)
        
        results = exact_matches[:k//2] + partial_matches[:k//2]
        return results[:k]
    
    async def _semantic_search(self, query_embedding: List[float], k: int, 
                              filter_metadata: Dict = None) -> List[Dict]:
        """Standard semantic search"""
        try:
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            similarities, indices = self.index.search(query_vector, k)
            
            results = []
            for i, (similarity, doc_idx) in enumerate(zip(similarities[0], indices[0])):
                if doc_idx >= len(self.documents):
                    continue
                
                if similarity < self.similarity_threshold:
                    continue
                
                content = self.documents[doc_idx]
                metadata = self.metadatas[doc_idx] if doc_idx < len(self.metadatas) else {}
                
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
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _rerank_by_entities(self, results: List[Dict], query_entities: List[str], query: str) -> List[Dict]:
        """SỬA LOGIC: Rerank results by entity matching"""
        if not query_entities:
            return results
        
        logger.info(f"🔄 Reranking {len(results)} results by entities: {query_entities}")
        
        reranked = []
        
        for result in results:
            content = result.get('content', '').lower()
            original_score = result.get('score', 0.5)
            
            # Calculate entity matching score
            entity_score = self._calculate_entity_score(content, query_entities)
            
            # Calculate final score
            final_score = original_score + entity_score
            
            # Track entity matches for debugging
            matched_entities = []
            missing_entities = []
            
            for entity in query_entities:
                if self._entity_exists_in_content(entity, content):
                    matched_entities.append(entity)
                else:
                    missing_entities.append(entity)
            
            # Add enhanced result
            enhanced_result = result.copy()
            enhanced_result['entity_score'] = entity_score
            enhanced_result['final_score'] = max(final_score, 0.0)
            enhanced_result['matched_entities'] = matched_entities
            enhanced_result['missing_entities'] = missing_entities
            
            reranked.append(enhanced_result)
        
        # Sort by final score
        reranked.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Filter out results with too many missing critical entities
        filtered = []
        for result in reranked:
            critical_missing = [e for e in result['missing_entities'] 
                              if e.lower() in self.critical_entities]
            
            # Skip if missing too many critical entities
            if len(critical_missing) > 2:
                logger.debug(f"❌ Filtered: missing {critical_missing}")
                continue
            
            # Skip if final score too low
            if result['final_score'] < 0.2:
                logger.debug(f"❌ Filtered: score {result['final_score']:.3f}")
                continue
            
            filtered.append(result)
        
        logger.info(f"✅ Reranked: {len(results)} → {len(filtered)} results")
        return filtered
    
    def _calculate_entity_score(self, content: str, query_entities: List[str]) -> float:
        """Calculate entity matching score"""
        if not query_entities:
            return 0.0
        
        score = 0.0
        matched_count = 0
        
        for entity in query_entities:
            if self._entity_exists_in_content(entity, content):
                matched_count += 1
                
                # Bonus for critical entities
                if entity.lower() in self.critical_entities:
                    score += 0.15
                else:
                    score += 0.1
        
        # Penalty for missing entities
        missing_count = len(query_entities) - matched_count
        if missing_count > 0:
            score -= missing_count * 0.1
        
        # Bonus for high match ratio
        match_ratio = matched_count / len(query_entities)
        if match_ratio >= 0.8:
            score += 0.1
        
        return score
    
    def _entity_exists_in_content(self, entity: str, content: str) -> bool:
        """Check if entity exists in content"""
        entity_lower = entity.lower()
        
        # Direct match
        if entity_lower in content:
            return True
        
        # Check variants
        if entity_lower in self.critical_entities:
            variants = self.critical_entities[entity_lower]
            if any(variant in content for variant in variants):
                return True
        
        return False
    
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
            'faiss_index_type': str(type(self.index).__name__) if self.index else 'None',
            'critical_entities': len(self.critical_entities)
        }
    
    def clear_store(self):
        """Clear vector store"""
        self._create_new_index()
        
        for file_path in [self.index_file, self.docs_file, self.meta_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        logger.info("🗑️ Vector store cleared")

    async def search_comprehensive(self, query: str, k: int = None) -> List[Dict]:
        """THÊM: Comprehensive search - lấy TẤT CẢ content liên quan"""
        k = k or config.search_k
        
        try:
            # Step 1: Normal semantic search với threshold thấp
            primary_results = await self.search(
                query, 
                k=k*2,  # Double the normal amount
                search_type="normal"
            )
            
            # Step 2: Extract key entities từ primary results
            key_entities = self._extract_entities_from_results(primary_results)
            
            # Step 3: Search cho từng entity để tìm related content
            related_results = []
            for entity in key_entities[:5]:  # Top 5 entities
                entity_results = await self.search(
                    entity,
                    k=3,
                    search_type="normal"
                )
                related_results.extend(entity_results)
            
            # Step 4: Merge và deduplicate
            all_results = primary_results + related_results
            unique_results = self._deduplicate_results(all_results)
            
            # Step 5: Sort by relevance
            sorted_results = sorted(unique_results, 
                                key=lambda x: x.get('final_score', x.get('score', 0)), 
                                reverse=True)
            
            logger.info(f"🔍 Comprehensive search: {len(sorted_results)} total results")
            return sorted_results[:k*3]  # Return up to 3x normal amount
            
        except Exception as e:
            logger.error(f"❌ Comprehensive search failed: {e}")
            return await self.search(query, k=k)  # Fallback to normal search

    def _extract_entities_from_results(self, results: List[Dict]) -> List[str]:
        """Extract key legal entities từ search results"""
        import re
        
        entities = set()
        
        for result in results[:3]:  # Top 3 results
            content = result.get('content', '')
            
            # Extract legal references
            legal_refs = re.findall(r'(Luật số \d+/\d{4}|Nghị định số \d+/\d{4}|Thông tư số \d+/\d{4})', content)
            entities.update(legal_refs[:2])  # Top 2 legal docs
            
            # Extract articles
            articles = re.findall(r'Điều \d+[a-z]?', content)
            entities.update(articles[:3])  # Top 3 articles
            
            # Extract key terms
            key_terms = re.findall(r'(hộ chiếu|thị thực|tạm trú|thường trú|xuất cảnh|nhập cảnh)', content.lower())
            entities.update(key_terms[:2])
        
        return list(entities)

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """Remove duplicate results based on content similarity"""
        unique_results = []
        seen_content_hashes = set()
        
        for result in results:
            content = result.get('content', '')
            # Create simple hash from first 200 chars
            content_hash = hash(content[:200])
            
            if content_hash not in seen_content_hashes:
                seen_content_hashes.add(content_hash)
                unique_results.append(result)
        
        return unique_results