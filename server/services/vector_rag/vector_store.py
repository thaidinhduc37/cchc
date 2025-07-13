# server/services/vector_rag/vector_store.py - IMPROVED VERSION
"""
Vector Store - SMART: Tìm kiếm thông minh dựa trên query type
Legal precise → Exact matching, Procedure → Enhanced search
"""
import os
import pickle
import asyncio
import time
import re
from typing import List, Dict, Any, Optional, Set, Tuple
import logging
from datetime import datetime
import numpy as np
from pathlib import Path

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("FAISS not available")

from services.vector_rag.rag_config import config
from services.vector_rag.document_processor import DocumentProcessor, Document
from services.vector_rag.embeddings import VietnameseEmbeddingModel

logger = logging.getLogger(__name__)

class VectorBuilder:
    """🔨 Enhanced builder - giữ nguyên từ module gốc"""
    
    def __init__(self):
        self.documents_path = config.documents_path
        self.embedding_model = VietnameseEmbeddingModel()
        self.storage_path = config.vector_store_path
        
        # File paths
        self.docs_file = os.path.join(self.storage_path, "documents.pkl")
        self.meta_file = os.path.join(self.storage_path, "metadata.pkl")
        self.index_file = os.path.join(self.storage_path, "faiss_index.bin")
        
        logger.info("VectorBuilder initialized - enhanced mode")
    
    async def build_from_directory(self, documents_path: str = None) -> Dict[str, Any]:
        """Enhanced build từ directory"""
        try:
            processor = DocumentProcessor()
            
            if documents_path:
                logger.info(f"Building from {documents_path}")
                documents = processor.process_directory(documents_path)
            else:
                logger.info(f"Building from documents directory")
                documents = processor.process_directory(config.documents_path)
            
            if not documents:
                return {'success': False, 'message': 'No documents processed'}
            
            return await self.build_from_documents(documents)
            
        except Exception as e:
            logger.error(f"Build from directory failed: {e}")
            return {'success': False, 'message': f'Build failed: {str(e)}'}
    
    async def build_from_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """Build process - simple and reliable"""
        if not documents:
            return {'success': False, 'message': 'No documents provided'}
        
        try:
            logger.info(f"Building vector database from {len(documents)} documents")
            
            # Process documents
            contents = []
            metadatas = []
            qa_count = 0
            legal_count = 0
            law_units_found = []
            
            for i, doc in enumerate(documents):
                if not doc or not hasattr(doc, 'content') or not doc.content:
                    logger.warning(f"Document {i} is invalid - skipping")
                    continue
                    
                content = doc.content.strip()
                metadata = getattr(doc, 'metadata', {})
                
                if len(content) > 10:
                    contents.append(content)
                    metadatas.append(metadata)
                    
                    # Count content types
                    content_type = metadata.get('content_type', 'unknown')
                    if content_type == 'qa_entry':
                        qa_count += 1
                    elif content_type == 'legal_document':
                        legal_count += 1
                        law_unit = metadata.get('law_unit')
                        if law_unit:
                            law_units_found.append(law_unit)
                else:
                    logger.warning(f"Document {i} too short: {len(content)} chars")
            
            if not contents:
                return {'success': False, 'message': 'No valid content after filtering'}
            
            logger.info(f"Content validation: {len(contents)}/{len(documents)} documents are valid")
            logger.info(f"   Q&A entries: {qa_count}")
            logger.info(f"   Legal documents: {legal_count}")
            logger.info(f"   Law units found: {len(law_units_found)}")
            
            # Embedding generation
            logger.info(f"Generating embeddings for {len(contents)} chunks")
            embeddings = self.embedding_model.embed_documents(contents)
            
            if not embeddings or len(embeddings) != len(contents):
                logger.error(f"Embedding mismatch: {len(embeddings)} embeddings for {len(contents)} contents")
                return {'success': False, 'message': 'Embedding generation failed'}
            
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            
            # Build FAISS index
            logger.info(f"Building FAISS index")
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            if FAISS_AVAILABLE:
                faiss.normalize_L2(embeddings_array)
                dimension = embeddings_array.shape[1]
                index = faiss.IndexFlatIP(dimension)
                index.add(embeddings_array)
                logger.info(f"FAISS index built: {index.ntotal} vectors, dimension {dimension}")
            else:
                index = None
                dimension = len(embeddings[0]) if embeddings else 768
                logger.warning("FAISS not available - using fallback")
            
            # Save
            logger.info(f"Saving vector database")
            os.makedirs(self.storage_path, exist_ok=True)
            
            # Atomic saves
            temp_suffix = '.tmp'
            
            try:
                # Save documents
                with open(self.docs_file + temp_suffix, 'wb') as f:
                    pickle.dump(contents, f)
                os.replace(self.docs_file + temp_suffix, self.docs_file)
                
                # Save metadata
                with open(self.meta_file + temp_suffix, 'wb') as f:
                    pickle.dump(metadatas, f)
                os.replace(self.meta_file + temp_suffix, self.meta_file)
                
                # Save FAISS index
                if index and FAISS_AVAILABLE:
                    faiss.write_index(index, self.index_file + temp_suffix)
                    os.replace(self.index_file + temp_suffix, self.index_file)
                
            except Exception as e:
                # Cleanup temp files
                for temp_file in [self.docs_file + temp_suffix, self.meta_file + temp_suffix, 
                                self.index_file + temp_suffix]:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                raise e
            
            # Stats
            stats = {
                'total_documents': len(contents),
                'qa_entries': qa_count,
                'legal_documents': legal_count,
                'law_units_found': len(law_units_found),
                'vectors': index.ntotal if index else len(contents),
                'dimension': dimension,
                'consistency_check': {
                    'documents_count': len(contents),
                    'embeddings_count': len(embeddings),
                    'metadata_count': len(metadatas),
                    'consistent': len(contents) == len(embeddings) == len(metadatas)
                }
            }
            
            logger.info(f"Build completed successfully!")
            logger.info(f"   Documents: {stats['total_documents']}")
            logger.info(f"   Vectors: {stats['vectors']}")
            logger.info(f"   Q&A entries: {stats['qa_entries']}")
            logger.info(f"   Legal documents: {stats['legal_documents']}")
            logger.info(f"   Law units: {stats['law_units_found']}")
            
            return {
                'success': True,
                'message': f'Built vector database with {stats["total_documents"]} documents',
                'stats': stats
            }
            
        except Exception as e:
            logger.error(f"Build failed: {e}")
            return {'success': False, 'message': f'Build failed: {str(e)}'}

class VectorSearcher:
    """🔍 SMART search với logic thông minh dựa trên query type"""
    
    def __init__(self):
        self.embedding_model = VietnameseEmbeddingModel()
        self.storage_path = config.vector_store_path
        
        # Runtime data
        self.documents = []
        self.metadatas = []
        self.faiss_index = None
        
        # File paths
        self.docs_file = os.path.join(self.storage_path, "documents.pkl")
        self.meta_file = os.path.join(self.storage_path, "metadata.pkl")
        self.index_file = os.path.join(self.storage_path, "faiss_index.bin")
        
        # SMART search thresholds - điều chỉnh theo query type
        self.thresholds = {
            'legal_precise': 0.1,    # Cao hơn cho legal precise
            'procedure': 0.2,        # Thấp hơn cho procedure
            'consultation': 0.25,    # Trung bình cho consultation
            'general': 0.2           # Thấp cho general
        }
        
        self.qa_boost = 1.2         # Giảm boost, không quá aggressive
        self.enhanced_mode = True
        
        # Smart search stats
        self.stats = {
            'total_searches': 0,
            'avg_search_time': 0.0,
            'legal_precise_searches': 0,
            'procedure_searches': 0,
            'consultation_searches': 0,
            'qa_matches': 0,
            'legal_matches': 0
        }
        
        logger.info("VectorSearcher initialized with smart capabilities")
    
    async def initialize(self) -> Dict[str, Any]:
        """Load vector database for search"""
        try:
            # Load documents
            if os.path.exists(self.docs_file):
                with open(self.docs_file, 'rb') as f:
                    self.documents = pickle.load(f)
            
            # Load metadata
            if os.path.exists(self.meta_file):
                with open(self.meta_file, 'rb') as f:
                    self.metadatas = pickle.load(f)
            
            # Load FAISS index
            if os.path.exists(self.index_file) and FAISS_AVAILABLE:
                self.faiss_index = faiss.read_index(self.index_file)
            
            # Ensure consistency
            if len(self.metadatas) < len(self.documents):
                while len(self.metadatas) < len(self.documents):
                    self.metadatas.append({})
            elif len(self.metadatas) > len(self.documents):
                self.metadatas = self.metadatas[:len(self.documents)]
            
            total_docs = len(self.documents)
            total_vectors = self.faiss_index.ntotal if self.faiss_index else 0
            
            if total_docs == 0:
                return {'success': False, 'message': 'No documents in vector database'}
            
            # Count document types
            qa_count = sum(1 for meta in self.metadatas if meta.get('content_type') == 'qa_entry')
            legal_count = total_docs - qa_count
            
            logger.info(f"✅ Smart loaded: {total_docs} docs ({qa_count} Q&A, {legal_count} legal), {total_vectors} vectors")
            
            return {
                'success': True,
                'message': f'Smart vector database ready: {total_docs} docs',
                'stats': {
                    'documents': total_docs,
                    'vectors': total_vectors,
                    'qa_entries': qa_count,
                    'legal_docs': legal_count,
                    'smart_features': {
                        'adaptive_thresholds': True,
                        'query_type_detection': True,
                        'content_priority': True
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Smart initialize failed: {e}")
            return {'success': False, 'message': f"Initialize failed: {e}"}

    async def _legal_precise_search(self, query: str, k: int) -> List[Dict]:
        """FIXED: Legal precise search với FAISS compatibility"""
        try:
            # Embed query
            query_embedding = self.embedding_model.embed_query(query)
            if not query_embedding:
                return []
            
            # CRITICAL FIX: Prepare query vector for FAISS
            import numpy as np
            
            # Convert to numpy array with correct dtype
            query_vector = np.array(query_embedding, dtype=np.float32)
            
            # Ensure proper shape for FAISS (must be 2D)
            if query_vector.ndim == 1:
                query_vector = query_vector.reshape(1, -1)
            
            # Ensure contiguous array for FAISS
            query_vector = np.ascontiguousarray(query_vector)
            
            # FIXED: Only normalize if model doesn't do it automatically
            if not self.embedding_model.normalize_embeddings:
                import faiss
                # Make a copy to avoid modifying original
                query_vector_norm = query_vector.copy()
                faiss.normalize_L2(query_vector_norm)
                query_vector = query_vector_norm
            
            # Search with FAISS
            search_k = min(k * 3, self.faiss_index.ntotal)
            similarities, indices = self.faiss_index.search(query_vector, search_k)
            
            results = []
            threshold = 0.15  # Lower threshold for legal precise
            
            # Extract điều/khoản từ query để exact matching
            query_lower = query.lower()
            article_match = re.search(r'điều\s+(\d+[a-z]?)', query_lower)
            paragraph_match = re.search(r'khoản\s+(\d+)', query_lower)
            point_match = re.search(r'điểm\s+([a-z]+)', query_lower)
            
            target_article = article_match.group(1) if article_match else None
            target_paragraph = paragraph_match.group(1) if paragraph_match else None
            target_point = point_match.group(1) if point_match else None
            
            logger.debug(f"🎯 Legal precise: Looking for Điều {target_article}, Khoản {target_paragraph}, Điểm {target_point}")
            
            for similarity, doc_idx in zip(similarities[0], indices[0]):
                if (doc_idx >= len(self.documents) or doc_idx < 0 or 
                    similarity < threshold):
                    continue
                
                result = {
                    'content': self.documents[doc_idx],
                    'metadata': self.metadatas[doc_idx] if doc_idx < len(self.metadatas) else {},
                    'score': float(similarity),
                    'index': int(doc_idx),
                    'search_type': 'legal_precise'
                }
                
                # FIXED: Exact matching boost logic
                content_lower = result['content'].lower()
                law_unit = result['metadata'].get('law_unit', '')
                exact_matches = []
                boost_multiplier = 3.0
                
                # Check for exact article match
                if target_article:
                    # Check in content
                    if f"điều {target_article}" in content_lower:
                        boost_multiplier *= 1.5
                        exact_matches.append(f'Điều {target_article}')
                    
                    # Check in law_unit (e.g., "15.2.a" contains article 15)
                    if law_unit.startswith(f"{target_article}."):
                        boost_multiplier *= 1.3
                        exact_matches.append(f'Điều {target_article} (structure)')
                
                # Check for exact paragraph match
                if target_paragraph:
                    if f"khoản {target_paragraph}" in content_lower:
                        boost_multiplier *= 1.4
                        exact_matches.append(f'Khoản {target_paragraph}')
                    
                    # Check in law_unit (e.g., "15.2.a" contains paragraph 2)
                    if f".{target_paragraph}." in law_unit or law_unit.endswith(f".{target_paragraph}"):
                        boost_multiplier *= 1.2
                        exact_matches.append(f'Khoản {target_paragraph} (structure)')
                
                # Check for exact point match
                if target_point:
                    if f"điểm {target_point}" in content_lower:
                        boost_multiplier *= 1.3
                        exact_matches.append(f'Điểm {target_point}')
                    
                    # Check in law_unit (e.g., "15.2.a" ends with point "a")
                    if law_unit.endswith(f".{target_point}"):
                        boost_multiplier *= 1.1
                        exact_matches.append(f'Điểm {target_point} (structure)')
                
                # Apply boost
                result['score'] *= boost_multiplier
                
                if exact_matches:
                    result['exact_match'] = ', '.join(exact_matches)
                    result['boost_applied'] = f'{boost_multiplier:.1f}x'
                    logger.debug(f"📍 Exact match found: {exact_matches} → boost {boost_multiplier:.1f}x")
                
                # Priority for legal documents
                if result['metadata'].get('content_type') == 'legal_document':
                    result['score'] *= 1.1
                    result['legal_priority'] = True
                
                # Update stats
                if result['metadata'].get('content_type') == 'qa_entry':
                    self.stats['qa_matches'] += 1
                else:
                    self.stats['legal_matches'] += 1
                
                results.append(result)
            
            # Sort by boosted score for legal precise
            results.sort(key=lambda x: x['score'], reverse=True)
            
            logger.debug(f"🎯 Legal precise results: {len(results)} total, top score: {results[0]['score']:.3f}" if results else "No results")
            
            return results[:k]
            
        except Exception as e:
            logger.error(f"Legal precise search failed: {e}")
            return []

    async def _procedure_search(self, query: str, k: int) -> List[Dict]:
        """FIXED: Procedure search với FAISS compatibility"""
        try:
            query_embedding = self.embedding_model.embed_query(query)
            if not query_embedding:
                return []
            
            # FAISS compatibility fix
            import numpy as np
            query_vector = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
            query_vector = np.ascontiguousarray(query_vector)
            
            if not self.embedding_model.normalize_embeddings:
                import faiss
                query_vector_norm = query_vector.copy()
                faiss.normalize_L2(query_vector_norm)
                query_vector = query_vector_norm
            
            search_k = min(k * 4, self.faiss_index.ntotal)
            similarities, indices = self.faiss_index.search(query_vector, search_k)
            
            results = []
            threshold = self.thresholds['procedure']
            
            for similarity, doc_idx in zip(similarities[0], indices[0]):
                if (doc_idx >= len(self.documents) or doc_idx < 0 or 
                    similarity < threshold):
                    continue
                
                result = {
                    'content': self.documents[doc_idx],
                    'metadata': self.metadatas[doc_idx] if doc_idx < len(self.metadatas) else {},
                    'score': float(similarity),
                    'index': int(doc_idx),
                    'search_type': 'procedure'
                }
                
                # SMART boost cho Q&A entries trong procedure searches
                if result['metadata'].get('content_type') == 'qa_entry':
                    result['score'] *= self.qa_boost
                    result['boosted'] = 'qa_procedure'
                    self.stats['qa_matches'] += 1
                else:
                    self.stats['legal_matches'] += 1
                
                results.append(result)
            
            # Smart mixing: ưu tiên Q&A nhưng vẫn giữ legal docs
            qa_results = [r for r in results if r['metadata'].get('content_type') == 'qa_entry']
            legal_results = [r for r in results if r['metadata'].get('content_type') != 'qa_entry']
            
            # Sort each type by score
            qa_results.sort(key=lambda x: x['score'], reverse=True)
            legal_results.sort(key=lambda x: x['score'], reverse=True)
            
            # Mix: 60% Q&A, 40% legal cho procedure questions
            qa_slots = min(int(k * 0.6), len(qa_results))
            legal_slots = k - qa_slots
            
            final_results = qa_results[:qa_slots] + legal_results[:legal_slots]
            final_results.sort(key=lambda x: x['score'], reverse=True)
            
            return final_results[:k]
            
        except Exception as e:
            logger.error(f"Procedure search failed: {e}")
            return []

    async def _consultation_search(self, query: str, k: int) -> List[Dict]:
        """CONSULTATION: Tìm kiếm cho câu hỏi tư vấn - cân bằng Q&A và legal"""
        try:
            # Embed query với moderate processing
            query_embedding = self.embedding_model.embed_query(query)
            if not query_embedding:
                return []
            
            # FAISS search với threshold trung bình
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            search_k = min(k * 3, self.faiss_index.ntotal)
            similarities, indices = self.faiss_index.search(query_vector, search_k)
            
            results = []
            threshold = self.thresholds['consultation']
            
            for similarity, doc_idx in zip(similarities[0], indices[0]):
                if (doc_idx >= len(self.documents) or doc_idx < 0 or 
                    similarity < threshold):
                    continue
                
                result = {
                    'content': self.documents[doc_idx],
                    'metadata': self.metadatas[doc_idx] if doc_idx < len(self.metadatas) else {},
                    'score': float(similarity),
                    'index': int(doc_idx),
                    'search_type': 'consultation'
                }
                
                # Moderate boost cho Q&A
                if result['metadata'].get('content_type') == 'qa_entry':
                    result['score'] *= 1.1  # Nhẹ hơn procedure
                    result['boosted'] = 'qa_consultation'
                    self.stats['qa_matches'] += 1
                else:
                    self.stats['legal_matches'] += 1
                
                results.append(result)
            
            # Sort by score
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:k]
            
        except Exception as e:
            logger.error(f"Consultation search failed: {e}")
            return []

    async def _general_search(self, query: str, k: int) -> List[Dict]:
        """GENERAL: Tìm kiếm chung - balanced approach"""
        try:
            # Embed query với minimal processing
            query_embedding = self.embedding_model.embed_query(query)
            if not query_embedding:
                return []
            
            # Standard FAISS search
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            search_k = min(k * 2, self.faiss_index.ntotal)
            similarities, indices = self.faiss_index.search(query_vector, search_k)
            
            results = []
            threshold = self.thresholds['general']
            
            for similarity, doc_idx in zip(similarities[0], indices[0]):
                if (doc_idx >= len(self.documents) or doc_idx < 0 or 
                    similarity < threshold):
                    continue
                
                result = {
                    'content': self.documents[doc_idx],
                    'metadata': self.metadatas[doc_idx] if doc_idx < len(self.metadatas) else {},
                    'score': float(similarity),
                    'index': int(doc_idx),
                    'search_type': 'general'
                }
                
                # No boost for general search - keep original scores
                if result['metadata'].get('content_type') == 'qa_entry':
                    self.stats['qa_matches'] += 1
                else:
                    self.stats['legal_matches'] += 1
                
                results.append(result)
            
            # Sort by original similarity score
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:k]
            
        except Exception as e:
            logger.error(f"General search failed: {e}")
            return []
    
    def _classify_query_type(self, query: str) -> str:
        """SỬA LOGIC: Classify query type để áp dụng search strategy phù hợp"""
        query_lower = query.lower()
        
        # LEGAL PRECISE: Hỏi về điều, khoản, điểm cụ thể
        legal_precise_patterns = [
            r'điều\s+\d+[a-z]?',
            r'khoản\s+\d+',
            r'điểm\s+[a-z]+',
            r'(điều|khoản|điểm).*?(nói về|quy định|là gì|có nội dung)'
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

    async def search(self, query: str, query_features=None, k: int = 10) -> List[Dict]:
        """
        ENHANCED SEARCH: Smart search + conversation context integration
        🎯 Combine existing smart search với conversation context enhancement
        """
        start_time = time.time()
        self.stats['total_searches'] += 1
        
        if not query or len(query.strip()) < 3:
            return []
        
        if not self.documents:
            logger.warning("No documents loaded")
            return []
        
        try:
            # STEP 1: ENHANCE QUERY với conversation context (NEW)
            enhanced_query = query
            if query_features and query_features.get('has_context'):
                enhanced_query = self._enhance_query_with_features(query, query_features)
                logger.debug(f"🔗 Query enhanced with context: '{query}' → '{enhanced_query}'")
            
            # STEP 2: CLASSIFY enhanced query type (existing logic)
            query_type = self._classify_query_type(enhanced_query)
            logger.debug(f"🧠 Query type: {query_type} for '{enhanced_query[:50]}...'")
            
            # Update stats
            if query_type == 'legal_precise':
                self.stats['legal_precise_searches'] += 1
            elif query_type == 'procedure':
                self.stats['procedure_searches'] += 1
            elif query_type == 'consultation':
                self.stats['consultation_searches'] += 1
            
            # STEP 3: Apply smart search strategy với enhanced query
            if query_type == 'legal_precise':
                results = await self._legal_precise_search(enhanced_query, k * 2)
            elif query_type == 'procedure':
                results = await self._procedure_search(enhanced_query, k * 2)
            elif query_type == 'consultation':
                results = await self._consultation_search(enhanced_query, k * 2)
            else:
                results = await self._general_search(enhanced_query, k * 2)
            
            # STEP 4: CONTEXT-AWARE POST-PROCESSING (NEW)
            if query_features and query_features.get('has_context'):
                # Apply conversation context filtering
                results = self._apply_context_filtering(results, query, query_features)
                # Apply conversation boosting
                results = self._apply_conversation_boosting(results, query_features)
            else:
                # Fallback to existing post-processing
                results = self._post_process_results(results, query_type, query)
            
            # STEP 5: Final result selection
            final_results = results[:k]
            
            # Update stats
            search_time = time.time() - start_time
            self._update_search_stats(search_time, final_results)
            
            context_used = query_features.get('has_context', False) if query_features else False
            logger.debug(f"✅ Enhanced search ({query_type}): {len(final_results)} results in {search_time:.3f}s, context: {context_used}")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            return []

    def _enhance_query_with_features(self, original_query: str, query_features: Dict[str, Any]) -> str:
        """
        NEW METHOD: Enhance query với conversation context
        """
        if not query_features:
            return original_query
        
        enhanced_parts = [original_query]
        
        # 1. TOPIC THREAD từ conversation
        topic_thread = query_features.get('topic_thread')
        if topic_thread and topic_thread not in original_query.lower():
            enhanced_parts.append(topic_thread)
        
        # 2. CONVERSATION CONTEXT keywords
        conversation_context = query_features.get('conversation_context', '')
        if conversation_context:
            context_keywords = self._extract_context_keywords(conversation_context)
            for keyword in context_keywords[:2]:  # Top 2 keywords only
                if keyword not in original_query.lower():
                    enhanced_parts.append(keyword)
        
        # 3. CITIZEN PROFILE entities
        citizen_profile = query_features.get('citizen_profile', {})
        
        # Location context
        location = citizen_profile.get('location')
        if location and any(loc_word in original_query.lower() for loc_word in ['ở đâu', 'tại đâu', 'thì sao']):
            enhanced_parts.append(f"tại {location}")
        
        # Age group context
        age_group = citizen_profile.get('age_group')
        if age_group == 'minor':
            enhanced_parts.append("trẻ em")
        elif age_group == 'elderly':
            enhanced_parts.append("người cao tuổi")
        
        # Document status context
        passport_status = citizen_profile.get('passport_status')
        if passport_status == 'not_have' and 'làm' in original_query.lower():
            enhanced_parts.append("lần đầu")
        elif passport_status == 'expired':
            enhanced_parts.append("cấp lại")
        
        # 4. BOOST CONFIG từ admin_units.json
        boost_config = query_features.get('boost_config', {})
        if boost_config:
            boost_terms = boost_config.get('context_boost_terms', [])
            for term in boost_terms[:1]:  # Only 1 boost term
                if term not in original_query.lower():
                    enhanced_parts.append(term)
        
        enhanced_query = ' '.join(enhanced_parts)
        return enhanced_query

    def _extract_context_keywords(self, conversation_context: str) -> List[str]:
        """Extract important keywords from conversation context"""
        if not conversation_context:
            return []
        
        important_terms = []
        context_lower = conversation_context.lower()
        
        # Priority legal terms
        priority_terms = ['hộ chiếu', 'visa', 'xuất cảnh', 'nhập cảnh', 'lệ phí', 'thủ tục', 'cấp lại']
        for term in priority_terms:
            if term in context_lower and term not in important_terms:
                important_terms.append(term)
        
        return important_terms[:3]  # Max 3 terms

    def _apply_context_filtering(self, search_results: List[Dict], original_query: str, query_features: Dict[str, Any]) -> List[Dict]:
        """
        NEW METHOD: Apply conversation context filtering
        """
        if not query_features or not search_results:
            return search_results
        
        filtered_results = []
        
        # Get context info
        citizen_profile = query_features.get('citizen_profile', {})
        topic_thread = query_features.get('topic_thread', '')
        context_summary = query_features.get('context_summary', {})
        
        for result in search_results:
            content = result.get('content', '').lower()
            relevance_score = result.get('score', 0.5)
            
            # 1. TOPIC THREAD BOOST
            if topic_thread and topic_thread in content:
                relevance_score += 0.15
            
            # 2. LOCATION RELEVANCE
            location = citizen_profile.get('location')
            if location:
                location_lower = location.lower()
                if location_lower in content or location_lower.replace(' ', '') in content:
                    relevance_score += 0.1
            
            # 3. AGE GROUP RELEVANCE
            age_group = citizen_profile.get('age_group')
            if age_group == 'minor' and any(term in content for term in ['trẻ em', 'dưới 14', 'chưa đủ']):
                relevance_score += 0.12
            elif age_group == 'elderly' and any(term in content for term in ['cao tuổi', 'người già']):
                relevance_score += 0.08
            
            # 4. DOCUMENT STATUS RELEVANCE
            passport_status = citizen_profile.get('passport_status')
            if passport_status == 'not_have' and any(term in content for term in ['lần đầu', 'chưa có', 'chưa làm']):
                relevance_score += 0.1
            elif passport_status == 'expired' and any(term in content for term in ['cấp lại', 'hết hạn', 'quá hạn']):
                relevance_score += 0.1
            
            # 5. PRIORITY ASPECT BOOST
            priority_aspect = context_summary.get('priority_aspect', '')
            if priority_aspect and priority_aspect in content:
                relevance_score += 0.08
            
            # 6. VAGUE QUERY HANDLING
            if context_summary.get('has_vague_query') and len(content) < 100:
                relevance_score -= 0.05  # Prefer detailed content for vague queries
            
            # Update result
            result['score'] = relevance_score
            result['context_enhanced'] = True
            
            # Keep results above threshold
            if relevance_score >= 0.25:
                filtered_results.append(result)
        
        # Sort by enhanced score
        filtered_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        logger.debug(f"🎯 Context filtering: {len(search_results)} → {len(filtered_results)} results")
        return filtered_results

    def _apply_conversation_boosting(self, search_results: List[Dict], query_features: Dict[str, Any]) -> List[Dict]:
        """
        NEW METHOD: Apply conversation-based boosting
        """
        if not query_features:
            return search_results
        
        # Get conversation context
        original_query = query_features.get('original_query', '')
        conversation_context = query_features.get('conversation_context', '')
        
        for result in search_results:
            content = result.get('content', '').lower()
            score = result.get('score', 0.5)
            
            # Boost if content matches conversation context
            if conversation_context:
                context_words = set(conversation_context.lower().split())
                content_words = set(content.split())
                
                # Calculate context overlap
                overlap = len(context_words & content_words)
                if overlap > 2:  # Significant overlap
                    score += min(overlap * 0.02, 0.08)  # Max 0.08 boost
            
            # Boost if matches original query intent
            if original_query and original_query.lower() != query_features.get('resolved_query', '').lower():
                original_words = set(original_query.lower().split())
                content_words = set(content.split())
                
                intent_overlap = len(original_words & content_words) / len(original_words) if original_words else 0
                if intent_overlap > 0.5:
                    score += 0.05
            
            result['score'] = score
        
        # Re-sort after boosting
        search_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return search_results

    async def _legal_precise_search(self, query: str, k: int) -> List[Dict]:
        """LEGAL PRECISE: Tìm kiếm chính xác cho câu hỏi pháp lý cụ thể"""
        try:
            # Embed query với minimal processing
            query_embedding = self.embedding_model.embed_query(query)
            if not query_embedding:
                return []
            
            # FAISS search với threshold thấp hơn (FIXED)
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            # Search với k lớn hơn để có nhiều candidates
            search_k = min(k * 3, self.faiss_index.ntotal)
            similarities, indices = self.faiss_index.search(query_vector, search_k)
            
            results = []
            threshold = 0.15  # FIXED: Lower threshold for legal precise
            
            # Extract điều/khoản từ query để exact matching
            query_lower = query.lower()
            article_match = re.search(r'điều\s+(\d+[a-z]?)', query_lower)
            paragraph_match = re.search(r'khoản\s+(\d+)', query_lower)
            point_match = re.search(r'điểm\s+([a-z]+)', query_lower)
            
            target_article = article_match.group(1) if article_match else None
            target_paragraph = paragraph_match.group(1) if paragraph_match else None
            target_point = point_match.group(1) if point_match else None
            
            logger.debug(f"🎯 Legal precise: Looking for Điều {target_article}, Khoản {target_paragraph}, Điểm {target_point}")
            
            for similarity, doc_idx in zip(similarities[0], indices[0]):
                if (doc_idx >= len(self.documents) or doc_idx < 0 or 
                    similarity < threshold):
                    continue
                
                result = {
                    'content': self.documents[doc_idx],
                    'metadata': self.metadatas[doc_idx] if doc_idx < len(self.metadatas) else {},
                    'score': float(similarity),
                    'index': int(doc_idx),
                    'search_type': 'legal_precise'
                }
                
                # FIXED: Exact matching boost logic
                content_lower = result['content'].lower()
                law_unit = result['metadata'].get('law_unit', '')
                exact_matches = []
                boost_multiplier = 1.0
                
                # Check for exact article match
                if target_article:
                    # Check in content
                    if f"điều {target_article}" in content_lower:
                        boost_multiplier *= 1.5
                        exact_matches.append(f'Điều {target_article}')
                    
                    # Check in law_unit (e.g., "15.2.a" contains article 15)
                    if law_unit.startswith(f"{target_article}."):
                        boost_multiplier *= 1.3
                        exact_matches.append(f'Điều {target_article} (structure)')
                
                # Check for exact paragraph match
                if target_paragraph:
                    if f"khoản {target_paragraph}" in content_lower:
                        boost_multiplier *= 1.4
                        exact_matches.append(f'Khoản {target_paragraph}')
                    
                    # Check in law_unit (e.g., "15.2.a" contains paragraph 2)
                    if f".{target_paragraph}." in law_unit or law_unit.endswith(f".{target_paragraph}"):
                        boost_multiplier *= 1.2
                        exact_matches.append(f'Khoản {target_paragraph} (structure)')
                
                # Check for exact point match
                if target_point:
                    if f"điểm {target_point}" in content_lower:
                        boost_multiplier *= 1.3
                        exact_matches.append(f'Điểm {target_point}')
                    
                    # Check in law_unit (e.g., "15.2.a" ends with point "a")
                    if law_unit.endswith(f".{target_point}"):
                        boost_multiplier *= 1.1
                        exact_matches.append(f'Điểm {target_point} (structure)')
                
                # Apply boost
                result['score'] *= boost_multiplier
                
                if exact_matches:
                    result['exact_match'] = ', '.join(exact_matches)
                    result['boost_applied'] = f'{boost_multiplier:.1f}x'
                    logger.debug(f"📍 Exact match found: {exact_matches} → boost {boost_multiplier:.1f}x")
                
                # Priority for legal documents
                if result['metadata'].get('content_type') == 'legal_document':
                    result['score'] *= 1.1  # Small boost for legal docs in legal precise search
                    result['legal_priority'] = True
                
                # Update stats
                if result['metadata'].get('content_type') == 'qa_entry':
                    self.stats['qa_matches'] += 1
                else:
                    self.stats['legal_matches'] += 1
                
                results.append(result)
            
            # Sort by boosted score for legal precise
            results.sort(key=lambda x: x['score'], reverse=True)
            
            logger.debug(f"🎯 Legal precise results: {len(results)} total, top score: {results[0]['score']:.3f}" if results else "No results")
            
            return results[:k]
            
        except Exception as e:
            logger.error(f"Legal precise search failed: {e}")
            return []

    def _post_process_results(self, results: List[Dict], query_type: str, query: str) -> List[Dict]:
        """Post-process results based on query type"""
        if not results:
            return results
        
        # Remove duplicates based on content similarity
        seen_indices = set()
        filtered_results = []
        
        for result in results:
            idx = result.get('index')
            if idx not in seen_indices:
                seen_indices.add(idx)
                
                # Add query type info to metadata
                result['query_type'] = query_type
                
                # Add relevance explanation for legal precise
                if query_type == 'legal_precise' and result.get('exact_match'):
                    result['relevance_reason'] = f"Exact match: {result['exact_match']}"
                elif result.get('boosted'):
                    result['relevance_reason'] = f"Enhanced for {query_type}: {result['boosted']}"
                
                filtered_results.append(result)
        
        return filtered_results

    def _update_search_stats(self, search_time: float, results: List[Dict]):
        """Update search statistics"""
        total = self.stats['total_searches']
        current_avg = self.stats['avg_search_time']
        self.stats['avg_search_time'] = (current_avg * (total - 1) + search_time) / total

    async def search_with_content_priority(self, query: str, k: int = 5, query_features=None) -> List[Dict]:
        """Content priority search - delegate to smart search"""
        return await self.search(query, query_features, k)

    async def search_by_intent(self, query: str, intent_data: dict, k: int = 5) -> List[Dict]:
        """Intent-aware search - enhanced with smart logic"""
        try:
            # Extract intent information
            query_type = self._classify_query_type(query)
            
            # Override with intent data if provided
            if intent_data:
                if intent_data.get('is_procedure', False):
                    query_type = 'procedure'
                elif intent_data.get('needs_conclusion', False):
                    query_type = 'consultation'
                elif intent_data.get('has_specific_article', False):
                    query_type = 'legal_precise'
            
            # Use appropriate search strategy
            if query_type == 'legal_precise':
                return await self._legal_precise_search(query, k)
            elif query_type == 'procedure':
                return await self._procedure_search(query, k)
            elif query_type == 'consultation':
                return await self._consultation_search(query, k)
            else:
                return await self._general_search(query, k)
                
        except Exception as e:
            logger.error(f"Intent-aware search failed: {e}")
            return await self.search(query, None, k)

    async def search_by_subject_priority(self, query: str, subject_type=None, k: int = 5, 
                                       focus_keywords=None, query_features=None) -> List[Dict]:
        """Subject priority search - use smart search"""
        return await self.search(query, query_features, k)

    def get_stats(self) -> Dict[str, Any]:
        """Get smart search statistics"""
        total_searches = self.stats['total_searches']
        
        return {
            'documents_loaded': len(self.documents),
            'faiss_vectors': self.faiss_index.ntotal if self.faiss_index else 0,
            'search_performance': {
                'total_searches': total_searches,
                'avg_search_time': round(self.stats['avg_search_time'], 3),
                'qa_matches': self.stats['qa_matches'],
                'legal_matches': self.stats['legal_matches']
            },
            'smart_search_breakdown': {
                'legal_precise_searches': self.stats['legal_precise_searches'],
                'procedure_searches': self.stats['procedure_searches'],
                'consultation_searches': self.stats['consultation_searches'],
                'legal_precise_ratio': self.stats['legal_precise_searches'] / max(total_searches, 1),
                'procedure_ratio': self.stats['procedure_searches'] / max(total_searches, 1),
                'consultation_ratio': self.stats['consultation_searches'] / max(total_searches, 1)
            },
            'smart_settings': {
                'thresholds': self.thresholds,
                'qa_boost': self.qa_boost,
                'enhanced_mode': self.enhanced_mode
            },
            'smart_features': {
                'query_type_classification': True,
                'adaptive_thresholds': True,
                'content_type_boosting': True,
                'legal_precise_matching': True,
                'procedure_qa_priority': True,
                'consultation_balancing': True
            }
        }

class VectorStore:
    """🎛️ Smart controller với improved components"""
    
    def __init__(self):
        self.builder = VectorBuilder()
        self.searcher = VectorSearcher()
        
        self.is_building = False
        self.is_initialized = False
        self.build_lock = asyncio.Lock()
        
        self.stats = {
            'builds_completed': 0,
            'searches_performed': 0,
            'smart_searches_performed': 0,
            'last_build_time': None,
            'last_search_time': None
        }
        
        logger.info("Smart VectorStore controller initialized")
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize smart vector store for search"""
        if self.is_building:
            return {'success': False, 'message': 'Building in progress, please wait'}
        
        try:
            result = await self.searcher.initialize()
            self.is_initialized = result['success']
            
            if result['success']:
                logger.info(f"✅ Smart VectorStore initialized successfully")
            else:
                logger.error(f"❌ Smart VectorStore initialization failed: {result.get('message')}")
                
            return result
        except Exception as e:
            logger.error(f"Smart VectorStore initialization failed: {e}")
            return {'success': False, 'message': f'Initialization failed: {str(e)}'}
    
    async def build_if_needed(self, documents_path: str = None, force_rebuild: bool = False) -> Dict[str, Any]:
        """Build smart vector database if needed"""
        async with self.build_lock:
            if self.is_building:
                return {'success': False, 'message': 'Build already in progress'}
            
            if not force_rebuild and self._vector_database_exists():
                return {'success': True, 'message': 'Smart vector database exists (use force_rebuild=True to rebuild)'}
            
            try:
                self.is_building = True
                self.is_initialized = False
                
                logger.info("🔨 Starting smart vector database build...")
                result = await self.builder.build_from_directory(documents_path)
                
                if result['success']:
                    self.stats['builds_completed'] += 1
                    self.stats['last_build_time'] = datetime.now().isoformat()
                    
                    # Auto-initialize after successful build
                    logger.info("🔄 Auto-initializing smart system after build...")
                    init_result = await self.initialize()
                    
                    if not init_result['success']:
                        logger.warning(f"Smart build succeeded but initialization failed: {init_result.get('message')}")
                
                return result
                
            except Exception as e:
                logger.error(f"Smart build failed: {e}")
                return {'success': False, 'message': f'Build failed: {str(e)}'}
            finally:
                self.is_building = False
    
    async def search(self, query: str, query_features=None, k: int = 10) -> List[Dict]:
        """Smart search với automatic query type detection"""
        if self.is_building:
            logger.warning("Search blocked: Building in progress")
            return []
        
        if not self.is_initialized:
            logger.info("Auto-initializing for smart search...")
            init_result = await self.initialize()
            if not init_result['success']:
                logger.warning("Smart search failed: Could not initialize")
                return []
        
        try:
            self.stats['searches_performed'] += 1
            self.stats['smart_searches_performed'] += 1
            self.stats['last_search_time'] = datetime.now().isoformat()
            
            results = await self.searcher.search(query, query_features, k)
            
            logger.debug(f"🧠 Smart search '{query[:50]}...' returned {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"Smart search failed: {e}")
            return []

    # Smart search methods
    async def search_with_content_priority(self, query: str, k: int = 5, query_features=None) -> List[Dict]:
        """Smart content priority search"""
        return await self.searcher.search_with_content_priority(query, k, query_features)

    async def search_by_intent(self, query: str, intent_data: dict, k: int = 5) -> List[Dict]:
        """Smart intent-aware search"""
        return await self.searcher.search_by_intent(query, intent_data, k)
    
    def _vector_database_exists(self) -> bool:
        """Check if smart vector database exists"""
        required_files = [
            self.builder.docs_file,
            self.builder.meta_file
        ]
        
        return all(os.path.exists(f) for f in required_files)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive smart health status"""
        builder_stats = {
            'storage_path': self.builder.storage_path,
            'files_exist': self._vector_database_exists()
        }
        
        searcher_stats = self.searcher.get_stats() if self.is_initialized else {}
        
        return {
            'system_status': {
                'is_building': self.is_building,
                'is_initialized': self.is_initialized,
                'database_exists': builder_stats['files_exist'],
                'faiss_available': FAISS_AVAILABLE,
                'smart_features_enabled': True
            },
            'builder_stats': builder_stats,
            'searcher_stats': searcher_stats,
            'overall_stats': self.stats,
            'storage_info': {
                'storage_path': self.builder.storage_path,
                'files': {
                    'documents': os.path.exists(self.builder.docs_file),
                    'metadata': os.path.exists(self.builder.meta_file),
                    'faiss_index': os.path.exists(self.builder.index_file)
                }
            },
            'smart_improvements': {
                'query_type_classification': True,
                'adaptive_search_strategies': True,
                'legal_precise_matching': True,
                'procedure_qa_priority': True,
                'consultation_balancing': True,
                'content_type_boosting': True,
                'smart_thresholds': True
            },
            'performance': {
                'builds_completed': self.stats['builds_completed'],
                'searches_performed': self.stats['searches_performed'],
                'smart_searches_performed': self.stats['smart_searches_performed'],
                'last_build_time': self.stats['last_build_time'],
                'last_search_time': self.stats['last_search_time']
            },
            'recommendations': self._get_smart_health_recommendations()
        }
    
    def _get_smart_health_recommendations(self) -> List[str]:
        """Get smart health recommendations"""
        recommendations = []
        
        if not self._vector_database_exists():
            recommendations.append("Build smart vector database first")
        
        if not FAISS_AVAILABLE and self.searcher.documents and len(self.searcher.documents) > 1000:
            recommendations.append("Install FAISS for better performance with large smart datasets")
        
        if self.is_initialized and self.searcher.stats['total_searches'] > 0:
            avg_time = self.searcher.stats['avg_search_time']
            if avg_time > 1.0:
                recommendations.append("Smart search time is slow - consider optimizing")
        
        # Smart-specific recommendations
        if self.is_initialized:
            searcher_stats = self.searcher.get_stats()
            legal_precise_ratio = searcher_stats['smart_search_breakdown']['legal_precise_ratio']
            
            if legal_precise_ratio > 0.5:
                recommendations.append("High legal precise queries - system optimized for exact matching")
            elif legal_precise_ratio < 0.1:
                recommendations.append("Low legal precise queries - consider promoting specific legal references")
        
        if not recommendations:
            recommendations.append("Smart system is healthy with all intelligent features enabled")
        
        return recommendations
    
    # Backward compatibility methods
    async def hybrid_search(self, query: str, k: int = 10) -> List[Dict]:
        """Smart backward compatibility wrapper"""
        return await self.search(query, None, k)
    
    async def vector_search(self, query: str, k: int = 10) -> List[Dict]:
        """Smart backward compatibility wrapper"""
        return await self.search(query, None, k)
    
    async def search_by_subject_priority(self, query: str, subject_type=None, k: int = 5, 
                                        focus_keywords=None, query_features=None) -> List[Dict]:
        """Smart backward compatibility wrapper"""
        return await self.searcher.search_by_subject_priority(query, subject_type, k, focus_keywords, query_features)
    
    def clear_cache(self):
        """Clear smart caches"""
        if hasattr(self.searcher.embedding_model, 'clear_cache'):
            self.searcher.embedding_model.clear_cache()
        
        logger.info("Smart caches cleared")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for smart system"""
        health = self.get_health_status()
        
        detailed_stats = {
            'smart_vector_store_info': {
                'version': 'Smart Vietnamese Legal Vector Store v5.0',
                'document_processor_version': 'Smart Legal RAG v1.0',
                'key_improvements': [
                    'Query type classification (legal_precise, procedure, consultation)',
                    'Adaptive search thresholds per query type',
                    'Smart content type boosting',
                    'Legal precise exact matching',
                    'Procedure Q&A priority',
                    'Consultation balanced approach',
                    'DEk21 model optimization'
                ]
            },
            'query_type_support': {
                'legal_precise': {
                    'description': 'Điều/Khoản/Điểm specific queries',
                    'strategy': 'High threshold + exact matching',
                    'boost_factor': 1.5,
                    'examples': ['Khoản 2 điều 15 nói về gì', 'Điều 20 quy định thế nào']
                },
                'procedure': {
                    'description': 'Thủ tục/quy trình queries',
                    'strategy': 'Q&A priority + enhanced processing',
                    'boost_factor': 1.2,
                    'examples': ['Thủ tục làm hộ chiếu', 'Quy trình xin visa']
                },
                'consultation': {
                    'description': 'Tư vấn điều kiện queries',
                    'strategy': 'Balanced Q&A + legal docs',
                    'boost_factor': 1.1,
                    'examples': ['Có được xuất cảnh không', 'Điều kiện để làm gì']
                },
                'general': {
                    'description': 'General queries',
                    'strategy': 'Standard search',
                    'boost_factor': 1.0,
                    'examples': ['Thông tin về visa', 'Hộ chiếu là gì']
                }
            },
            'smart_architecture': {
                'components': ['VectorBuilder (enhanced)', 'VectorSearcher (smart)', 'VectorStore (smart)'],
                'embedding_model': self.searcher.embedding_model.model_name if hasattr(self.searcher.embedding_model, 'model_name') else 'DEk21 Vietnamese Model',
                'search_approach': 'Query classification → Strategy selection → Adaptive search → Smart boosting',
                'thresholds': self.searcher.thresholds if hasattr(self.searcher, 'thresholds') else 'Smart adaptive',
                'features': [
                    'Query type auto-detection',
                    'Adaptive similarity thresholds',
                    'Content type aware boosting',
                    'Legal structure exact matching',
                    'Q&A priority for procedures',
                    'Smart result mixing'
                ]
            },
            'performance_optimizations': {
                'legal_precise': 'High threshold (0.3) + exact article/paragraph matching',
                'procedure': 'Q&A boost (1.2x) + 60/40 Q&A/legal mixing',
                'consultation': 'Moderate boost (1.1x) + balanced approach',
                'general': 'Standard search with optimal thresholds'
            }
        }
        
        return {**health, **detailed_stats}

# Smart backward compatible alias
SmartVectorStore = VectorStore 