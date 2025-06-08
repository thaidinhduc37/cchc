# server/services/vector_rag/embeddings.py
"""
Vietnamese Legal Embedding Engine - CẬP NHẬT: E5-base optimized
"""
import os
import pickle
import hashlib
import logging
import numpy as np
from typing import List, Dict, Any
from datetime import datetime

from sentence_transformers import SentenceTransformer
from services.vector_rag.rag_config import config

logger = logging.getLogger(__name__)

class VietnameseEmbeddingModel:
    """CẬP NHẬT: Optimized for e5-base and Vietnamese legal"""

    def __init__(self):
        self.model_name = config.embedding_model
        self.model = None
        self.cache = {}
        self.cache_file = os.path.join(config.data_path, config.domain, "embeddings_cache.pkl")
        self.dimension = 768  # Default, will be updated
        
        # CẬP NHẬT: E5-base specific prefixes
        self.use_e5_prefixes = 'multilingual-e5' in self.model_name.lower()
        self.query_prefix = "query: " if self.use_e5_prefixes else ""
        self.doc_prefix = "passage: " if self.use_e5_prefixes else ""
        
        # CẬP NHẬT: Simplified legal terms for e5-base
        self.legal_terms = {
            'điều': 1.3, 'khoản': 1.3, 'điểm': 1.2,
            'hộ chiếu': 1.5, 'thị thực': 1.5, 'tạm trú': 1.4, 'thường trú': 1.4,
            'thủ tục': 1.3, 'hồ sơ': 1.3, 'lệ phí': 1.3
        }
        
        self._init_model()
        self._load_cache()

    def _init_model(self):
        """CẬP NHẬT: Initialize với e5-base optimization"""
        try:
            logger.info(f"🔄 Loading: {self.model_name}")
            
            # CẬP NHẬT: Special handling for e5 models
            if 'multilingual-e5' in self.model_name.lower():
                logger.info("🔧 Configuring for E5-base model...")
                self.model = SentenceTransformer(self.model_name)
                
                # E5 models benefit from normalization
                self.normalize_embeddings = True
            else:
                self.model = SentenceTransformer(self.model_name)
                self.normalize_embeddings = False
            
            # Get actual dimension
            test_embedding = self.model.encode(["test"], convert_to_tensor=False)
            self.dimension = len(test_embedding[0])
            
            logger.info(f"✅ Model loaded - Dimension: {self.dimension}")
            logger.info(f"   E5 prefixes: {self.use_e5_prefixes}")
            logger.info(f"   Normalization: {self.normalize_embeddings}")
            
        except Exception as e:
            logger.error(f"❌ Model init failed: {e}")
            raise

    def _load_cache(self):
        """Load cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    
                # CẬP NHẬT: Check cache compatibility
                if isinstance(cache_data, dict) and 'model_name' in cache_data:
                    if cache_data['model_name'] == self.model_name:
                        self.cache = cache_data.get('embeddings', {})
                        logger.info(f"📂 Cache loaded: {len(self.cache)} embeddings")
                    else:
                        logger.info(f"🔄 Cache model mismatch, clearing...")
                        self.cache = {}
                else:
                    # Old cache format
                    self.cache = cache_data if isinstance(cache_data, dict) else {}
                    logger.info(f"📂 Legacy cache loaded: {len(self.cache)} embeddings")
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")
            self.cache = {}

    def _save_cache(self):
        """CẬP NHẬT: Save cache với model info"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            cache_data = {
                'model_name': self.model_name,
                'dimension': self.dimension,
                'created_at': datetime.now().isoformat(),
                'embeddings': self.cache
            }
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def _preprocess_text(self, text: str, is_query: bool = False) -> str:
        """CẬP NHẬT: Preprocessing với E5 prefixes"""
        if not text or not text.strip():
            return ""
        
        text = text.strip()
        if len(text) > 1500:
            text = text[:1500] + "..."
        
        # CẬP NHẬT: Add E5 prefixes if using E5 model
        if self.use_e5_prefixes:
            if is_query:
                text = f"{self.query_prefix}{text}"
            else:
                text = f"{self.doc_prefix}{text}"
        else:
            # CẬP NHẬT: Reduced legal term boosting for other models
            words = text.split()
            boosted_words = []
            
            for word in words:
                weight = self.legal_terms.get(word.lower(), 1.0)
                if weight > 1.2:
                    boosted_words.extend([word] * min(int(weight), 2))
                else:
                    boosted_words.append(word)
            
            text = ' '.join(boosted_words)
        
        return text

    def _get_cache_key(self, text: str, is_query: bool = False) -> str:
        """CẬP NHẬT: Cache key với query/doc distinction"""
        preprocessed = self._preprocess_text(text, is_query)
        key_data = f"{self.model_name}:{preprocessed}:{'q' if is_query else 'd'}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()[:16]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """CẬP NHẬT: Embed documents với E5 optimization"""
        if not texts:
            return []

        # Check cache and prepare
        results = []
        texts_to_embed = []
        cache_indices = []
        
        for i, text in enumerate(texts):
            if not text or len(text.strip()) < 10:
                results.append([0.0] * self.dimension)
                continue
                
            cache_key = self._get_cache_key(text, is_query=False)
            
            if cache_key in self.cache:
                results.append(self.cache[cache_key])
            else:
                results.append(None)
                texts_to_embed.append(text)
                cache_indices.append(i)

        # Generate new embeddings
        if texts_to_embed:
            logger.info(f"🔄 Generating {len(texts_to_embed)} document embeddings...")
            
            try:
                # CẬP NHẬT: Preprocess with doc prefix
                preprocessed = [self._preprocess_text(t, is_query=False) for t in texts_to_embed]
                
                # CẬP NHẬT: Encode với E5 optimization
                embeddings = self.model.encode(
                    preprocessed,
                    batch_size=16,
                    show_progress_bar=False,
                    convert_to_tensor=False,
                    normalize_embeddings=self.normalize_embeddings
                )
                
                # Convert to list
                if hasattr(embeddings, 'tolist'):
                    embeddings = embeddings.tolist()
                
                # Store results and cache
                for i, embedding in enumerate(embeddings):
                    if i < len(cache_indices):
                        original_idx = cache_indices[i]
                        results[original_idx] = embedding
                        
                        # Cache with document key
                        cache_key = self._get_cache_key(texts_to_embed[i], is_query=False)
                        self.cache[cache_key] = embedding
                
                self._save_cache()
                logger.info(f"✅ Generated {len(embeddings)} document embeddings")
                
            except Exception as e:
                logger.error(f"❌ Document embedding failed: {e}")
                # Fill with zeros
                for idx in cache_indices:
                    if results[idx] is None:
                        results[idx] = [0.0] * self.dimension

        # Final validation
        for i, result in enumerate(results):
            if not isinstance(result, list) or len(result) != self.dimension:
                results[i] = [0.0] * self.dimension

        return results

    def embed_query(self, text: str) -> List[float]:
        """CẬP NHẬT: Query embedding với E5 query prefix"""
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        # Check cache first
        cache_key = self._get_cache_key(text, is_query=True)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            # CẬP NHẬT: Preprocess with query prefix
            preprocessed = self._preprocess_text(text, is_query=True)
            
            # Generate embedding
            embedding = self.model.encode(
                [preprocessed],
                convert_to_tensor=False,
                normalize_embeddings=self.normalize_embeddings
            )[0]
            
            # Convert to list and cache
            if hasattr(embedding, 'tolist'):
                embedding = embedding.tolist()
            
            self.cache[cache_key] = embedding
            self._save_cache()
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Query embedding failed: {e}")
            return [0.0] * self.dimension

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity"""
        if len(embedding1) != len(embedding2) or len(embedding1) != self.dimension:
            return 0.0
        
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # CẬP NHẬT: Handle normalized embeddings
        if self.normalize_embeddings:
            # For normalized embeddings, dot product = cosine similarity
            dot_product = np.dot(vec1, vec2)
            return float(np.clip(dot_product, -1.0, 1.0))
        else:
            # Standard cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))

    def get_stats(self) -> Dict[str, Any]:
        """CẬP NHẬT: Enhanced statistics"""
        cache_size_mb = 0
        if os.path.exists(self.cache_file):
            cache_size_mb = os.path.getsize(self.cache_file) / (1024 * 1024)
        
        return {
            'model_name': self.model_name,
            'dimension': self.dimension,
            'cached_embeddings': len(self.cache),
            'cache_size_mb': round(cache_size_mb, 2),
            'legal_terms_count': len(self.legal_terms),
            'use_e5_prefixes': self.use_e5_prefixes,
            'normalize_embeddings': self.normalize_embeddings,
            'query_prefix': self.query_prefix if self.query_prefix else 'None',
            'doc_prefix': self.doc_prefix if self.doc_prefix else 'None'
        }

    def clear_cache(self):
        """Clear cache"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        logger.info("🗑️ Embedding cache cleared")

    def test_embeddings(self, test_queries: List[str] = None) -> Dict[str, Any]:
        """CẬP NHẬT: Test embedding functionality"""
        if test_queries is None:
            test_queries = [
                "Điều kiện cấp hộ chiếu phổ thông",
                "Thủ tục làm thị thực",
                "Lệ phí gia hạn tạm trú"
            ]
        
        try:
            logger.info("🧪 Testing embeddings...")
            
            # Test query embeddings
            query_embeddings = []
            for query in test_queries:
                emb = self.embed_query(query)
                query_embeddings.append(emb)
            
            # Test document embeddings
            doc_embeddings = self.embed_documents(test_queries)
            
            # Test similarities
            similarities = []
            for i in range(len(query_embeddings)):
                if i < len(doc_embeddings):
                    sim = self.calculate_similarity(query_embeddings[i], doc_embeddings[i])
                    similarities.append(sim)
            
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0
            
            result = {
                'success': True,
                'test_queries': test_queries,
                'query_embeddings_generated': len(query_embeddings),
                'doc_embeddings_generated': len(doc_embeddings),
                'embedding_dimension': self.dimension,
                'average_self_similarity': round(avg_similarity, 3),
                'model_stats': self.get_stats()
            }
            
            logger.info(f"✅ Embedding test completed")
            logger.info(f"   📐 Dimension: {result['embedding_dimension']}")
            logger.info(f"   📊 Avg self-similarity: {result['average_self_similarity']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Embedding test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'model_stats': self.get_stats()
            }

# Alias
EmbeddingModel = VietnameseEmbeddingModel