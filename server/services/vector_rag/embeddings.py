# server/services/vector_rag/embeddings.py
"""
Vietnamese Legal Embedding Engine - OPTIMIZED & CONCISE
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
    """Tối ưu Vietnamese Legal Embedding Model"""

    def __init__(self):
        self.model_name = config.embedding_model
        self.model = None
        self.cache = {}
        self.cache_file = os.path.join(config.data_path, config.domain, "embeddings_cache.pkl")
        self.dimension = 768
        
        # Core legal terms only (simplified)
        self.legal_terms = {
            'điều': 1.5, 'khoản': 1.5, 'điểm': 1.3,
            'hộ chiếu': 1.8, 'thị thực': 1.8, 'tạm trú': 1.6, 'thường trú': 1.6,
            'thủ tục': 1.5, 'hồ sơ': 1.4, 'lệ phí': 1.4
        }
        
        self._init_model()
        self._load_cache()

    def _init_model(self):
        """Initialize model - simplified"""
        try:
            logger.info(f"🔄 Loading: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            
            # Get dimension
            test_embedding = self.model.encode(["test"], convert_to_tensor=False)
            self.dimension = len(test_embedding[0])
            
            logger.info(f"✅ Model loaded - Dimension: {self.dimension}")
        except Exception as e:
            logger.error(f"❌ Model init failed: {e}")
            raise

    def _load_cache(self):
        """Load cache - simplified"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    self.cache = pickle.load(f)
                logger.info(f"📂 Cache loaded: {len(self.cache)} embeddings")
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")
            self.cache = {}

    def _save_cache(self):
        """Save cache - simplified"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def _preprocess_text(self, text: str) -> str:
        """Simple preprocessing"""
        if not text or not text.strip():
            return ""
        
        text = text.strip()
        if len(text) > 1500:
            text = text[:1500] + "..."
        
        # Simple legal term boosting
        words = text.split()
        boosted_words = []
        
        for word in words:
            weight = self.legal_terms.get(word.lower(), 1.0)
            if weight > 1.3:
                boosted_words.extend([word] * min(int(weight), 2))
            else:
                boosted_words.append(word)
        
        return ' '.join(boosted_words)

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key"""
        preprocessed = self._preprocess_text(text)
        return hashlib.sha256(preprocessed.encode('utf-8')).hexdigest()[:16]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents - optimized"""
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
                
            cache_key = self._get_cache_key(text)
            
            if cache_key in self.cache:
                results.append(self.cache[cache_key])
            else:
                results.append(None)
                texts_to_embed.append(text)
                cache_indices.append(i)

        # Generate new embeddings
        if texts_to_embed:
            logger.info(f"🔄 Generating {len(texts_to_embed)} embeddings...")
            
            try:
                # Preprocess
                preprocessed = [self._preprocess_text(t) for t in texts_to_embed]
                
                # Encode
                embeddings = self.model.encode(
                    preprocessed,
                    batch_size=16,
                    show_progress_bar=False,
                    convert_to_tensor=False,
                    normalize_embeddings=True
                )
                
                # Convert to list
                if hasattr(embeddings, 'tolist'):
                    embeddings = embeddings.tolist()
                
                # Store results and cache
                for i, embedding in enumerate(embeddings):
                    if i < len(cache_indices):
                        original_idx = cache_indices[i]
                        results[original_idx] = embedding
                        
                        # Cache
                        cache_key = self._get_cache_key(texts_to_embed[i])
                        self.cache[cache_key] = embedding
                
                self._save_cache()
                logger.info(f"✅ Generated {len(embeddings)} embeddings")
                
            except Exception as e:
                logger.error(f"❌ Embedding failed: {e}")
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
        """Query embedding - optimized"""
        if not text or not text.strip():
            return [0.0] * self.dimension
        
        result = self.embed_documents([text])
        return result[0] if result else [0.0] * self.dimension

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity"""
        if len(embedding1) != len(embedding2) or len(embedding1) != self.dimension:
            return 0.0
        
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        cache_size_mb = 0
        if os.path.exists(self.cache_file):
            cache_size_mb = os.path.getsize(self.cache_file) / (1024 * 1024)
        
        return {
            'model_name': self.model_name,
            'dimension': self.dimension,
            'cached_embeddings': len(self.cache),
            'cache_size_mb': round(cache_size_mb, 2),
            'legal_terms_count': len(self.legal_terms)
        }

    def clear_cache(self):
        """Clear cache"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        logger.info("🗑️ Cache cleared")

# Alias
EmbeddingModel = VietnameseEmbeddingModel