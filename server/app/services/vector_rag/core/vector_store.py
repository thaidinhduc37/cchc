# app/services/vector_rag/core/vector_store.py - OPTIMIZED VERSION
"""
Optimized Vector Store - Fast & Accurate với Mapping Guidance
🎯 Balance: Không quá đơn giản, không quá phức tạp
📋 Focus: Truy xuất nhanh + độ chính xác cao với mapping
🚀 Reusable cho nhiều lĩnh vực với mapping pattern
"""
import os
import pickle
import asyncio
import time
import re
from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import numpy as np
from pathlib import Path

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("FAISS not available - performance will be limited")

from app.services.vector_rag.rag_config import config
from app.services.vector_rag.core.document_processor import DocumentProcessor, Document
from app.services.vector_rag.core.embeddings import VietnameseEmbeddingModel

logger = logging.getLogger(__name__)

class VectorBuilder:
    """Vector Builder - unchanged, optimized for reliability"""
    
    def __init__(self):
        self.documents_path = config.documents_path
        self.embedding_model = VietnameseEmbeddingModel()
        self.storage_path = config.vector_store_path
        
        # File paths
        self.docs_file = os.path.join(self.storage_path, "documents.pkl")
        self.meta_file = os.path.join(self.storage_path, "metadata.pkl")
        self.index_file = os.path.join(self.storage_path, "faiss_index.bin")
        
        logger.info("VectorBuilder initialized - optimized build")
    
    async def build_from_directory(self, documents_path: str = None) -> Dict[str, Any]:
        """Optimized build từ directory"""
        try:
            processor = DocumentProcessor()
            
            if documents_path:
                documents = processor.process_directory(documents_path)
            else:
                documents = processor.process_directory(config.documents_path)
            
            if not documents:
                return {'success': False, 'message': 'No documents processed'}
            
            return await self.build_from_documents(documents)
            
        except Exception as e:
            logger.error("Build from directory failed: {}".format(str(e)))
            return {'success': False, 'message': 'Build failed: {}'.format(str(e))}
    
    async def build_from_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """Optimized build process - fast & reliable"""
        if not documents:
            return {'success': False, 'message': 'No documents provided'}
        
        try:
            logger.info("Building optimized vector database from {} documents".format(len(documents)))
            
            # Process documents efficiently
            contents = []
            metadatas = []
            stats = {'qa_count': 0, 'legal_count': 0, 'other_count': 0}
            
            for doc in documents:
                if not doc or not hasattr(doc, 'content') or not doc.content:
                    continue
                    
                content = doc.content.strip()
                metadata = getattr(doc, 'metadata', {})
                
                if len(content) > 10:
                    contents.append(content)
                    metadatas.append(metadata)
                    
                    # Count types for optimization
                    content_type = metadata.get('content_type', 'other')
                    if content_type == 'qa_entry':
                        stats['qa_count'] += 1
                    elif content_type == 'legal_document':
                        stats['legal_count'] += 1
                    else:
                        stats['other_count'] += 1
            
            if not contents:
                return {'success': False, 'message': 'No valid content after filtering'}
            
            logger.info("Content processed: {} valid chunks".format(len(contents)))
            logger.info("Distribution: Q&A={}, Legal={}, Other={}".format(stats['qa_count'], stats['legal_count'], stats['other_count']))
            
            # Fast embedding generation
            logger.info("Generating embeddings...")
            start_time = time.time()
            embeddings = self.embedding_model.embed_documents(contents)
            embed_time = time.time() - start_time
            
            if not embeddings or len(embeddings) != len(contents):
                return {'success': False, 'message': 'Embedding generation failed'}
            
            logger.info("Embeddings generated in {:.2f}s".format(embed_time))
            
            # Build optimized FAISS index
            logger.info("Building FAISS index...")
            start_time = time.time()
            
            embeddings_array = np.array(embeddings, dtype=np.float32)
            dimension = embeddings_array.shape[1]
            
            if FAISS_AVAILABLE:
                # Normalize for cosine similarity (faster search)
                faiss.normalize_L2(embeddings_array)
                
                # Use IndexFlatIP for fast exact search (good for < 100k docs)
                if len(embeddings) < 50000:
                    index = faiss.IndexFlatIP(dimension)
                else:
                    # Use IVF for larger datasets
                    nlist = min(int(np.sqrt(len(embeddings))), 1000)
                    quantizer = faiss.IndexFlatIP(dimension)
                    index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
                    index.train(embeddings_array)
                
                index.add(embeddings_array)
                index_time = time.time() - start_time
                logger.info("FAISS index built in {:.2f}s: {} vectors".format(index_time, index.ntotal))
            else:
                index = None
                index_time = 0
                logger.warning("FAISS not available - using fallback")
            
            # Atomic save
            logger.info("Saving vector database...")
            os.makedirs(self.storage_path, exist_ok=True)
            
            with open(self.docs_file, 'wb') as f:
                pickle.dump(contents, f)
            
            with open(self.meta_file, 'wb') as f:
                pickle.dump(metadatas, f)
            
            if index and FAISS_AVAILABLE:
                faiss.write_index(index, self.index_file)
            
            # Final stats
            build_stats = {
                'total_documents': len(contents),
                'qa_entries': stats['qa_count'],
                'legal_documents': stats['legal_count'],
                'other_content': stats['other_count'],
                'vectors': index.ntotal if index else len(contents),
                'dimension': dimension,
                'build_time': {
                    'embedding': round(embed_time, 2),
                    'indexing': round(index_time, 2),
                    'total': round(embed_time + index_time, 2)
                },
                'index_type': 'IndexFlatIP' if len(embeddings) < 50000 else 'IndexIVFFlat'
            }
            
            logger.info("✅ Build completed successfully in {}s".format(build_stats['build_time']['total']))
            
            return {
                'success': True,
                'message': 'Built optimized vector database with {} documents'.format(build_stats["total_documents"]),
                'stats': build_stats
            }
            
        except Exception as e:
            logger.error("Build failed: {}".format(str(e)))
            return {'success': False, 'message': 'Build failed: {}'.format(str(e))}

class VectorSearcher:
    """Optimized Vector Searcher - Fast với Mapping Guidance"""
    
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
        
        # Search optimization settings
        self.search_config = {
            'default_threshold': 0.2,
            'max_results_multiplier': 3,
            'boost_decay': 0.95,  # For keyword boosting
            'similarity_floor': 0.05  # Minimum similarity to consider
        }
        
        # Performance tracking
        self.stats = {
            'total_searches': 0,
            'mapping_guided_searches': 0,
            'avg_search_time': 0.0,
            'cache_hits': 0,
            'fast_searches': 0  # < 100ms
        }
        
        # Simple LRU cache for frequent queries
        self.query_cache = {}
        self.cache_size = 100
        
        logger.info("VectorSearcher initialized - optimized with mapping guidance")
    
    async def initialize(self) -> Dict[str, Any]:
        """Load vector database optimized"""
        try:
            start_time = time.time()
            
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
            if len(self.metadatas) != len(self.documents):
                # Fix metadata length
                while len(self.metadatas) < len(self.documents):
                    self.metadatas.append({})
                self.metadatas = self.metadatas[:len(self.documents)]
            
            load_time = time.time() - start_time
            total_docs = len(self.documents)
            total_vectors = self.faiss_index.ntotal if self.faiss_index else 0
            
            if total_docs == 0:
                return {'success': False, 'message': 'No documents in vector database'}
            
            # Count document types for optimization
            type_counts = {}
            for meta in self.metadatas:
                content_type = meta.get('content_type', 'unknown')
                type_counts[content_type] = type_counts.get(content_type, 0) + 1
            
            logger.info("✅ Vector database loaded in {:.2f}s: {} docs, {} vectors".format(load_time, total_docs, total_vectors))
            
            return {
                'success': True,
                'message': 'Optimized vector database ready: {} documents'.format(total_docs),
                'stats': {
                    'documents': total_docs,
                    'vectors': total_vectors,
                    'load_time': round(load_time, 3),
                    'type_distribution': type_counts,
                    'index_available': self.faiss_index is not None
                }
            }
            
        except Exception as e:
            logger.error("Initialize failed: {}".format(str(e)))
            return {'success': False, 'message': "Initialize failed: {}".format(str(e))}

    async def search(self, query: str, query_features: Dict = None, k: int = 10) -> List[Dict]:
        """
        Optimized search với mapping guidance - FIXED VERSION
        """
        search_start = time.time()
        self.stats['total_searches'] += 1
        
        # Input validation
        if not query or len(query.strip()) < 2:
            logger.warning("Empty or too short query")
            return []
        
        if not self.documents:
            logger.warning("No documents loaded")
            return []
        
        try:
            # Check cache first
            cache_key = f"{query.lower().strip()}_{k}"
            if cache_key in self.query_cache:
                self.stats['cache_hits'] += 1
                return self.query_cache[cache_key]
            
            mapping_config = None
            if query_features and isinstance(query_features, dict):
                mapping_config = query_features.get('mapping_config')
                
                
                if mapping_config is not None:
                    if not isinstance(mapping_config, dict):
                        logger.warning(f"Invalid mapping_config type: {type(mapping_config)}, ignoring")
                        mapping_config = None
                    elif not mapping_config:  # Empty dict
                        logger.debug("Empty mapping_config, treating as None")
                        mapping_config = None
                    else:
                        self.stats['mapping_guided_searches'] += 1
                        logger.debug(f"Using mapping guidance: {mapping_config.get('method', 'unknown')}")
            
            search_strategy = self._determine_search_strategy(query, mapping_config)
            
            results = []
            
            if search_strategy == 'mapping_guided' and mapping_config:
                try:
                    results = await self._mapping_guided_search(query, mapping_config, k)
                    logger.debug(f"Mapping-guided search completed: {len(results)} results")
                except Exception as e:
                    logger.error(f"Mapping-guided search failed: {e}")
                    logger.info("Falling back to standard search")
                    results = await self._standard_search(query, k)
                    
            elif search_strategy == 'exact_match':
                try:
                    results = await self._exact_match_search(query, k)
                    logger.debug(f"Exact match search completed: {len(results)} results")
                except Exception as e:
                    logger.error(f"Exact match search failed: {e}")
                    results = await self._standard_search(query, k)
                    
            else:
                results = await self._standard_search(query, k)
                logger.debug(f"Standard search completed: {len(results)} results")
            
            if mapping_config and isinstance(mapping_config, dict) and results:
                try:
                    results = self._apply_mapping_boosts(results, mapping_config)
                    logger.debug("Mapping boosts applied successfully")
                except Exception as e:
                    logger.warning(f"Mapping boosts failed: {e}")
            
            if query_features and isinstance(query_features, dict):
                try:
                    # Extract filter parameters safely
                    law_unit_filter = query_features.get('law_unit_filter')
                    short_content_boost = query_features.get('short_content_boost', 1.0)
                    
                    # Validate parameters
                    if not isinstance(short_content_boost, (int, float)) or short_content_boost <= 0:
                        short_content_boost = 1.0
                    
                    # Apply law_unit_filter
                    filtered_results = []
                    if law_unit_filter and isinstance(law_unit_filter, str):
                        try:
                            import re
                            for result in results:
                                if isinstance(result, dict):
                                    metadata = result.get('metadata', {})
                                    law_unit = metadata.get('law_unit', '')
                                    if isinstance(law_unit, str) and re.match(law_unit_filter, law_unit):
                                        filtered_results.append(result)
                            
                            if filtered_results:
                                results = filtered_results
                                logger.debug(f"Law unit filter '{law_unit_filter}' applied: {len(results)} results")
                            else:
                                logger.debug(f"Law unit filter '{law_unit_filter}' found no matches, keeping original results")
                                
                        except re.error as e:
                            logger.warning(f"Invalid law_unit_filter regex '{law_unit_filter}': {e}")
                        except Exception as e:
                            logger.warning(f"Law unit filtering failed: {e}")
                    
                    # Apply short content boost
                    if short_content_boost > 1.0:
                        try:
                            for result in results:
                                if isinstance(result, dict):
                                    content = result.get('content', '')
                                    if isinstance(content, str) and len(content) < 150:
                                        current_score = result.get('score', 0)
                                        if isinstance(current_score, (int, float)):
                                            result['score'] = current_score * short_content_boost * 2.0
                                            metadata = result.get('metadata', {})
                                            law_unit = metadata.get('law_unit', '')
                                            logger.debug(f"Boosted short chunk: law_unit={law_unit}, new_score={result['score']}")
                        except Exception as e:
                            logger.warning(f"Short content boost failed: {e}")
                    
                    # Sort results by score after boosts
                    try:
                        results.sort(key=lambda x: x.get('score', 0), reverse=True)
                    except Exception as e:
                        logger.warning(f"Result sorting failed: {e}")
                        
                except Exception as e:
                    logger.warning(f"Query features processing failed: {e}")
            
            # Limit results to requested amount
            results = results[:k] if isinstance(results, list) else []
            
            search_time = time.time() - search_start
            
            if search_time < 0.5 and len(self.query_cache) < self.cache_size:
                try:
                    self.query_cache[cache_key] = results
                except Exception as e:
                    logger.warning(f"Cache storing failed: {e}")
            
            # Update stats
            self._update_search_stats(search_time)
            
            if results:
                logger.debug(f"Search completed in {search_time:.3f}s: {len(results)} results")
                if logger.isEnabledFor(logging.DEBUG):
                    sample_results = [
                        f"law_unit: {r.get('metadata', {}).get('law_unit', '')}, "
                        f"score: {r.get('score', 0.0):.3f}, "
                        f"content: {r.get('content', '')[:50]}..."
                        for r in results[:3]  # Log top 3 results
                    ]
                    logger.debug(f"Top results: {sample_results}")
            else:
                logger.warning(f"No results found for query: {query[:50]}...")
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed completely: {e}")
            search_time = time.time() - search_start
            self._update_search_stats(search_time)

            return []
    
    def _determine_search_strategy(self, query: str, mapping_config: Dict = None) -> str:
        """FIXED: Handle null mapping_config"""
        try:
            query_lower = query.lower()
            
            # Direct article detection
            if re.search(r'điều\s+\d+', query_lower):
                return 'exact_match'
            
            # Legal keywords
            legal_keywords = ['hộ chiếu', 'xuất cảnh', 'nhập cảnh', 'thủ tục', 'giấy tờ', 'quy định']
            if any(keyword in query_lower for keyword in legal_keywords):
                return 'mapping_guided'
            
            # Check mapping_config safely
            if mapping_config and isinstance(mapping_config, dict):
                method = mapping_config.get('method', 'standard')
                if method != 'standard':
                    return 'mapping_guided'
            
            return 'standard'
            
        except Exception as e:
            logger.warning(f"Strategy determination failed: {e}")
            return 'standard'
    
    async def _mapping_guided_search(self, query: str, mapping_config: Dict, k: int) -> List[Dict]:
        """FIXED: Null safety cho mapping_config"""
        try:
            # CRITICAL FIX: Null check mapping_config
            if not mapping_config or not isinstance(mapping_config, dict):
                logger.warning("mapping_config is None or invalid, falling back to standard search")
                return await self._standard_search(query, k)
            
            # Safe extraction với defaults
            target_articles = mapping_config.get('target_articles', [])
            boost_keywords = mapping_config.get('boost_keywords', [])
            search_strategy = mapping_config.get('search_strategy', 'balanced')
            confidence_multiplier = mapping_config.get('confidence_multiplier', 1.0)
            expected_law_unit = mapping_config.get('expected_law_unit', None)
            
            # Validate extracted values
            if not isinstance(target_articles, list):
                target_articles = []
            if not isinstance(boost_keywords, list):
                boost_keywords = []
            if not isinstance(confidence_multiplier, (int, float)) or confidence_multiplier <= 0:
                confidence_multiplier = 1.0
            
            k_multiplier = mapping_config.get('k_multiplier', 2.0)
            if not isinstance(k_multiplier, (int, float)) or k_multiplier <= 0:
                k_multiplier = 2.0
                
            search_k = max(1, min(int(k * k_multiplier), len(self.documents)))
            
            # Enhanced query với safe processing
            try:
                enhanced_query = self._enhance_query_with_mapping(query, boost_keywords)
            except Exception as e:
                logger.warning(f"Query enhancement failed: {e}")
                enhanced_query = query
            
            # Vector search với error handling
            results = await self._vector_search(enhanced_query, search_k)
            
            # Apply filters safely
            if target_articles:
                try:
                    results = self._filter_by_target_articles(results, target_articles)
                except Exception as e:
                    logger.warning(f"Target article filtering failed: {e}")
            
            # Apply strategy boosts safely
            try:
                if search_strategy == 'legal_precise':
                    results = self._apply_legal_precise_boost(results, query)
                elif search_strategy == 'procedure_focused':
                    results = self._apply_procedure_boost(results)
            except Exception as e:
                logger.warning(f"Strategy boost failed: {e}")
            
            # Apply expected_law_unit boost
            if expected_law_unit:
                try:
                    for result in results:
                        law_unit = result.get('metadata', {}).get('law_unit', '')
                        if law_unit == expected_law_unit or law_unit.startswith(expected_law_unit + '.'):
                            result['score'] *= 10.0
                            result['expected_law_unit_boost'] = True
                            logger.debug(f"Boosted expected law_unit {law_unit} for query {query}")
                except Exception as e:
                    logger.warning(f"Expected law unit boost failed: {e}")
            
            # Apply confidence multiplier safely
            try:
                for result in results:
                    result['score'] *= confidence_multiplier
                    result['mapping_boosted'] = True
            except Exception as e:
                logger.warning(f"Confidence multiplier failed: {e}")
            
            results.sort(key=lambda x: x.get('score', 0), reverse=True)
            return results[:k]
            
        except Exception as e:
            logger.error(f"Mapping-guided search failed completely: {e}")
            # Fallback to standard search
            return await self._standard_search(query, k)
    
    async def _exact_match_search(self, query: str, k: int) -> List[Dict]:
        """Exact match search for legal references"""
        try:
            # Extract legal references
            article_matches = re.findall(r'điều\s+(\d+)', query.lower())
            results = await self._vector_search(query, k * 10)
            
            for result in results:
                content_lower = result['content'].lower()
                law_unit = result['metadata'].get('law_unit', '')
                boost = 1.0
                
                for article in article_matches:
                    if law_unit == article or law_unit.startswith(article + '.'):
                        boost *= 8.0
                        result['exact_article_match'] = article
                    elif f'điều {article}' in content_lower:
                        boost *= 4.0
                        result['exact_article_match'] = article
                
                result['score'] *= boost
                if boost > 1.0:
                    result['exact_match_boost'] = boost
            
            results.sort(key=lambda x: x['score'], reverse=True)
            logger.info("Exact match results: " + str([f"law_unit: {r.get('metadata', {}).get('law_unit', '')}, score: {r.get('score', 0.0)}" for r in results[:k]]))
            return results[:k]
            
        except Exception as e:
            logger.error("Exact match search failed: {}".format(str(e)))
            return await self._standard_search(query, k)
    
    async def _standard_search(self, query: str, k: int) -> List[Dict]:
        """Standard vector search - optimized baseline"""
        return await self._vector_search(query, k)
    
    async def _vector_search(self, query: str, k: int) -> List[Dict]:
        try:
            query_embedding = self.embedding_model.embed_query(query)
            if not query_embedding:
                return []
            
            query_vector = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
            query_vector = np.ascontiguousarray(query_vector)
            
            if not self.embedding_model.normalize_embeddings:
                faiss.normalize_L2(query_vector)
            
            search_k = max(1, min(k * 20, self.faiss_index.ntotal))  # Tăng k lên 20 lần
            
            similarities, indices = self.faiss_index.search(query_vector, search_k)
            
            results = []
            threshold = 0.0
            
            # Từ khóa ngữ nghĩa cho boost
            legal_keywords = ['hộ chiếu', 'xuất cảnh', 'nhập cảnh', 'thủ tục', 'giấy tờ', 'quy định']
            
            for similarity, doc_idx in zip(similarities[0], indices[0]):
                if doc_idx >= len(self.documents) or doc_idx < 0:
                    continue
                
                result = {
                    'content': self.documents[doc_idx],
                    'metadata': self.metadatas[doc_idx] if doc_idx < len(self.metadatas) else {},
                    'score': float(similarity),
                    'index': int(doc_idx),
                    'search_method': 'vector'
                }
                law_unit = result['metadata'].get('law_unit', '')
                content_lower = result['content'].lower()
                # Boost law_unit khớp query
                if law_unit and re.search(r'điều\s+\d+', query.lower()):
                    query_parts = re.findall(r'\d+', query.lower())
                    if query_parts and (law_unit == query_parts[0] or law_unit.startswith(query_parts[0] + '.')):
                        result['score'] *= 12.0  # Tăng boost
                        logger.debug("Boosted law_unit {} for query {}".format(law_unit, query))
                # Boost ngữ nghĩa cho query không rõ ràng
                elif any(keyword in query.lower() for keyword in legal_keywords):
                    if any(keyword in content_lower for keyword in legal_keywords):
                        result['score'] *= 5.0  # Boost ngữ nghĩa
                        logger.debug("Boosted semantic match for law_unit {}: {}".format(law_unit, query))
                # Boost chunk ngắn
                if len(result['content']) < 150:
                    result['score'] *= 4.0
                    logger.debug("Boosted short chunk: law_unit={}, score={}".format(law_unit, result['score']))
                results.append(result)
            
            logger.info("Vector search results: " + str([f"law_unit: {r.get('metadata', {}).get('law_unit', '')}, score: {r.get('score', 0.0)}" for r in results]))
            return results
        
        except Exception as e:
            logger.error("Vector search failed: {}".format(str(e)))
            return []
    
    def _enhance_query_with_mapping(self, query: str, boost_keywords: List[str]) -> str:
        """Enhance query with mapping keywords"""
        if not boost_keywords:
            return query
        
        # Add relevant boost keywords that aren't already in query
        query_lower = query.lower()
        added_keywords = []
        
        for keyword in boost_keywords[:3]:  # Limit to top 3
            if keyword.lower() not in query_lower:
                added_keywords.append(keyword)
        
        if added_keywords:
            enhanced = f"{query} {' '.join(added_keywords)}"
            logger.debug("Enhanced query: '{}' → '{}'".format(query, enhanced))
            return enhanced
        
        return query
    
    def _filter_by_target_articles(self, results: List[Dict], target_articles: List[str]) -> List[Dict]:
        """Filter results by target articles - FIXED to use metadata"""
        if not target_articles:
            return results
        
        filtered = []
        for result in results:
            metadata = result.get('metadata', {})
            law_unit = metadata.get('law_unit', '')
            
            # Check if law_unit matches any target article
            for article in target_articles:
                if law_unit == article or law_unit.startswith(article + '.'):
                    result['target_article_match'] = article
                    filtered.append(result)
                    break
        
        # If filtering too strict, keep some original results
        if len(filtered) < len(results) * 0.3:
            filtered.extend(results[:max(3, len(results) // 2)])
        
        logger.info("Filtered by target_articles {}: {} results".format(target_articles, len(filtered)))
        return filtered
    
    def _apply_legal_precise_boost(self, results: List[Dict], query: str) -> List[Dict]:
        """Apply legal precise boost"""
        for result in results:
            if result['metadata'].get('content_type') == 'legal_document':
                result['score'] *= 1.3
                result['legal_precise_boost'] = True
        return results
    
    def _apply_procedure_boost(self, results: List[Dict]) -> List[Dict]:
        """Apply procedure-focused boost"""
        for result in results:
            if result['metadata'].get('content_type') == 'qa_entry':
                result['score'] *= 1.2
                result['procedure_boost'] = True
        return results
    
    def _apply_mapping_boosts(self, results: List[Dict], mapping_config: Dict) -> List[Dict]:
        """Apply mapping-based boosts"""
        boost_keywords = mapping_config.get('boost_keywords', [])
        
        for result in results:
            content_lower = result['content'].lower()
            boost = 1.0
            matched_keywords = []
            
            for keyword in boost_keywords:
                if keyword.lower() in content_lower:
                    boost *= 1.1
                    matched_keywords.append(keyword)
            
            if boost > 1.0:
                result['score'] *= boost
                result['keyword_boost'] = boost
                result['matched_keywords'] = matched_keywords
        
        return results
    
    def _update_search_stats(self, search_time: float):
        """Update search statistics"""
        total = self.stats['total_searches']
        current_avg = self.stats['avg_search_time']
        self.stats['avg_search_time'] = (current_avg * (total - 1) + search_time) / total
        
        if search_time < 0.1:
            self.stats['fast_searches'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        total_searches = self.stats['total_searches']
        
        return {
            'documents_loaded': len(self.documents),
            'faiss_vectors': self.faiss_index.ntotal if self.faiss_index else 0,
            'search_performance': {
                'total_searches': total_searches,
                'mapping_guided_rate': round(self.stats['mapping_guided_searches'] / max(total_searches, 1), 3),
                'avg_search_time': round(self.stats['avg_search_time'], 3),
                'fast_search_rate': round(self.stats['fast_searches'] / max(total_searches, 1), 3),
                'cache_hit_rate': round(self.stats['cache_hits'] / max(total_searches, 1), 3)
            },
            'optimization_features': {
                'faiss_available': FAISS_AVAILABLE,
                'mapping_guidance': True,
                'exact_match_boost': True,
                'keyword_enhancement': True,
                'query_caching': True,
                'adaptive_search_strategy': True
            },
            'search_config': self.search_config
        }

class VectorStore:
    """Optimized Vector Store Controller"""
    
    def __init__(self):
        self.builder = VectorBuilder()
        self.searcher = VectorSearcher()
        
        self.is_building = False
        self.is_initialized = False
        self.build_lock = asyncio.Lock()
        
        self.stats = {
            'builds_completed': 0,
            'searches_performed': 0,
            'last_build_time': None,
            'last_search_time': None
        }
        
        logger.info("Optimized VectorStore controller initialized")
    
    async def initialize(self) -> Dict[str, Any]:
        """Initialize optimized vector store"""
        if self.is_building:
            return {'success': False, 'message': 'Building in progress, please wait'}
        
        try:
            result = await self.searcher.initialize()
            self.is_initialized = result['success']
            return result
        except Exception as e:
            logger.error("VectorStore initialization failed: {}".format(str(e)))
            return {'success': False, 'message': 'Initialization failed: {}'.format(str(e))}
    
    async def build_if_needed(self, documents_path: str = None, force_rebuild: bool = False) -> Dict[str, Any]:
        """Build optimized vector database if needed"""
        async with self.build_lock:
            if self.is_building:
                return {'success': False, 'message': 'Build already in progress'}
            
            if not force_rebuild and self._vector_database_exists():
                return {'success': True, 'message': 'Optimized vector database exists'}
            
            try:
                self.is_building = True
                self.is_initialized = False
                
                logger.info("🔨 Starting optimized vector database build...")
                result = await self.builder.build_from_directory(documents_path)
                
                if result['success']:
                    self.stats['builds_completed'] += 1
                    self.stats['last_build_time'] = datetime.now().isoformat()
                    
                    # Auto-initialize
                    init_result = await self.initialize()
                    if not init_result['success']:
                        logger.warning("Build succeeded but initialization failed")
                
                return result
                
            except Exception as e:
                logger.error("Build failed: {}".format(str(e)))
                return {'success': False, 'message': 'Build failed: {}'.format(str(e))}
            finally:
                self.is_building = False
    
    async def search(self, query: str, query_features: Dict = None, k: int = 10) -> List[Dict]:
        """Optimized search with mapping guidance"""
        if self.is_building:
            logger.warning("Search blocked: Building in progress")
            return []
        
        if not self.is_initialized:
            init_result = await self.initialize()
            if not init_result['success']:
                logger.warning("Search failed: Could not initialize")
                return []
        
        try:
            self.stats['searches_performed'] += 1
            self.stats['last_search_time'] = datetime.now().isoformat()
            
            results = await self.searcher.search(query, query_features, k)
            
            logger.debug("Search '{}...' returned {} results".format(query[:30], len(results)))
            return results
            
        except Exception as e:
            logger.error("Search failed: {}".format(str(e)))
            return []
    
    def _vector_database_exists(self) -> bool:
        """Check if vector database exists"""
        return all(os.path.exists(f) for f in [
            self.builder.docs_file,
            self.builder.meta_file
        ])
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
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
                'faiss_available': FAISS_AVAILABLE
            },
            'builder_stats': builder_stats,
            'searcher_stats': searcher_stats,
            'overall_stats': self.stats,
            'optimization_features': {
                'mapping_guidance': True,
                'fast_exact_matching': True,
                'adaptive_search_strategies': True,
                'query_caching': True,
                'performance_tracking': True
            }
        }
    
    def clear_cache(self):
        """Clear search cache"""
        if hasattr(self.searcher, 'query_cache'):
            self.searcher.query_cache.clear()
        logger.info("Search cache cleared")

# Backward compatibility
SmartVectorStore = VectorStore