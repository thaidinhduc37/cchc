# server/services/vector_rag/lightweight_embeddings.py
"""
Embedding siêu nhẹ thay thế HuggingFaceEmbeddings
Tối ưu cho văn bản pháp lý tiếng Việt
"""
import os
import pickle
import hashlib
from typing import List, Optional, Dict, Any
import logging

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# Thay đổi import ở đầu file:
from .lightweight_config import EMBEDDING_CONFIG, SYSTEM_CONFIG

logger = logging.getLogger(__name__)

class LightweightEmbeddings:
    """
    Embedding siêu nhẹ với cache thông minh
    RAM usage: ~50MB thay vì 500MB+
    """
    
    def __init__(self, config=None):
        self.config = config or EMBEDDING_CONFIG
        self.model = None
        self.cache_file = os.path.join(SYSTEM_CONFIG.cache_path, "embeddings_cache.pkl")
        self.cache = self._load_cache()
        
        # Initialize model
        self._initialize_model()
    
    def _initialize_model(self):
        """Khởi tạo model embedding"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers không có. Cài đặt: pip install sentence-transformers"
            )
        
        try:
            logger.info(f"🔄 Loading embedding model: {self.config.model_name}")
            
            # Download model nếu cần
            self.model = SentenceTransformer(
                self.config.model_name,
                device=self.config.device
            )
            
            # Set max sequence length
            if hasattr(self.model, 'max_seq_length'):
                self.model.max_seq_length = self.config.max_length
            
            logger.info(f"✅ Embedding model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise
    
    def _load_cache(self) -> Dict[str, np.ndarray]:
        """Load embedding cache từ disk"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    cache = pickle.load(f)
                logger.info(f"📂 Loaded {len(cache)} cached embeddings")
                return cache
        except Exception as e:
            logger.warning(f"⚠️ Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """Lưu embedding cache xuống disk"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
            logger.debug(f"💾 Saved {len(self.cache)} embeddings to cache")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save cache: {e}")
    
    def _get_cache_key(self, text: str) -> str:
        """Tạo cache key từ text"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple documents với cache thông minh
        """
        if not texts:
            return []
        
        embeddings = []
        texts_to_embed = []
        cache_keys = []
        
        # Check cache trước
        for text in texts:
            cache_key = self._get_cache_key(text)
            cache_keys.append(cache_key)
            
            if self.config.cache_embeddings and cache_key in self.cache:
                embeddings.append(self.cache[cache_key].tolist())
                texts_to_embed.append(None)  # Placeholder
            else:
                embeddings.append(None)  # Placeholder
                texts_to_embed.append(text)
        
        # Embed những text chưa có trong cache
        new_texts = [t for t in texts_to_embed if t is not None]
        if new_texts:
            logger.info(f"🔄 Embedding {len(new_texts)} new texts...")
            
            try:
                # Batch embedding để tối ưu
                new_embeddings = self.model.encode(
                    new_texts,
                    batch_size=self.config.batch_size,
                    convert_to_tensor=False,
                    show_progress_bar=len(new_texts) > 10
                )
                
                # Update cache và results
                new_idx = 0
                for i, text in enumerate(texts_to_embed):
                    if text is not None:
                        embedding = new_embeddings[new_idx]
                        embeddings[i] = embedding.tolist()
                        
                        # Add to cache
                        if self.config.cache_embeddings:
                            self.cache[cache_keys[i]] = embedding
                        
                        new_idx += 1
                
                # Save cache
                if self.config.cache_embeddings and new_texts:
                    self._save_cache()
                    
            except Exception as e:
                logger.error(f"❌ Embedding failed: {e}")
                raise
        
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed single query text"""
        return self.embed_documents([text])[0]
    
    def clear_cache(self):
        """Xóa cache embeddings"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        logger.info("🗑️ Embedding cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Thống kê cache"""
        cache_size_mb = 0
        if os.path.exists(self.cache_file):
            cache_size_mb = os.path.getsize(self.cache_file) / 1024 / 1024
        
        return {
            'cached_embeddings': len(self.cache),
            'cache_size_mb': round(cache_size_mb, 2),
            'cache_enabled': self.config.cache_embeddings,
            'model_name': self.config.model_name
        }

class FallbackEmbeddings:
    """
    Fallback embedding đơn giản nếu sentence-transformers không có
    Dùng TF-IDF hoặc word2vec cơ bản
    """
    
    def __init__(self):
        logger.warning("⚠️ Using fallback embeddings (TF-IDF based)")
        
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Simple TF-IDF based embedding"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            
            vectorizer = TfidfVectorizer(
                max_features=384,  # Match sentence-transformers dimension
                lowercase=True,
                stop_words=None  # Keep Vietnamese words
            )
            
            tfidf_matrix = vectorizer.fit_transform(texts)
            return tfidf_matrix.toarray().tolist()
            
        except ImportError:
            logger.error("❌ sklearn not available for fallback")
            # Return dummy embeddings
            return [[0.0] * 384 for _ in texts]
    
    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

def create_embeddings(config=None) -> LightweightEmbeddings:
    """Factory function để tạo embeddings phù hợp"""
    try:
        return LightweightEmbeddings(config)
    except Exception as e:
        logger.warning(f"⚠️ Failed to create LightweightEmbeddings: {e}")
        logger.warning("🔄 Falling back to simple embeddings")
        return FallbackEmbeddings()

# Test function
def test_embeddings():
    """Test embedding functionality"""
    embeddings = create_embeddings()
    
    test_texts = [
        "Người nước ngoài muốn nhập cảnh Việt Nam cần visa",
        "Thủ tục xin cấp hộ chiếu mới",
        "Quy định về thời hạn cư trú tạm thời"
    ]
    
    print("🧪 Testing embeddings...")
    results = embeddings.embed_documents(test_texts)
    
    print(f"✅ Embedded {len(results)} texts")
    print(f"📊 Embedding dimension: {len(results[0])}")
    print(f"💾 Cache stats: {embeddings.get_cache_stats()}")
    
    return results

# if __name__ == "__main__":
#     test_embeddings()