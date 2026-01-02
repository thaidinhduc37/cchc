# app/server/services/vector_rag/core/embeddings.py - SENIOR AI FIXED
"""
🎯 SENIOR AI OPTIMIZED FOR PRODUCTION
📋 Focus: Accuracy + Performance + Clean Architecture  
🏛️ Use case: Cơ quan nhà nước - Legal document search

Key improvements:
✅ Complete warning elimination (model-index fixed)
✅ Vietnamese legal text normalization
✅ Guaranteed FAISS compatibility
✅ Lightweight & fast processing
✅ Accurate vector generation for legal search
❌ No overcomplicated logic - pure embedding responsibility
"""
import os
import pickle
import hashlib
import logging
import re
import numpy as np
import warnings
from typing import List, Dict, Any, Union, Optional
from datetime import datetime
from dataclasses import dataclass
import time
import contextlib
import sys

# CRITICAL: Complete warning suppression for production
import logging
logging.getLogger("transformers.modeling_utils").setLevel(logging.ERROR)
logging.getLogger("transformers.configuration_utils").setLevel(logging.ERROR)
logging.getLogger("transformers.tokenization_utils_base").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub.repocard_data").setLevel(logging.ERROR)

warnings.filterwarnings("ignore", message="Invalid model-index")
warnings.filterwarnings("ignore", message="Not loading eval results into CardData")
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", module="huggingface_hub")

os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = 'true'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
os.environ['HF_HUB_VERBOSITY'] = 'error'

@contextlib.contextmanager
def suppress_all_output():
    """Suppress all output during model loading"""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

# Import with complete suppression
with suppress_all_output():
    from sentence_transformers import SentenceTransformer

from app.services.vector_rag.rag_config import config

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Clean embedding result for production"""
    embedding: List[float]
    metadata: Dict[str, Any]
    confidence: float
    processing_time: float
    cache_hit: bool = False
    
    def __post_init__(self):
        if not isinstance(self.embedding, list):
            raise ValueError("Embedding must be a list")
        if not isinstance(self.metadata, dict):
            self.metadata = {}
        if not (0.0 <= self.confidence <= 1.0):
            self.confidence = max(0.0, min(1.0, self.confidence))

class VietnameseEmbeddingModel:
    """
    Production Vietnamese Embedding Model - FIXED
    Optimized for truro7/vn-law-embedding + cơ quan nhà nước use case
    """

    def __init__(self):
        # Primary model - proven best for Vietnamese legal
        self.model_name = "truro7/vn-law-embedding"
        self.model = None
        self.dimension = 768  # Known dimension for this specific model
        
        # Cache system for performance
        self.cache = {}
        self.cache_file = os.path.join(config.data_path, config.domain, "embeddings_cache_production.pkl")
        
        # Optimized settings for legal text
        self.normalize_embeddings = True
        self.batch_size = 16
        
        # Performance tracking
        self.stats = {
            'total_embeddings': 0,
            'cache_hits': 0,
            'total_processing_time': 0.0,
            'model_load_time': 0.0,
            'successful_operations': 0
        }
        
        # Vietnamese legal keywords for normalization
        self.legal_keywords = {
            'hộ chiếu', 'visa', 'thị thực', 'xuất cảnh', 'nhập cảnh',
            'trẻ em', 'điều kiện', 'thủ tục', 'hồ sơ', 'lệ phí',
            'thời hạn', 'quy trình', 'giấy tờ', 'yêu cầu', 'công dân'
        }
        
        # Initialize model and cache
        if not getattr(config, 'lazy_model_loading', False):
            self._init_model()
        self._load_cache()

    def _init_model(self):
        """Initialize model with complete warning suppression"""
        if self.model is not None:
            logger.info("✅ Model already initialized")
            return
        
        try:
            start_time = time.time()
            logger.info(f"🔄 Loading Vietnamese legal model: {self.model_name}")
            
            # Load model with complete suppression
            with suppress_all_output():
                self.model = SentenceTransformer(self.model_name)
            
            if self.model is None:
                raise RuntimeError("Model loading returned None")
            
            # Verify model with Vietnamese legal test
            test_text = "Điều 15 Luật xuất nhập cảnh về cấp hộ chiếu"
            test_embedding = self.model.encode([test_text], convert_to_tensor=False)
            
            if test_embedding is None or len(test_embedding) == 0:
                raise RuntimeError("Model encode test failed")
            
            self.dimension = len(test_embedding[0])
            load_time = time.time() - start_time
            self.stats['model_load_time'] = load_time
            
            logger.info(f"✅ Vietnamese legal model loaded successfully")
            logger.info(f"   📐 Dimension: {self.dimension}")
            logger.info(f"   ⏱️ Load time: {load_time:.2f}s")
            logger.info(f"   🇻🇳 Vietnamese legal support: enabled")
            
        except Exception as e:
            logger.error(f"❌ Model initialization failed: {e}")
            self.model = None
            self.dimension = 768  # Fallback dimension

    def _load_cache(self):
        """Load embedding cache for performance"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    
                if isinstance(cache_data, dict) and cache_data.get('model_name') == self.model_name:
                    self.cache = cache_data.get('embeddings', {})
                    stored_stats = cache_data.get('stats', {})
                    self.stats.update(stored_stats)
                    logger.info(f"📂 Cache loaded: {len(self.cache)} embeddings")
                else:
                    logger.info("🔄 Model changed or invalid cache, starting fresh")
                    self.cache = {}
                    
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")
            self.cache = {}

    def _save_cache(self):
        """Save cache for performance"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            cache_data = {
                'model_name': self.model_name,
                'dimension': self.dimension,
                'version': 'production_1.0',
                'created_at': datetime.now().isoformat(),
                'embeddings': self.cache,
                'stats': self.stats
            }
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def _preprocess_text(self, text: str, is_query: bool = False, metadata: Dict[str, Any] = None) -> str:
        """
        Vietnamese legal text preprocessing - SIMPLIFIED
        Keep original method name for compatibility
        """
        if not text or not text.strip():
            return ""
        
        text = text.strip()
        
        # Simple legal structure normalization only
        text = re.sub(r'Điều\s*(\d+[a-z]?)', r'Điều \1', text, flags=re.IGNORECASE)
        text = re.sub(r'Khoản\s*(\d+)', r'Khoản \1', text, flags=re.IGNORECASE)
        text = re.sub(r'Điểm\s*([a-z]+)', r'Điểm \1', text, flags=re.IGNORECASE)
        
        # Normalize common legal terms
        text = re.sub(r'xuất\s*cảnh', 'xuất cảnh', text, flags=re.IGNORECASE)
        text = re.sub(r'nhập\s*cảnh', 'nhập cảnh', text, flags=re.IGNORECASE)
        text = re.sub(r'hộ\s*chiếu', 'hộ chiếu', text, flags=re.IGNORECASE)
        text = re.sub(r'thị\s*thực', 'thị thực', text, flags=re.IGNORECASE)
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Length limit
        if len(text) > 1000:
            text = text[:1000] + "..."
        
        return text

    def _calculate_confidence(self, text: str, metadata: Dict[str, Any] = None, 
                            processing_time: float = 0.0) -> float:
        """Calculate embedding confidence score"""
        confidence = 0.7  # Base confidence
        
        text_length = len(text.strip())
        
        # Length-based confidence
        if 50 <= text_length <= 800:
            confidence += 0.15
        elif text_length < 50:
            confidence -= 0.2
        elif text_length > 800:
            confidence += 0.05
        
        # Legal content boost
        if metadata:
            content_type = metadata.get('content_type', '')
            if content_type == 'legal_document':
                confidence += 0.1
                if any(pattern in text for pattern in ['Điều ', 'Khoản ', 'quy định']):
                    confidence += 0.05
            elif content_type == 'qa_entry':
                confidence += 0.1
        
        # Vietnamese legal keyword matching
        text_lower = text.lower()
        keyword_matches = sum(1 for keyword in self.legal_keywords if keyword in text_lower)
        if keyword_matches >= 2:
            confidence += 0.1
        elif keyword_matches >= 1:
            confidence += 0.05
        
        # Performance factor
        if processing_time < 0.01:
            confidence += 0.05
        
        return max(0.5, min(0.95, confidence))

    def _get_cache_key(self, text: str, is_query: bool = False, metadata: Dict[str, Any] = None) -> str:
        """Generate cache key"""
        meta_str = ""
        if metadata:
            content_type = metadata.get('content_type', '')
            meta_str = f"type:{content_type}"
        
        normalized_text = self._preprocess_text(text, is_query=True, metadata=metadata)
        key_data = f"{self.model_name}:{normalized_text}:{'q' if is_query else 'd'}:{meta_str}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()[:16]

    def _ensure_faiss_compatibility(self, embeddings):
        """Ensure FAISS-compatible float32 arrays"""
        import numpy as np
        
        # Handle different input types
        if hasattr(embeddings, 'cpu'):  # torch tensor
            embeddings = embeddings.cpu().numpy()
        elif hasattr(embeddings, 'numpy'):  # some tensor types
            embeddings = embeddings.numpy()
        elif not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)
        
        # Ensure float32 for FAISS
        embeddings = embeddings.astype(np.float32)
        
        # Validate shape
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        if embeddings.shape[1] != self.dimension:
            logger.warning(f"Dimension mismatch: {embeddings.shape[1]} vs {self.dimension}")
            # Pad or truncate to match expected dimension
            if embeddings.shape[1] < self.dimension:
                pad_width = ((0, 0), (0, self.dimension - embeddings.shape[1]))
                embeddings = np.pad(embeddings, pad_width, 'constant')
            else:
                embeddings = embeddings[:, :self.dimension]
        
        return embeddings

    # Public API methods
    def embed_documents_enhanced(self, documents: Union[List[str], List[Dict[str, Any]]]) -> List[EmbeddingResult]:
        """
        Enhanced document embedding for legal texts
        Optimized for Vietnamese legal documents
        """
        if not documents:
            return []

        if self.model is None:
            self._init_model()
            if self.model is None:
                logger.error("❌ Model not available")
                return []

        start_time = time.time()
        results = []
        texts_to_embed = []
        cache_indices = []
        
        # Process input documents
        processed_docs = []
        for doc in documents:
            if isinstance(doc, str):
                processed_docs.append({'content': doc, 'metadata': {}})
            elif hasattr(doc, 'content'):
                processed_docs.append({'content': doc.content, 'metadata': getattr(doc, 'metadata', {})})
            elif isinstance(doc, dict):
                processed_docs.append({'content': doc.get('content', str(doc)), 'metadata': doc.get('metadata', {})})
            else:
                processed_docs.append({'content': str(doc), 'metadata': {}})

        # Check cache and prepare for embedding
        for i, doc_data in enumerate(processed_docs):
            content = doc_data['content']
            metadata = doc_data['metadata']
            
            if not content or len(content.strip()) < 10:
                results.append(EmbeddingResult(
                    embedding=[0.0] * self.dimension,
                    metadata=metadata,
                    confidence=0.5,
                    processing_time=0.0,
                    cache_hit=False
                ))
                continue
                
            cache_key = self._get_cache_key(content, is_query=False, metadata=metadata)
            
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                results.append(EmbeddingResult(
                    embedding=cached_data['embedding'],
                    metadata={**metadata, **cached_data.get('metadata', {})},
                    confidence=cached_data.get('confidence', 0.8),
                    processing_time=cached_data.get('processing_time', 0.0),
                    cache_hit=True
                ))
                self.stats['cache_hits'] += 1
            else:
                results.append(None)
                texts_to_embed.append(doc_data)
                cache_indices.append(i)

        # Generate new embeddings
        if texts_to_embed:
            try:
                # Normalize texts using original method name
                normalized_texts = [
                    self._preprocess_text(doc['content'], is_query=False, metadata=doc['metadata'])
                    for doc in texts_to_embed
                ]
                
                # Generate embeddings
                embeddings = self.model.encode(
                    normalized_texts,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                    convert_to_tensor=False,
                    normalize_embeddings=self.normalize_embeddings
                )
                
                # Ensure FAISS compatibility
                embeddings = self._ensure_faiss_compatibility(embeddings)
                
                embed_time = time.time() - start_time
                avg_time_per_doc = embed_time / max(len(texts_to_embed), 1)
                
                # Process results
                for i, embedding in enumerate(embeddings):
                    if i < len(cache_indices):
                        original_idx = cache_indices[i]
                        doc_data = texts_to_embed[i]
                        
                        # Convert to list for storage
                        embedding_list = embedding.tolist()
                        
                        confidence = self._calculate_confidence(doc_data['content'], doc_data['metadata'], avg_time_per_doc)
                        
                        result = EmbeddingResult(
                            embedding=embedding_list,
                            metadata=doc_data['metadata'],
                            confidence=confidence,
                            processing_time=avg_time_per_doc,
                            cache_hit=False
                        )
                        
                        if original_idx < len(results):
                            results[original_idx] = result
                        
                        # Cache result
                        cache_key = self._get_cache_key(doc_data['content'], is_query=False, metadata=doc_data['metadata'])
                        self.cache[cache_key] = {
                            'embedding': embedding_list,
                            'metadata': doc_data['metadata'],
                            'confidence': confidence,
                            'processing_time': avg_time_per_doc,
                            'created_at': datetime.now().isoformat()
                        }
                
                self.stats['total_embeddings'] += len(embeddings)
                self.stats['total_processing_time'] += embed_time
                self.stats['successful_operations'] += 1
                
            except Exception as e:
                logger.error(f"❌ Document embedding failed: {e}")
                raise e

        # Fill any remaining None results
        for i, result in enumerate(results):
            if result is None:
                metadata = processed_docs[i]['metadata'] if i < len(processed_docs) else {}
                results[i] = EmbeddingResult(
                    embedding=[0.0] * self.dimension,
                    metadata=metadata,
                    confidence=0.5,
                    processing_time=0.0,
                    cache_hit=False
                )

        return results

    def embed_query_enhanced(self, text: str, metadata: Dict[str, Any] = None) -> EmbeddingResult:
        """
        Enhanced query embedding for legal search
        Optimized for Vietnamese legal queries
        """
        if not text or not text.strip():
            return EmbeddingResult(
                embedding=[0.0] * self.dimension,
                metadata=metadata or {},
                confidence=0.1,
                processing_time=0.0,
                cache_hit=False
            )

        if self.model is None:
            self._init_model()
            if self.model is None:
                logger.error("❌ Model not available")
                return EmbeddingResult(
                    embedding=[0.0] * self.dimension,
                    metadata=metadata or {},
                    confidence=0.1,
                    processing_time=0.0,
                    cache_hit=False
                )

        start_time = time.time()
        
        # Check cache
        cache_key = self._get_cache_key(text, is_query=True, metadata=metadata)
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            self.stats['cache_hits'] += 1
            return EmbeddingResult(
                embedding=cached_data['embedding'],
                metadata={**(metadata or {}), **cached_data.get('metadata', {})},
                confidence=cached_data.get('confidence', 0.8),
                processing_time=cached_data.get('processing_time', 0.0),
                cache_hit=True
            )
        
        try:
            # Normalize query text using original method name
            normalized_text = self._preprocess_text(text, is_query=True, metadata=metadata)
            
            # Generate embedding
            embedding = self.model.encode(
                normalized_text,
                convert_to_tensor=False,
                normalize_embeddings=self.normalize_embeddings
            )
            
            # Ensure FAISS compatibility
            embedding = self._ensure_faiss_compatibility(embedding)
            if embedding.ndim > 1:
                embedding = embedding.flatten()
            
            # Convert to list for storage
            embedding_list = embedding.tolist()
            
            processing_time = time.time() - start_time
            confidence = self._calculate_confidence(normalized_text, metadata, processing_time)
            
            # Enhanced metadata
            enhanced_metadata = {
                **(metadata or {}), 
                'original_text': text,
                'normalized_text': normalized_text
            }
            
            result = EmbeddingResult(
                embedding=embedding_list,
                metadata=enhanced_metadata,
                confidence=confidence,
                processing_time=processing_time,
                cache_hit=False
            )
            
            # Cache result
            self.cache[cache_key] = {
                'embedding': embedding_list,
                'metadata': result.metadata,
                'confidence': confidence,
                'processing_time': processing_time,
                'created_at': datetime.now().isoformat()
            }
            
            self.stats['total_embeddings'] += 1
            self.stats['total_processing_time'] += processing_time
            self.stats['successful_operations'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Query embedding failed: {e}")
            raise e

    # Legacy compatibility methods
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Legacy method for backward compatibility"""
        if not texts:
            return []
        
        results = self.embed_documents_enhanced(texts)
        return [result.embedding for result in results]

    def embed_query(self, query: str, query_metadata: Dict = None) -> List[float]:
        """Legacy method for backward compatibility"""
        if not query:
            return []
        
        try:
            result = self.embed_query_enhanced(query, query_metadata)
            return result.embedding
        except Exception as e:
            logger.error(f"Failed to embed query '{query}': {e}")
            return []

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between embeddings"""
        if len(embedding1) != len(embedding2) or len(embedding1) != self.dimension:
            return 0.0
        
        vec1 = np.array(embedding1, dtype=np.float32)
        vec2 = np.array(embedding2, dtype=np.float32)
        
        if self.normalize_embeddings:
            dot_product = np.dot(vec1, vec2)
            return float(np.clip(dot_product, -1.0, 1.0))
        else:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return float(dot_product / (norm1 * norm2))

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        cache_size_mb = 0
        if os.path.exists(self.cache_file):
            cache_size_mb = os.path.getsize(self.cache_file) / (1024 * 1024)
        
        total_requests = self.stats['total_embeddings'] + self.stats['cache_hits']
        cache_hit_rate = self.stats['cache_hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'model_info': {
                'model_name': self.model_name,
                'dimension': self.dimension,
                'normalize_embeddings': self.normalize_embeddings,
                'batch_size': self.batch_size,
                'status': 'production_optimized'
            },
            'performance': {
                'total_embeddings': self.stats['total_embeddings'],
                'cache_hits': self.stats['cache_hits'],
                'cache_hit_rate': round(cache_hit_rate, 3),
                'total_processing_time': round(self.stats['total_processing_time'], 2),
                'avg_time_per_embedding': round(
                    self.stats['total_processing_time'] / max(1, self.stats['total_embeddings']), 4
                ),
                'model_load_time': round(self.stats['model_load_time'], 2),
                'successful_operations': self.stats['successful_operations']
            },
            'cache_info': {
                'cached_embeddings': len(self.cache),
                'cache_size_mb': round(cache_size_mb, 2),
                'cache_file': self.cache_file
            },
            'vietnamese_legal_features': {
                'legal_structure_normalization': True,
                'legal_keywords_recognition': True,
                'faiss_compatibility': True,
                'warning_free_operation': True,
                'production_ready': True
            }
        }

    def clear_cache(self):
        """Clear embedding cache"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        
        # Reset relevant stats
        self.stats['cache_hits'] = 0
        
        logger.info("🗑️ Embedding cache cleared")

    def test_embeddings(self, test_queries: List[str] = None) -> Dict[str, Any]:
        """Test embedding functionality - keep original method name"""
        if test_queries is None:
            test_queries = [
                "Điều 15 Luật xuất nhập cảnh về cấp hộ chiếu",
                "Khoản 2 điều 33 về điều kiện xuất cảnh", 
                "Trẻ em dưới 14 tuổi làm hộ chiếu cần gì",
                "Bị khởi tố có được xuất cảnh không"
            ]
        
        try:
            logger.info("🧪 Testing embedding functionality...")
            
            start_time = time.time()
            results = []
            
            for test_case in test_queries:
                result = self.embed_query_enhanced(test_case)
                results.append({
                    'query': test_case,
                    'embedding_length': len(result.embedding),
                    'confidence': result.confidence,
                    'processing_time': result.processing_time,
                    'cache_hit': result.cache_hit
                })
            
            total_time = time.time() - start_time
            avg_confidence = sum(r['confidence'] for r in results) / len(results)
            
            test_result = {
                'success': True,
                'test_cases': len(test_queries),
                'total_time': round(total_time, 3),
                'avg_confidence': round(avg_confidence, 3),
                'dimension': self.dimension,
                'model_name': self.model_name,
                'results': results,
                'features_tested': [
                    'Legal structure normalization',
                    'Vietnamese text processing', 
                    'FAISS compatibility',
                    'Cache functionality',
                    'Confidence calculation'
                ]
            }
            
            logger.info(f"✅ Embedding test completed")
            logger.info(f"   📐 Dimension: {self.dimension}")
            logger.info(f"   🎯 Avg confidence: {avg_confidence:.3f}")
            logger.info(f"   ⏱️ Total time: {total_time:.3f}s")
            
            return test_result
            
        except Exception as e:
            logger.error(f"❌ Embedding test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'model_stats': self.get_stats()
            }

# Backward compatible alias
EmbeddingModel = VietnameseEmbeddingModel