# server/services/vector_rag/embeddings.py - IMPROVED VERSION
"""
🎓 VIETNAMESE EMBEDDING ENGINE - Logic cải tiến từ module gốc
Sửa logic: Câu hỏi pháp lý → Precise search, Câu hỏi tư vấn → Enhanced search
"""
import os
import pickle
import hashlib
import logging
import re
import numpy as np
from typing import List, Dict, Any, Union, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import time

from sentence_transformers import SentenceTransformer
from services.vector_rag.rag_config import config

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Embedding result với metadata mở rộng"""
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
    """Enhanced Vietnamese Embedding Model với logic thông minh"""

    def __init__(self):
        self.model_name = config.embedding_model
        self.model = None
        self.cache = {}
        self.cache_file = os.path.join(config.data_path, config.domain, "embeddings_cache_enhanced.pkl")
        self.dimension = 768
        
        # Model settings cho Vietnamese legal
        self.normalize_embeddings = True
        self.batch_size = 16
        
        # SỬA LOGIC: Keywords for different query types
        self.legal_keywords = {
            'hộ chiếu', 'visa', 'thị thực', 'xuất cảnh', 'nhập cảnh',
            'trẻ em', 'điều kiện', 'thủ tục', 'hồ sơ', 'lệ phí',
            'thời hạn', 'quy trình', 'giấy tờ', 'yêu cầu'
        }
        
        # Performance tracking
        self.stats = {
            'total_embeddings': 0,
            'cache_hits': 0,
            'total_processing_time': 0.0,
            'qa_chunks_processed': 0,
            'legal_chunks_processed': 0,
            'precise_queries': 0,
            'enhanced_queries': 0
        }
        
        if getattr(config, 'lazy_model_loading', False):
            self.model = None
            logger.info("📌 Lazy loading enabled")
        else:
            self._init_model()
        self._load_cache()

    def _init_model(self):
        """Model initialization"""
        if self.model is not None:
            logger.info("Model already initialized")
            return
        
        try:
            logger.info(f"🔄 Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            
            if self.model is None:
                raise RuntimeError("SentenceTransformer returned None")
            
            # Test model với Vietnamese text
            test_embedding = self.model.encode(["làm hộ chiếu"], convert_to_tensor=False)
            if test_embedding is None or len(test_embedding) == 0:
                raise RuntimeError("Model encode test failed")
            
            self.dimension = len(test_embedding[0])
            
            logger.info(f"✅ Vietnamese legal model loaded successfully")
            logger.info(f"   📐 Dimension: {self.dimension}")
            logger.info(f"   🇻🇳 Vietnamese legal support: enabled")
            
        except Exception as e:
            logger.error(f"❌ Model initialization failed: {e}")
            self.model = None
            self.dimension = 768

    def _load_cache(self):
        """Load cache"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    cache_data = pickle.load(f)
                    
                if isinstance(cache_data, dict):
                    if cache_data.get('model_name') == self.model_name:
                        self.cache = cache_data.get('embeddings', {})
                        self.stats = {**self.stats, **cache_data.get('stats', {})}
                        logger.info(f"📂 Cache loaded: {len(self.cache)} embeddings")
                    else:
                        logger.info(f"🔄 Model changed, clearing cache...")
                        self.cache = {}
                        
        except Exception as e:
            logger.warning(f"Cache load failed: {e}")
            self.cache = {}

    def _save_cache(self):
        """Save cache"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            cache_data = {
                'model_name': self.model_name,
                'dimension': self.dimension,
                'version': 'smart_legal_1.0',
                'created_at': datetime.now().isoformat(),
                'embeddings': self.cache,
                'stats': self.stats
            }
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache_data, f)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

    def _classify_query_type(self, query: str) -> str:
        """SỬA LOGIC: Phân loại query để áp dụng processing phù hợp"""
        query_lower = query.lower()
        
        # LEGAL PRECISE: Hỏi về điều, khoản, điểm cụ thể
        legal_precise_patterns = [
            r'điều\s+\d+[a-z]?',
            r'khoản\s+\d+',
            r'điểm\s+[a-z]+',
            r'(điều|khoản|điểm).*?(nói về|quy định|là gì)'
        ]
        
        for pattern in legal_precise_patterns:
            if re.search(pattern, query_lower):
                return 'legal_precise'
        
        # PROCEDURE: Hỏi về thủ tục, quy trình
        procedure_patterns = [
            r'thủ tục.*?(như thế nào|thế nào|ra sao)',
            r'quy trình.*?(làm|cấp|xin)',
            r'làm.*?(hộ chiếu|thị thực|giấy tờ)',
            r'cần.*?(gì|những gì|điều kiện)',
            r'hồ sơ.*?(gồm|bao gồm)'
        ]
        
        for pattern in procedure_patterns:
            if re.search(pattern, query_lower):
                return 'procedure'
        
        # CONSULTATION: Hỏi tư vấn điều kiện, được phép
        consultation_patterns = [
            r'có.*?được.*?không',
            r'được phép.*?không',
            r'điều kiện.*?để',
            r'trường hợp.*?nào',
            r'có thể.*?không'
        ]
        
        for pattern in consultation_patterns:
            if re.search(pattern, query_lower):
                return 'consultation'
        
        return 'general'

    def _preprocess_for_legal_precise(self, text: str) -> str:
        """Xử lý cho câu hỏi pháp lý chính xác - MINIMAL processing"""
        if not text:
            return ""
        
        text = text.strip()
        
        # CHỈ normalize cấu trúc pháp luật - KHÔNG thêm keywords
        text = re.sub(r'Điều\s*(\d+[a-z]?)', r'Điều \1', text)
        text = re.sub(r'Khoản\s*(\d+)', r'Khoản \1', text)
        text = re.sub(r'Điểm\s*([a-z]+)', r'Điểm \1', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text

    def _preprocess_for_procedure(self, text: str, is_query: bool = False) -> str:
        """Xử lý cho câu hỏi thủ tục - Enhanced processing"""
        if not text:
            return ""
        
        text = text.strip()
        
        # Normalize legal structure
        text = re.sub(r'Điều\s*(\d+[a-z]?)', r'Điều \1', text)
        text = re.sub(r'Khoản\s*(\d+)', r'Khoản \1', text)
        text = re.sub(r'\s+', ' ', text)
        
        if is_query:
            # Chỉ expand một số từ quan trọng cho procedure queries
            expansions = {
                r'\bhộ\s*chiếu\b': 'hộ chiếu passport',
                r'\bvisa\b': 'visa thị thực',
                r'\bthủ\s*tục\b': 'thủ tục quy trình',
                r'\bhồ\s*sơ\b': 'hồ sơ giấy tờ'
            }
            
            for pattern, replacement in expansions.items():
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text

    def _preprocess_for_consultation(self, text: str, is_query: bool = False) -> str:
        """Xử lý cho câu hỏi tư vấn - Moderate processing"""
        if not text:
            return ""
        
        text = text.strip()
        
        # Normalize legal structure
        text = re.sub(r'Điều\s*(\d+[a-z]?)', r'Điều \1', text)
        text = re.sub(r'Khoản\s*(\d+)', r'Khoản \1', text)
        text = re.sub(r'\s+', ' ', text)
        
        if is_query:
            # Add context cho consultation queries
            if any(indicator in text.lower() for indicator in ['có được không', 'được phép không']):
                text += ' điều kiện quy định'
        
        return text

    def _enhance_qa_content_smart(self, content: str, metadata: Dict[str, Any]) -> str:
        """SỬA LOGIC: Smart enhancement cho Q&A content"""
        if metadata.get('content_type') != 'qa_entry':
            return content  # Legal docs unchanged
        
        lines = content.split('\n')
        enhanced_parts = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('CÂU HỎI:'):
                question = line.replace('CÂU HỎI:', '').strip()
                enhanced_parts.append(line)
                
                # Chỉ thêm searchable variations cho procedure questions
                if any(word in question.lower() for word in ['thủ tục', 'quy trình', 'làm', 'cần']):
                    enhanced_parts.append(f"PROCEDURE_SEARCH: {question}")
                
            elif line.startswith('TRẢ LỜI:'):
                answer = line.replace('TRẢ LỜI:', '').strip()
                enhanced_parts.append(line)
                
                # Chỉ thêm answer content cho detailed responses
                if len(answer) > 100:
                    enhanced_parts.append(f"DETAILED_ANSWER: {answer}")
                
            else:
                enhanced_parts.append(line)
        
        return '\n'.join(enhanced_parts)

    def _preprocess_text(self, text: str, is_query: bool = False, metadata: Dict[str, Any] = None) -> str:
        """SỬA LOGIC CHÍNH: Preprocessing thông minh dựa trên query type"""
        if not text or not text.strip():
            return ""
        
        text = text.strip()
        
        # Apply Q&A enhancement for Q&A content
        if not is_query and metadata:
            text = self._enhance_qa_content_smart(text, metadata)
        
        # Apply query-specific preprocessing
        if is_query:
            query_type = self._classify_query_type(text)
            
            if query_type == 'legal_precise':
                # MINIMAL processing cho legal precise
                processed = self._preprocess_for_legal_precise(text)
                self.stats['precise_queries'] += 1
                logger.debug(f"🎯 Legal precise: {text[:30]}...")
                
            elif query_type == 'procedure':
                # ENHANCED processing cho procedure
                processed = self._preprocess_for_procedure(text, is_query=True)
                self.stats['enhanced_queries'] += 1
                logger.debug(f"🔧 Procedure: {text[:30]}...")
                
            elif query_type == 'consultation':
                # MODERATE processing cho consultation
                processed = self._preprocess_for_consultation(text, is_query=True)
                self.stats['enhanced_queries'] += 1
                logger.debug(f"💡 Consultation: {text[:30]}...")
                
            else:
                # STANDARD processing cho general
                processed = self._preprocess_for_legal_precise(text)  # Use minimal for general
                
            text = processed
        else:
            # Document processing - minimal
            text = re.sub(r'Điều\s*(\d+[a-z]?)', r'Điều \1', text)
            text = re.sub(r'Khoản\s*(\d+)', r'Khoản \1', text)
            text = re.sub(r'\s+', ' ', text)
        
        # Truncation
        if len(text) > 1200:
            text = text[:1200] + "..."
        
        return text

    def _calculate_confidence(self, text: str, metadata: Dict[str, Any] = None, 
                            processing_time: float = 0.0) -> float:
        """SỬA: Better confidence calculation"""
        confidence = 0.7  # Base confidence
        
        # Length-based confidence
        text_length = len(text.strip())
        if 100 <= text_length <= 1000:
            confidence += 0.1
        elif text_length < 100:
            confidence -= 0.15
        elif text_length > 1000:
            confidence += 0.05
        
        # Content type specific boosts
        if metadata:
            content_type = metadata.get('content_type', 'general')
            
            if content_type == 'qa_entry':
                confidence += 0.2
                if 'CÂU HỎI:' in text and 'TRẢ LỜI:' in text:
                    confidence += 0.1
                    
            elif content_type == 'legal_document':
                confidence += 0.1
                if any(pattern in text for pattern in ['Điều ', 'Khoản ', 'quy định']):
                    confidence += 0.05
                if metadata.get('law_unit'):
                    confidence += 0.05
        
        # Enhanced keyword matching
        text_lower = text.lower()
        keyword_matches = sum(1 for keyword in self.legal_keywords if keyword in text_lower)
        
        if keyword_matches >= 3:
            confidence += 0.15
        elif keyword_matches >= 2:
            confidence += 0.1
        elif keyword_matches >= 1:
            confidence += 0.05
        
        # Processing time factor
        if processing_time < 0.01:
            confidence += 0.05
        
        return max(0.4, min(0.98, confidence))

    def _get_cache_key(self, text: str, is_query: bool = False, metadata: Dict[str, Any] = None) -> str:
        """Cache key generation"""
        meta_str = ""
        if metadata:
            content_type = metadata.get('content_type', '')
            meta_str = f"type:{content_type}"
        
        # Include query type in cache key for queries
        if is_query:
            query_type = self._classify_query_type(text)
            meta_str += f":qtype:{query_type}"
        
        preprocessed = self._preprocess_text(text, is_query, metadata)
        key_data = f"{self.model_name}:{preprocessed}:{'q' if is_query else 'd'}:{meta_str}"
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()[:16]

    # Backward compatible methods
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Original document embedding method"""
        if not texts:
            return []
        
        results = self.embed_documents_enhanced(texts)
        return [result.embedding for result in results]

    def embed_query(self, query: str, query_metadata: Dict = None) -> List[float]:
        """Query embedding"""
        if not query:
            return []
        
        try:
            result = self.embed_query_enhanced(query, query_metadata)
            return result.embedding
        except Exception as e:
            logger.error(f"Failed to embed query '{query}': {e}")
            return []

    def embed_documents_enhanced(self, documents: Union[List[str], List[Dict[str, Any]]]) -> List[EmbeddingResult]:
        """FIXED: Enhanced document embedding với FAISS compatibility"""
        if not documents:
            return []

        if self.model is None:
            self._init_model()

        start_time = time.time()
        results = []
        texts_to_embed = []
        cache_indices = []
        
        # Process input - keep existing logic
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

        # Check cache - keep existing logic
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
                preprocessed_texts = [
                    self._preprocess_text(doc['content'], is_query=False, metadata=doc['metadata'])
                    for doc in texts_to_embed
                ]
                
                embeddings = self.model.encode(
                    preprocessed_texts,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                    convert_to_tensor=False,
                    normalize_embeddings=self.normalize_embeddings
                )
                
                # CRITICAL FIX: Handle embeddings for FAISS compatibility
                import numpy as np
                
                if hasattr(embeddings, 'cpu'):  # torch tensor
                    embeddings = embeddings.cpu().numpy()
                elif hasattr(embeddings, 'numpy'):  # some tensor types
                    embeddings = embeddings.numpy()
                elif not isinstance(embeddings, np.ndarray):
                    embeddings = np.array(embeddings)
                
                # ENSURE float32 for FAISS
                embeddings = embeddings.astype(np.float32)
                
                # Validate shape
                if embeddings.ndim != 2 or embeddings.shape[1] != self.dimension:
                    logger.warning(f"Embeddings shape issue: {embeddings.shape}, expected: (N, {self.dimension})")
                    # Fix shape if needed
                    if embeddings.ndim == 1:
                        embeddings = embeddings.reshape(1, -1)
                    if embeddings.shape[1] != self.dimension:
                        if embeddings.shape[1] < self.dimension:
                            # Pad
                            pad_width = ((0, 0), (0, self.dimension - embeddings.shape[1]))
                            embeddings = np.pad(embeddings, pad_width, 'constant')
                        else:
                            # Truncate
                            embeddings = embeddings[:, :self.dimension]
                
                embed_time = time.time() - start_time
                avg_time_per_doc = embed_time / max(len(texts_to_embed), 1)
                
                # Process results
                for i, embedding in enumerate(embeddings):
                    if i < len(cache_indices):
                        original_idx = cache_indices[i]
                        doc_data = texts_to_embed[i]
                        
                        # Convert embedding to list for storage
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
                        
                        # Update stats based on content type
                        content_type = doc_data['metadata'].get('content_type', 'general')
                        if content_type == 'qa_entry':
                            self.stats['qa_chunks_processed'] += 1
                        else:
                            self.stats['legal_chunks_processed'] += 1
                
                self.stats['total_embeddings'] += len(embeddings)
                self.stats['total_processing_time'] += embed_time
                
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
        """FIXED: Enhanced query embedding với FAISS compatibility"""
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

        start_time = time.time()
        
        # Smart cache key includes query type
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
            # SMART: Better preprocessing for queries based on type
            preprocessed = self._preprocess_text(text, is_query=True, metadata=metadata)
            
            embedding = self.model.encode(
                preprocessed,
                convert_to_tensor=False,
                normalize_embeddings=self.normalize_embeddings
            )
            
            # CRITICAL FIX: Ensure FAISS-compatible data type
            import numpy as np
            
            # Handle different return types from SentenceTransformer
            if hasattr(embedding, 'cpu'):  # torch tensor
                embedding = embedding.cpu().numpy()
            elif hasattr(embedding, 'numpy'):  # some tensor types
                embedding = embedding.numpy()
            elif not isinstance(embedding, np.ndarray):
                embedding = np.array(embedding)
            
            # ENSURE float32 for FAISS compatibility
            embedding = embedding.astype(np.float32)
            
            # Flatten if needed
            if embedding.ndim > 1:
                embedding = embedding.flatten()
            
            # Validate dimension
            if len(embedding) != self.dimension:
                logger.warning(f"Embedding dimension mismatch: {len(embedding)} vs expected {self.dimension}")
                # Pad or truncate to match expected dimension
                if len(embedding) < self.dimension:
                    embedding = np.pad(embedding, (0, self.dimension - len(embedding)), 'constant')
                else:
                    embedding = embedding[:self.dimension]
            
            # Convert to list for JSON serialization and storage
            embedding_list = embedding.tolist()
            
            processing_time = time.time() - start_time
            confidence = self._calculate_confidence(preprocessed, metadata, processing_time)
            
            # Include query type info
            query_type = self._classify_query_type(text)
            enhanced_metadata = {
                **(metadata or {}), 
                'query_type': query_type,
                'original_text': text,
                'preprocessed_text': preprocessed
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
                'created_at': datetime.now().isoformat(),
                'query_type': query_type
            }
            
            self.stats['total_embeddings'] += 1
            self.stats['total_processing_time'] += processing_time
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Enhanced query embedding failed: {e}")
            raise e

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity"""
        if len(embedding1) != len(embedding2) or len(embedding1) != self.dimension:
            return 0.0
        
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
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
        """Get enhanced statistics"""
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
                'approach': 'Smart adaptive preprocessing'
            },
            'performance': {
                'total_embeddings': self.stats['total_embeddings'],
                'cache_hits': self.stats['cache_hits'],
                'cache_hit_rate': round(cache_hit_rate, 3),
                'total_processing_time': round(self.stats['total_processing_time'], 2),
                'avg_time_per_embedding': round(
                    self.stats['total_processing_time'] / max(1, self.stats['total_embeddings']), 4
                )
            },
            'query_breakdown': {
                'precise_queries': self.stats['precise_queries'],
                'enhanced_queries': self.stats['enhanced_queries'],
                'precise_ratio': round(self.stats['precise_queries'] / max(1, total_requests), 2),
                'enhanced_ratio': round(self.stats['enhanced_queries'] / max(1, total_requests), 2)
            },
            'content_breakdown': {
                'qa_chunks_processed': self.stats['qa_chunks_processed'],
                'legal_chunks_processed': self.stats['legal_chunks_processed'],
                'qa_ratio': round(self.stats['qa_chunks_processed'] / max(1, self.stats['total_embeddings']), 2)
            },
            'cache_info': {
                'cached_embeddings': len(self.cache),
                'cache_size_mb': round(cache_size_mb, 2),
                'cache_file': self.cache_file
            },
            'features': {
                'smart_preprocessing': True,
                'adaptive_query_handling': True,
                'legal_precise_support': True,
                'procedure_enhancement': True,
                'consultation_support': True,
                'docx_qa_support': True,
                'legal_structure_preservation': True
            }
        }

    def clear_cache(self):
        """Clear cache"""
        self.cache = {}
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        
        # Reset stats
        self.stats['cache_hits'] = 0
        self.stats['total_embeddings'] = 0
        self.stats['qa_chunks_processed'] = 0
        self.stats['legal_chunks_processed'] = 0
        self.stats['precise_queries'] = 0
        self.stats['enhanced_queries'] = 0
        self.stats['total_processing_time'] = 0.0
        
        logger.info("🗑️ Embedding cache cleared")

    # Legacy methods
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Legacy alias"""
        return self.embed_documents(texts)
    
    def embed_single(self, text: str) -> List[float]:
        """Legacy alias"""
        return self.embed_query(text)

    def test_embeddings(self, test_queries: List[str] = None) -> Dict[str, Any]:
        """Test smart embedding functionality"""
        if test_queries is None:
            test_queries = [
                "Khoản 2 điều 15 Luật xuất nhập cảnh nói về cái gì",  # legal_precise
                "Thủ tục cấp hộ chiếu thế nào",                      # procedure
                "Tôi bị nợ thuế có xuất cảnh được không",            # consultation
                "Trẻ em tự đi nước ngoài như thế nào"                # procedure
            ]
        
        try:
            logger.info("🧪 Testing smart embeddings...")
            
            # Test query classification
            query_types = []
            for query in test_queries:
                query_type = self._classify_query_type(query)
                query_types.append(query_type)
                logger.info(f"'{query[:30]}...' → {query_type}")
            
            # Test embeddings
            query_results = [self.embed_query_enhanced(query) for query in test_queries]
            
            # Test documents with metadata
            test_documents = [
                {
                    'content': 'CÂU HỎI: Quy trình làm hộ chiếu như thế nào?\n\nTRẢ LỜI: Để làm hộ chiếu phổ thông cần thực hiện...',
                    'metadata': {
                        'content_type': 'qa_entry',
                        'qa_id': 'passport_001'
                    }
                },
                {
                    'content': '[Luật 49-2019] Điều 15. Tạm hoãn xuất cảnh\n\nKhoản 2. Công dân Việt Nam bị tạm hoãn xuất cảnh...',
                    'metadata': {
                        'content_type': 'legal_document',
                        'article_number': '15',
                        'law_unit': '15.2'
                    }
                }
            ]
            
            doc_results = self.embed_documents_enhanced(test_documents)
            
            # Calculate similarities
            similarities = []
            for i, q_result in enumerate(query_results):
                if i < len(doc_results):
                    sim = self.calculate_similarity(q_result.embedding, doc_results[i].embedding)
                    similarities.append(sim)
            
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0
            avg_confidence = sum(r.confidence for r in query_results + doc_results) / len(query_results + doc_results)
            
            result = {
                'success': True,
                'test_queries': test_queries,
                'query_types': query_types,
                'results': {
                    'query_embeddings': len(query_results),
                    'doc_embeddings': len(doc_results),
                    'embedding_dimension': self.dimension,
                    'average_similarity': round(avg_similarity, 3),
                    'average_confidence': round(avg_confidence, 3),
                    'cache_hits': sum(1 for r in query_results + doc_results if r.cache_hit)
                },
                'smart_features': {
                    'query_classification': True,
                    'adaptive_preprocessing': True,
                    'legal_precise_handling': 'legal_precise' in query_types,
                    'procedure_enhancement': 'procedure' in query_types,
                    'consultation_support': 'consultation' in query_types
                },
                'model_stats': self.get_stats()
            }
            
            logger.info(f"✅ Smart embedding test completed")
            logger.info(f"   📐 Dimension: {result['results']['embedding_dimension']}")
            logger.info(f"   📊 Avg similarity: {result['results']['average_similarity']}")
            logger.info(f"   🎯 Avg confidence: {result['results']['average_confidence']}")
            logger.info(f"   🧠 Query types: {set(query_types)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Embedding test failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'model_stats': self.get_stats()
            }

# Backward compatible alias
EmbeddingModel = VietnameseEmbeddingModel