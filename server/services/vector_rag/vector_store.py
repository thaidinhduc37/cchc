# server/services/vector_rag/vector_store.py  
"""
Vector Store - REBUILT: Simple but smart legal search
"""
import os
import json
import pickle
import asyncio
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import numpy as np
import re

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
    """REBUILT: Smart vector store without hardcoded rules"""
    
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
    
    # MAIN SEARCH METHOD - REBUILT
    async def search(self, query: str, k: int = None, 
                    search_type: str = "normal",
                    filter_metadata: Dict = None,
                    query_entities: List[str] = None) -> List[Dict]:
        """REBUILT: Smart search without hardcoded rules"""
        k = k or config.search_k
        
        try:
            if self.index.ntotal == 0:
                logger.warning("Vector store is empty")
                return []
            
            # Step 1: Analyze query to understand intent
            query_analysis = self._analyze_query(query)
            
            # Step 2: Create search strategies based on analysis
            search_strategies = self._create_search_strategies(query, query_analysis)
            
            # Step 3: Execute multiple searches
            all_results = []
            for strategy in search_strategies:
                results = await self._execute_search_strategy(strategy, k)
                all_results.extend(results)
            
            # Step 4: Merge and deduplicate
            unique_results = self._merge_and_deduplicate(all_results)
            
            # Step 5: Smart ranking based on query intent
            ranked_results = self._smart_ranking(unique_results, query, query_analysis)
            
            # Step 6: Apply entity filtering if provided
            if query_entities:
                ranked_results = self._filter_by_entities(ranked_results, query_entities)
            
            # Step 7: Apply metadata filtering
            if filter_metadata:
                ranked_results = [r for r in ranked_results 
                                if self._match_metadata_filter(r.get('metadata', {}), filter_metadata)]
            
            logger.info(f"🔍 Search: {len(ranked_results)} results for '{query[:50]}...'")
            return ranked_results[:k]
            
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []
    
    def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query to understand legal intent"""
        query_lower = query.lower()
        
        analysis = {
            'legal_terms': [],
            'entities': [],
            'question_type': 'general',
            'legal_domains': [],
            'complexity': 'simple'
        }
        
        # Extract legal terms
        legal_patterns = {
            'articles': r'điều\s+\d+[a-z]?',
            'laws': r'luật\s+[^,\n]+',
            'decrees': r'nghị\s*định\s+số\s+\d+',
            'circulars': r'thông\s*tư\s+số\s+\d+',
            'paragraphs': r'khoản\s+\d+',
            'points': r'điểm\s+[a-z]+'
        }
        
        for term_type, pattern in legal_patterns.items():
            matches = re.findall(pattern, query_lower)
            if matches:
                analysis['legal_terms'].extend([(term_type, match) for match in matches])
        
        # Extract entities
        entity_patterns = {
            'people': r'(?:bị\s+(?:can|cáo|khởi\s+tố)|công\s+dân|người\s+nước\s+ngoài)',
            'documents': r'(?:hộ\s+chiếu|thị\s+thực|visa|giấy\s+tờ)',
            'actions': r'(?:xuất\s+cảnh|nhập\s+cảnh|tạm\s+hoãn|cấm|cấp)'
        }
        
        for entity_type, pattern in entity_patterns.items():
            matches = re.findall(pattern, query_lower)
            if matches:
                analysis['entities'].extend([(entity_type, match) for match in matches])
        
        # Determine question type
        if any(word in query_lower for word in ['có được', 'được không', 'có thể']):
            analysis['question_type'] = 'permission'
        elif any(word in query_lower for word in ['điều kiện', 'yêu cầu']):
            analysis['question_type'] = 'requirements'
        elif any(word in query_lower for word in ['thủ tục', 'cách', 'làm thế nào']):
            analysis['question_type'] = 'procedure'
        elif any(word in query_lower for word in ['phí', 'lệ phí', 'bao nhiêu']):
            analysis['question_type'] = 'cost'
        elif any(word in query_lower for word in ['là gì', 'định nghĩa']):
            analysis['question_type'] = 'definition'
        
        # Detect legal domains dynamically
        domain_indicators = {
            'criminal_law': ['khởi tố', 'bị can', 'bị cáo', 'tố tụng', 'hình sự'],
            'immigration_citizens': ['xuất cảnh', 'nhập cảnh', 'công dân', 'hộ chiếu'],
            'immigration_foreigners': ['người nước ngoài', 'thị thực', 'visa'],
            'administrative': ['vi phạm hành chính', 'xử phạt']
        }
        
        for domain, indicators in domain_indicators.items():
            if any(indicator in query_lower for indicator in indicators):
                analysis['legal_domains'].append(domain)
        
        # Determine complexity
        if len(analysis['legal_terms']) > 2 or len(analysis['legal_domains']) > 1:
            analysis['complexity'] = 'complex'
        elif analysis['legal_terms'] or analysis['legal_domains']:
            analysis['complexity'] = 'moderate'
        
        return analysis
    
    def _create_search_strategies(self, query: str, analysis: Dict) -> List[Dict]:
        """Create search strategies based on query analysis"""
        strategies = []
        
        # Strategy 1: Direct query search
        strategies.append({
            'type': 'direct',
            'query': query,
            'weight': 1.0
        })
        
        # Strategy 2: Enhanced query with legal terms
        if analysis['legal_terms']:
            enhanced_terms = []
            for term_type, term in analysis['legal_terms']:
                enhanced_terms.append(term)
            
            enhanced_query = f"{query} {' '.join(enhanced_terms)}"
            strategies.append({
                'type': 'enhanced_legal',
                'query': enhanced_query,
                'weight': 1.2
            })
        
        # Strategy 3: Domain-specific searches
        for domain in analysis['legal_domains']:
            domain_keywords = self._get_domain_keywords(domain)
            domain_query = f"{query} {' '.join(domain_keywords[:3])}"
            strategies.append({
                'type': 'domain_specific',
                'query': domain_query,
                'domain': domain,
                'weight': 0.8
            })
        
        # Strategy 4: Entity-focused search
        if analysis['entities']:
            entity_terms = [term for _, term in analysis['entities']]
            entity_query = f"{query} {' '.join(entity_terms)}"
            strategies.append({
                'type': 'entity_focused',
                'query': entity_query,
                'weight': 0.9
            })
        
        # Strategy 5: Cross-domain search for complex queries
        if analysis['complexity'] == 'complex' and len(analysis['legal_domains']) > 1:
            cross_terms = []
            for domain in analysis['legal_domains']:
                cross_terms.extend(self._get_domain_keywords(domain)[:2])
            
            cross_query = f"{query} {' '.join(cross_terms)}"
            strategies.append({
                'type': 'cross_domain',
                'query': cross_query,
                'weight': 1.1
            })
        
        return strategies
    
    def _get_domain_keywords(self, domain: str) -> List[str]:
        """Get keywords for legal domain"""
        domain_keywords = {
            'criminal_law': ['tố tụng hình sự', 'bộ luật', 'điều tra', 'tạm hoãn', 'cấm'],
            'immigration_citizens': ['luật xuất cảnh nhập cảnh', 'công dân việt nam', 'điều kiện'],
            'immigration_foreigners': ['người nước ngoài', 'cư trú', 'tạm trú', 'thường trú'],
            'administrative': ['vi phạm', 'xử phạt', 'hành chính']
        }
        
        return domain_keywords.get(domain, [])
    
    async def _execute_search_strategy(self, strategy: Dict, k: int) -> List[Dict]:
        """Execute a single search strategy"""
        try:
            query_embedding = self.embedding_model.embed_query(strategy['query'])
            
            if not query_embedding:
                return []
            
            # Adjust search parameters based on strategy
            search_k = k * 2 if strategy['type'] == 'direct' else k
            threshold = self.similarity_threshold * 0.8 if strategy['type'] == 'cross_domain' else self.similarity_threshold
            
            # Perform vector search
            query_vector = np.array([query_embedding], dtype=np.float32)
            faiss.normalize_L2(query_vector)
            
            similarities, indices = self.index.search(query_vector, min(search_k, len(self.documents)))
            
            results = []
            for similarity, doc_idx in zip(similarities[0], indices[0]):
                if doc_idx >= len(self.documents) or similarity < threshold:
                    continue
                
                result = {
                    'content': self.documents[doc_idx],
                    'metadata': self.metadatas[doc_idx] if doc_idx < len(self.metadatas) else {},
                    'score': float(similarity),
                    'strategy': strategy['type'],
                    'strategy_weight': strategy['weight'],
                    'index': int(doc_idx)
                }
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            return []
    
    def _merge_and_deduplicate(self, all_results: List[Dict]) -> List[Dict]:
        """Merge results from different strategies and remove duplicates"""
        seen_indices = set()
        unique_results = []
        
        # Sort by strategy weight first
        all_results.sort(key=lambda x: x.get('strategy_weight', 0), reverse=True)
        
        for result in all_results:
            doc_index = result.get('index')
            if doc_index not in seen_indices:
                seen_indices.add(doc_index)
                unique_results.append(result)
        
        return unique_results
    
    def _smart_ranking(self, results: List[Dict], query: str, analysis: Dict) -> List[Dict]:
        """Smart ranking based on query analysis"""
        query_lower = query.lower()
        
        for result in results:
            content_lower = result['content'].lower()
            base_score = result['score']
            bonus_score = 0.0
            
            # Bonus for legal term matches
            for term_type, term in analysis['legal_terms']:
                if term in content_lower:
                    if term_type == 'articles':
                        bonus_score += 0.3  # High bonus for specific articles
                    elif term_type == 'laws':
                        bonus_score += 0.2
                    else:
                        bonus_score += 0.1
            
            # Bonus for entity matches
            for entity_type, entity in analysis['entities']:
                if entity in content_lower:
                    if entity_type == 'people':
                        bonus_score += 0.2
                    elif entity_type == 'actions':
                        bonus_score += 0.15
                    else:
                        bonus_score += 0.1
            
            # Bonus for question type relevance
            if analysis['question_type'] == 'permission':
                permission_indicators = ['được', 'không được', 'có thể', 'cấm', 'cho phép']
                permission_matches = sum(1 for indicator in permission_indicators if indicator in content_lower)
                bonus_score += permission_matches * 0.1
            
            elif analysis['question_type'] == 'requirements':
                requirement_indicators = ['điều kiện', 'yêu cầu', 'phải', 'cần']
                requirement_matches = sum(1 for indicator in requirement_indicators if indicator in content_lower)
                bonus_score += requirement_matches * 0.1
            
            # Strategy weight bonus
            strategy_bonus = (result.get('strategy_weight', 1.0) - 1.0) * 0.1
            
            # Calculate final score
            result['final_score'] = base_score + bonus_score + strategy_bonus
            result['bonus_breakdown'] = {
                'legal_terms': sum(0.1 for _, term in analysis['legal_terms'] if term in content_lower),
                'entities': sum(0.1 for _, entity in analysis['entities'] if entity in content_lower),
                'question_type': bonus_score - sum(0.1 for _, term in analysis['legal_terms'] if term in content_lower) - sum(0.1 for _, entity in analysis['entities'] if entity in content_lower),
                'strategy': strategy_bonus
            }
        
        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)
        return results
    
    def _filter_by_entities(self, results: List[Dict], query_entities: List[str]) -> List[Dict]:
        """Filter results by entity relevance"""
        if not query_entities:
            return results
        
        filtered_results = []
        
        for result in results:
            content_lower = result['content'].lower()
            entity_matches = sum(1 for entity in query_entities if entity.lower() in content_lower)
            
            # Keep results with at least some entity matches
            if entity_matches > 0:
                result['entity_match_score'] = entity_matches / len(query_entities)
                filtered_results.append(result)
        
        return filtered_results
    
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
    
    # COMPREHENSIVE SEARCH FOR COMPLEX QUERIES
    async def search_comprehensive(self, query: str, k: int = None) -> List[Dict]:
        """Comprehensive search for complex legal queries"""
        k = k or config.search_k
        
        try:
            # Analyze query complexity
            analysis = self._analyze_query(query)
            
            if analysis['complexity'] == 'simple':
                # Use regular search for simple queries
                return await self.search(query, k=k)
            
            # For complex queries, use expanded search
            expanded_k = k * 3
            
            # Create comprehensive search strategies
            strategies = self._create_search_strategies(query, analysis)
            
            # Add additional semantic variations
            semantic_variations = self._generate_semantic_variations(query, analysis)
            for variation in semantic_variations:
                strategies.append({
                    'type': 'semantic_variation',
                    'query': variation,
                    'weight': 0.7
                })
            
            # Execute all strategies
            all_results = []
            for strategy in strategies:
                results = await self._execute_search_strategy(strategy, expanded_k // len(strategies))
                all_results.extend(results)
            
            # Advanced processing for comprehensive results
            unique_results = self._merge_and_deduplicate(all_results)
            ranked_results = self._smart_ranking(unique_results, query, analysis)
            
            # Additional filtering for comprehensive search
            filtered_results = self._filter_comprehensive_results(ranked_results, query, analysis)
            
            logger.info(f"🔍 Comprehensive search: {len(filtered_results)} results")
            return filtered_results[:k*2]  # Return more results for comprehensive search
            
        except Exception as e:
            logger.error(f"❌ Comprehensive search failed: {e}")
            return await self.search(query, k=k)
    
    def _generate_semantic_variations(self, query: str, analysis: Dict) -> List[str]:
        """Generate semantic variations of the query"""
        variations = []
        
        # Synonym replacement
        synonyms = {
            'có được': ['được phép', 'có thể', 'được'],
            'bị khởi tố': ['bị truy tố', 'bị điều tra', 'bị can'],
            'xuất cảnh': ['ra nước ngoài', 'đi nước ngoài'],
            'điều kiện': ['yêu cầu', 'quy định']
        }
        
        query_lower = query.lower()
        for original, replacements in synonyms.items():
            if original in query_lower:
                for replacement in replacements:
                    variation = query_lower.replace(original, replacement)
                    variations.append(variation)
        
        # Add context variations based on legal domains
        for domain in analysis['legal_domains']:
            domain_keywords = self._get_domain_keywords(domain)
            for keyword in domain_keywords[:2]:
                variations.append(f"{query} {keyword}")
        
        return variations[:5]  # Limit variations
    
    def _filter_comprehensive_results(self, results: List[Dict], query: str, analysis: Dict) -> List[Dict]:
        """Additional filtering for comprehensive search results"""
        # Remove very low relevance results
        min_score = 0.1 if analysis['complexity'] == 'complex' else 0.15
        
        filtered = []
        for result in results:
            if result['final_score'] >= min_score:
                filtered.append(result)
        
        return filtered
    
    # UTILITY METHODS
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
        
        for file_path in [self.index_file, self.docs_file, self.meta_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        logger.info("🗑️ Vector store cleared")