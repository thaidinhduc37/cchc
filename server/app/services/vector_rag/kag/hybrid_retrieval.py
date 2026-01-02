# app/services/vector_rag/kag/hybrid_retrieval.py

from typing import List, Dict, Optional, Tuple
import logging
from dataclasses import dataclass
import numpy as np
from ..core.vector_store import VectorStore
from ..core.embeddings import EmbeddingService
from .legal_entities import LegalEntityExtractor

logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Represents a search result with score and metadata"""
    content: str
    score: float
    metadata: Dict
    source: str  # 'exact', 'semantic', 'hybrid'
    boost_factor: float = 1.0

class HybridRetrieval:
    """
    Hybrid retrieval system combining exact legal lookup with semantic search
    Designed for Vietnamese legal document retrieval with focus on immigration law
    """
    
    def __init__(self, vector_store: VectorStore, embedding_service: EmbeddingService):
        """
        Initialize hybrid retrieval system
        
        Args:
            vector_store: Vector store for semantic search
            embedding_service: Service for creating embeddings
        """
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.entity_extractor = LegalEntityExtractor()
        
        # Configuration
        self.exact_boost_factor = 2.0
        self.semantic_weight = 0.6
        self.exact_weight = 0.4
        self.min_exact_score = 0.8
        
        # Initialize exact lookup index
        self.exact_index = self._build_exact_index()
        
        logger.info("Initialized HybridRetrieval system")
    
    def _build_exact_index(self) -> Dict[str, List[Dict]]:
        """
        Build exact lookup index from vector store documents
        
        Returns:
            Dictionary mapping legal terms to document chunks
        """
        exact_index = {}
        
        try:
            # Get all documents from vector store
            all_docs = self.vector_store.get_all_documents()
            
            for doc in all_docs:
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                
                # Extract legal entities from content
                entities = self.entity_extractor.extract_entities(content)
                
                # Index by entity canonical forms
                for entity in entities:
                    key = entity.canonical_form or entity.text
                    key_normalized = key.lower().strip()
                    
                    if key_normalized not in exact_index:
                        exact_index[key_normalized] = []
                    
                    exact_index[key_normalized].append({
                        'content': content,
                        'metadata': metadata,
                        'entity_type': entity.entity_type,
                        'confidence': entity.confidence
                    })
            
            logger.info(f"Built exact index with {len(exact_index)} terms")
            return exact_index
            
        except Exception as e:
            logger.error(f"Error building exact index: {str(e)}")
            return {}
    
    def search(self, query: str, k: int = 10) -> List[Dict]:
        """
        Main search method combining exact and semantic search
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of search results ranked by relevance
        """
        try:
            # Check if query contains legal entities
            has_legal_entities = self.entity_extractor.is_legal_query(query)
            
            if has_legal_entities:
                # Hybrid search: exact + semantic
                exact_results = self._exact_legal_lookup(query)
                semantic_results = self._semantic_search(query, k)
                
                # Fuse results
                fused_results = self._fuse_results(exact_results, semantic_results)
                
                logger.info(f"Hybrid search: {len(exact_results)} exact + {len(semantic_results)} semantic = {len(fused_results)} fused")
                
            else:
                # Semantic search only
                semantic_results = self._semantic_search(query, k)
                fused_results = [self._result_to_dict(r) for r in semantic_results]
                
                logger.info(f"Semantic search only: {len(fused_results)} results")
            
            # Apply final ranking and return top k
            final_results = self._apply_final_ranking(fused_results, query)
            return final_results[:k]
            
        except Exception as e:
            logger.error(f"Error in hybrid search: {str(e)}")
            # Fallback to semantic search
            return self._fallback_search(query, k)
    
    def _exact_legal_lookup(self, query: str) -> List[SearchResult]:
        """
        Perform exact lookup for legal entities in query
        
        Args:
            query: Search query
            
        Returns:
            List of exact match results
        """
        results = []
        
        try:
            # Extract legal references from query
            legal_refs = self.entity_extractor.get_legal_references(query)
            
            for ref in legal_refs:
                ref_normalized = ref.lower().strip()
                
                # Look up in exact index
                if ref_normalized in self.exact_index:
                    for match in self.exact_index[ref_normalized]:
                        result = SearchResult(
                            content=match['content'],
                            score=match['confidence'],
                            metadata=match['metadata'],
                            source='exact',
                            boost_factor=self.exact_boost_factor
                        )
                        results.append(result)
            
            # Remove duplicates
            results = self._remove_duplicate_results(results)
            
            # Sort by score
            results.sort(key=lambda x: x.score * x.boost_factor, reverse=True)
            
            logger.debug(f"Exact lookup found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in exact lookup: {str(e)}")
            return []
    
    def _semantic_search(self, query: str, k: int) -> List[SearchResult]:
        """
        Perform semantic search using vector store
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of semantic search results
        """
        try:
            # Normalize query
            normalized_query = self.entity_extractor.normalize_query(query)
            
            # Perform vector search
            vector_results = self.vector_store.search(normalized_query, k=k*2)  # Get more for filtering
            
            # Convert to SearchResult objects
            results = []
            for result in vector_results:
                search_result = SearchResult(
                    content=result.get('content', ''),
                    score=result.get('score', 0.0),
                    metadata=result.get('metadata', {}),
                    source='semantic'
                )
                results.append(search_result)
            
            logger.debug(f"Semantic search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []
    
    def _fuse_results(self, exact_results: List[SearchResult], semantic_results: List[SearchResult]) -> List[Dict]:
        """
        Fuse exact and semantic results using weighted combination
        
        Args:
            exact_results: Results from exact lookup
            semantic_results: Results from semantic search
            
        Returns:
            Fused and ranked results
        """
        all_results = {}
        
        # Add exact results with boost
        for result in exact_results:
            content_hash = hash(result.content)
            if content_hash not in all_results:
                all_results[content_hash] = {
                    'content': result.content,
                    'metadata': result.metadata,
                    'exact_score': result.score * result.boost_factor,
                    'semantic_score': 0.0,
                    'source': 'exact'
                }
        
        # Add semantic results
        for result in semantic_results:
            content_hash = hash(result.content)
            if content_hash not in all_results:
                all_results[content_hash] = {
                    'content': result.content,
                    'metadata': result.metadata,
                    'exact_score': 0.0,
                    'semantic_score': result.score,
                    'source': 'semantic'
                }
            else:
                # Update semantic score if exists
                all_results[content_hash]['semantic_score'] = result.score
                all_results[content_hash]['source'] = 'hybrid'
        
        # Calculate combined scores
        fused_results = []
        for result_data in all_results.values():
            combined_score = (
                self.exact_weight * result_data['exact_score'] +
                self.semantic_weight * result_data['semantic_score']
            )
            
            fused_results.append({
                'content': result_data['content'],
                'metadata': result_data['metadata'],
                'score': combined_score,
                'exact_score': result_data['exact_score'],
                'semantic_score': result_data['semantic_score'],
                'source': result_data['source']
            })
        
        # Sort by combined score
        fused_results.sort(key=lambda x: x['score'], reverse=True)
        
        return fused_results
    
    def _boost_exact_matches(self, results: List[Dict]) -> List[Dict]:
        """
        Apply additional boosting to exact matches
        
        Args:
            results: List of fused results
            
        Returns:
            Results with exact match boosting applied
        """
        boosted_results = []
        
        for result in results:
            boosted_result = result.copy()
            
            # Boost exact matches
            if result['source'] in ['exact', 'hybrid'] and result['exact_score'] > self.min_exact_score:
                boosted_result['score'] *= self.exact_boost_factor
                boosted_result['boosted'] = True
            else:
                boosted_result['boosted'] = False
            
            boosted_results.append(boosted_result)
        
        # Re-sort after boosting
        boosted_results.sort(key=lambda x: x['score'], reverse=True)
        
        return boosted_results
    
    def _apply_final_ranking(self, results: List[Dict], query: str) -> List[Dict]:
        """
        Apply final ranking adjustments
        
        Args:
            results: Fused results
            query: Original query
            
        Returns:
            Final ranked results
        """
        # Apply exact match boosting
        ranked_results = self._boost_exact_matches(results)
        
        # Apply query-specific boosts
        entity_types = self.entity_extractor.get_entity_types(query)
        
        for result in ranked_results:
            # Boost results that match query entity types
            result_entities = self.entity_extractor.extract_entities(result['content'])
            result_entity_types = set(entity.entity_type for entity in result_entities)
            
            # Calculate entity type overlap
            overlap = len(entity_types.intersection(result_entity_types))
            if overlap > 0:
                result['score'] *= (1.0 + 0.1 * overlap)
                result['entity_overlap'] = overlap
            else:
                result['entity_overlap'] = 0
        
        # Final sort
        ranked_results.sort(key=lambda x: x['score'], reverse=True)
        
        return ranked_results
    
    def _remove_duplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate results based on content"""
        seen_content = set()
        unique_results = []
        
        for result in results:
            content_hash = hash(result.content)
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def _result_to_dict(self, result: SearchResult) -> Dict:
        """Convert SearchResult to dictionary format"""
        return {
            'content': result.content,
            'score': result.score,
            'metadata': result.metadata,
            'source': result.source,
            'exact_score': result.score if result.source == 'exact' else 0.0,
            'semantic_score': result.score if result.source == 'semantic' else 0.0,
            'boosted': False,
            'entity_overlap': 0
        }
    
    def _fallback_search(self, query: str, k: int) -> List[Dict]:
        """
        Fallback search method when hybrid search fails
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            Fallback search results
        """
        try:
            logger.warning("Using fallback search")
            semantic_results = self._semantic_search(query, k)
            return [self._result_to_dict(r) for r in semantic_results]
        except Exception as e:
            logger.error(f"Fallback search failed: {str(e)}")
            return []
    
    def get_search_stats(self, query: str) -> Dict:
        """
        Get search statistics for debugging
        
        Args:
            query: Search query
            
        Returns:
            Dictionary with search statistics
        """
        stats = {
            'query': query,
            'has_legal_entities': self.entity_extractor.is_legal_query(query),
            'entity_types': list(self.entity_extractor.get_entity_types(query)),
            'legal_references': self.entity_extractor.get_legal_references(query),
            'normalized_query': self.entity_extractor.normalize_query(query),
            'exact_index_size': len(self.exact_index),
            'vector_store_size': self.vector_store.get_document_count() if hasattr(self.vector_store, 'get_document_count') else 'unknown'
        }
        
        return stats
    
    def update_exact_index(self, new_documents: List[Dict]) -> None:
        """
        Update exact index with new documents
        
        Args:
            new_documents: List of new documents to index
        """
        try:
            for doc in new_documents:
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                
                # Extract legal entities from content
                entities = self.entity_extractor.extract_entities(content)
                
                # Update index
                for entity in entities:
                    key = entity.canonical_form or entity.text
                    key_normalized = key.lower().strip()
                    
                    if key_normalized not in self.exact_index:
                        self.exact_index[key_normalized] = []
                    
                    self.exact_index[key_normalized].append({
                        'content': content,
                        'metadata': metadata,
                        'entity_type': entity.entity_type,
                        'confidence': entity.confidence
                    })
            
            logger.info(f"Updated exact index with {len(new_documents)} documents")
            
        except Exception as e:
            logger.error(f"Error updating exact index: {str(e)}")
    
    def rebuild_exact_index(self) -> None:
        """Rebuild the entire exact index"""
        try:
            self.exact_index = self._build_exact_index()
            logger.info("Rebuilt exact index successfully")
        except Exception as e:
            logger.error(f"Error rebuilding exact index: {str(e)}")


# Integration example for rag_engine.py
# Integration với RAG Engine hiện tại
class RAGEngineIntegration:
    """
    Integration KAG với RAG Engine của bạn
    """
    
    def __init__(self, vector_searcher, embedding_service):
        # Tích hợp với VectorSearcher hiện có
        self.vector_searcher = vector_searcher  
        self.embedding_service = embedding_service
        
        # Khởi tạo hybrid retrieval
        self.hybrid_retrieval = HybridRetrieval(vector_searcher, embedding_service)
        
        # Mapping từ rag_mapping.py
        from .rag_mapping import create_xuatnhapcanh_mapping
        self.domain_mapping = create_xuatnhapcanh_mapping()
    
    def enhanced_search(self, query: str, unified_context: Dict = None, k: int = 10) -> List[Dict]:
        """
        Enhanced search tích hợp KAG + mapping
        
        Args:
            query: Search query
            unified_context: Context từ unified_processor
            k: Number of results
            
        Returns:
            Enhanced search results
        """
        try:
            # STEP 1: Mapping navigation (từ rag_engine.py)
            intent_analysis = unified_context.get('intent_analysis', {}) if unified_context else {}
            
            search_config = self.domain_mapping.get_vector_search_config(
                query=query,
                intent_analysis=intent_analysis,
                unified_context=unified_context
            )
            
            # STEP 2: Hybrid search với KAG
            if search_config['method'] != 'standard':
                # Mapping-guided hybrid search
                results = self.hybrid_retrieval.search(query, k=int(k * search_config.get('k_multiplier', 1.0)))
                
                # Apply mapping boosts
                for result in results:
                    result['mapping_method'] = search_config['method']
                    result['score'] *= search_config.get('confidence_multiplier', 1.0)
                
                # Re-sort after mapping boost
                results.sort(key=lambda x: x['score'], reverse=True)
                return results[:k]
            else:
                # Standard hybrid search
                return self.hybrid_retrieval.search(query, k)
                
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            # Fallback to standard search
            return self.hybrid_retrieval.search(query, k)
    
    def get_context_for_llm(self, query: str, search_results: List[Dict], max_context_length: int = 4000) -> str:
        """
        Format context cho LLM từ search results
        
        Args:
            query: User query
            search_results: Results from enhanced_search
            max_context_length: Maximum context length
            
        Returns:
            Formatted context string
        """
        context_parts = []
        current_length = 0
        
        for i, result in enumerate(search_results):
            content = result['content']
            metadata = result.get('metadata', {})
            
            # Enhanced source information
            source_info = f"[Nguồn {i+1}]"
            
            # Add document type
            if metadata.get('law_unit'):
                source_info += f" {metadata['law_unit']}"
            elif metadata.get('source'):
                source_info += f" {metadata['source']}"
            
            # Add search method info
            if result.get('source') == 'exact':
                source_info += " (Tìm kiếm chính xác)"
            elif result.get('mapping_method'):
                source_info += f" ({result['mapping_method']})"
            
            formatted_content = f"{source_info}\n{content}\n"
            
            if current_length + len(formatted_content) > max_context_length:
                break
            
            context_parts.append(formatted_content)
            current_length += len(formatted_content)
        
        return "\n".join(context_parts)
    
    def debug_search(self, query: str, unified_context: Dict = None) -> Dict:
        """
        Debug toàn bộ search process
        
        Args:
            query: Search query
            unified_context: Context từ unified_processor
            
        Returns:
            Comprehensive debug information
        """
        # KAG stats
        kag_stats = self.hybrid_retrieval.get_search_stats(query)
        
        # Mapping stats
        intent_analysis = unified_context.get('intent_analysis', {}) if unified_context else {}
        mapping_config = self.domain_mapping.get_vector_search_config(query, intent_analysis, unified_context)
        
        # Search results
        results = self.enhanced_search(query, unified_context, k=10)
        
        debug_info = {
            'query_analysis': {
                'original_query': query,
                'has_legal_entities': kag_stats['has_legal_entities'],
                'entity_types': kag_stats['entity_types'],
                'legal_references': kag_stats['legal_references'],
                'normalized_query': kag_stats['normalized_query']
            },
            'mapping_info': {
                'method': mapping_config['method'],
                'target_articles': mapping_config['target_articles'],
                'boost_keywords': mapping_config['boost_keywords'],
                'confidence_multiplier': mapping_config['confidence_multiplier']
            },
            'search_results': {
                'total_results': len(results),
                'results_by_source': {
                    'exact': len([r for r in results if r.get('source') == 'exact']),
                    'semantic': len([r for r in results if r.get('source') == 'semantic']),
                    'hybrid': len([r for r in results if r.get('source') == 'hybrid'])
                },
                'mapping_enhanced': len([r for r in results if r.get('mapping_method')])
            },
            'top_results': results[:3] if results else [],
            'system_stats': {
                'kag_stats': kag_stats,
                'mapping_stats': self.domain_mapping.get_stats()
            }
        }
        
        return debug_info

# Factory function cho integration
def create_rag_integration(vector_searcher, embedding_service) -> RAGEngineIntegration:
    """
    Create integrated RAG system với KAG + mapping
    """
    return RAGEngineIntegration(vector_searcher, embedding_service)