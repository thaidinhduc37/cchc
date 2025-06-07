# server/services/vector_rag/rag_engine.py
"""
RAG Engine - OPTIMIZED & STREAMLINED
"""
import asyncio
import re
from typing import Dict, Any, List
from datetime import datetime
import logging

from services.vector_rag.rag_config import config
from services.vector_rag.document_processor import DocumentProcessor
from services.vector_rag.web_processor import WebProcessor
from services.vector_rag.vector_store import VectorStore
from services.vector_rag.llm_handler import LLMHandler
from services.vector_rag.query_classifier import VietnameseQueryClassifier
from services.vector_rag.context_optimizer import VietnameseContextOptimizer

logger = logging.getLogger(__name__)

class RAGEngine:
    """Streamlined RAG Engine"""
    
    def __init__(self):
        # Core components
        self.document_processor = DocumentProcessor()
        self.web_processor = WebProcessor()
        self.vector_store = VectorStore()
        self.llm_handler = LLMHandler()
        self.query_classifier = VietnameseQueryClassifier()
        self.context_optimizer = VietnameseContextOptimizer()
        
        # Settings
        self.min_confidence = 0.25
        self.is_initialized = False
        
        logger.info("🚀 RAG Engine initialized")
    
    async def initialize(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Initialize system"""
        try:
            logger.info("🔧 Initializing RAG system...")
            
            # Initialize vector store
            vector_result = await self.vector_store.initialize(force_rebuild=force_rebuild)
            
            if not vector_result['success']:
                return {
                    'success': False,
                    'message': f"Vector store failed: {vector_result['message']}"
                }
            
            # Check LLM providers
            llm_status = self.llm_handler.get_provider_status()
            available_providers = [name for name, info in llm_status['providers'].items() 
                                 if info['available']]
            
            if not available_providers:
                self.llm_handler.refresh_providers()
            
            self.is_initialized = True
            
            return {
                'success': True,
                'message': 'RAG initialized successfully',
                'components': {
                    'vector_store': vector_result,
                    'llm_providers': available_providers
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return {'success': False, 'message': f"Failed: {e}"}
    
    async def query(self, question: str) -> Dict[str, Any]:
        """Process query - streamlined"""
        start_time = datetime.now()
        
        if not self.is_initialized:
            return {
                'success': False,
                'answer': "❌ RAG system chưa khởi tạo",
                'error': 'not_initialized'
            }
        
        try:
            logger.info(f"🎯 Processing: {question[:50]}...")
            
            # 1. Classify query
            features = self.query_classifier.classify(question)
            
            # 2. Execute search
            search_results = await self._search(question, features)
            
            if not search_results:
                return self._no_data_response(question, start_time)
            
            # 3. Optimize context
            context = self.context_optimizer.optimize_context(search_results, features)
            
            logger.info(f"📊 Context: {context.context_type}, conf: {context.confidence_score:.2f}")
            
            # 4. Generate response
            if context.confidence_score >= self.min_confidence:
                response = await self._generate_response(question, context)
            else:
                response = self._no_data_response(question, start_time)
            
            # 5. Add metadata
            response['metadata'] = {
                'response_time': (datetime.now() - start_time).total_seconds(),
                'context_sources': context.total_sources,
                'context_type': context.context_type,
                'query_intent': features.primary_intent
            }
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return {
                'success': False,
                'answer': f"❌ Lỗi hệ thống: {str(e)}",
                'error': str(e),
                'metadata': {
                    'response_time': (datetime.now() - start_time).total_seconds()
                }
            }
    
    async def _search(self, query: str, features: Any) -> List[Dict]:
        """Execute search based on strategy"""
        strategy = features.search_strategy
        all_results = []
        
        try:
            if strategy == 'vector_priority':
                # Vector first, then web
                vector_results = await self._vector_search(query, features, k=7)
                web_results = await self._web_search(query, features, k=2)
                all_results = vector_results + web_results
                
            elif strategy == 'web_priority':
                # Web first, then vector
                web_results = await self._web_search(query, features, k=5)
                vector_results = await self._vector_search(query, features, k=3)
                all_results = web_results + vector_results
                
            else:  # hybrid
                # Parallel search
                vector_task = self._vector_search(query, features, k=5)
                web_task = self._web_search(query, features, k=3)
                
                vector_results, web_results = await asyncio.gather(
                    vector_task, web_task, return_exceptions=True
                )
                
                if isinstance(vector_results, list):
                    all_results.extend(vector_results)
                if isinstance(web_results, list):
                    all_results.extend(web_results)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
        
        return all_results
    
    async def _vector_search(self, query: str, features: Any, k: int = 5) -> List[Dict]:
        """Vector search"""
        try:
            # Optimize query for vector
            optimized_query = self.query_classifier.format_query_for_vector(query, features)
            
            # Search type
            search_type = "exact_legal" if features.has_specific_article else "normal"
            
            results = await self.vector_store.search(optimized_query, k=k, search_type=search_type)
            logger.info(f"✅ Vector: {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"❌ Vector search error: {e}")
            return []
    
    async def _web_search(self, query: str, features: Any, k: int = 3) -> List[Dict]:
        """Web search"""
        try:
            procedures = await self.web_processor.search_procedures(query)
            
            web_results = []
            for procedure in procedures[:k]:
                formatted_content = self.web_processor.format_for_rag(procedure)
                
                if formatted_content and len(formatted_content) >= 100:
                    web_result = {
                        'content': formatted_content,
                        'metadata': {
                            'title': procedure.get('title', 'Unknown'),
                            'code': procedure.get('code', ''),
                            'content_type': 'web_procedure'
                        },
                        'score': procedure.get('relevance_score', 0.5)
                    }
                    web_results.append(web_result)
            
            logger.info(f"✅ Web: {len(web_results)} procedures")
            return web_results
            
        except Exception as e:
            logger.error(f"❌ Web search error: {e}")
            return []
    
    async def _generate_response(self, query: str, context: Any) -> Dict[str, Any]:
        """Generate LLM response"""
        try:
            if not context.context or len(context.context.strip()) < 100:
                return {
                    'success': False,
                    'answer': "Không đủ thông tin để trả lời.",
                    'reason': 'insufficient_context'
                }
            
            response = await self.llm_handler.generate_response(query, context.context)
            
            if response['success']:
                return {
                    'success': True,
                    'answer': response['response'],
                    'provider': response.get('provider', 'unknown'),
                    'context_confidence': context.confidence_score,
                    'sources': context.source_summary
                }
            else:
                return {
                    'success': False,
                    'answer': "Không thể tạo phản hồi.",
                    'error': response.get('error', 'llm_error')
                }
                
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {
                'success': False,
                'answer': f"Lỗi tạo phản hồi: {str(e)}",
                'error': str(e)
            }
    
    def _no_data_response(self, query: str, start_time: datetime) -> Dict[str, Any]:
        """Response when no data found"""
        suggestions = self._get_suggestions(query)
        
        return {
            'success': True,
            'answer': "Xin lỗi, tôi không tìm thấy thông tin phù hợp để trả lời câu hỏi của bạn. " +
                     "Vui lòng thử diễn đạt lại hoặc liên hệ cơ quan có thẩm quyền.",
            'reason': 'no_relevant_data',
            'suggestions': suggestions,
            'metadata': {
                'response_time': (datetime.now() - start_time).total_seconds()
            }
        }
    
    def _get_suggestions(self, query: str) -> List[str]:
        """Generate suggestions"""
        query_lower = query.lower()
        
        if any(term in query_lower for term in ['hộ chiếu', 'passport']):
            return [
                "Điều kiện cấp hộ chiếu phổ thông",
                "Hồ sơ làm hộ chiếu",
                "Thời gian và lệ phí làm hộ chiếu"
            ]
        elif any(term in query_lower for term in ['thị thực', 'visa']):
            return [
                "Thủ tục cấp thị thực",
                "Điều kiện gia hạn thị thực",
                "Miễn thị thực"
            ]
        elif any(term in query_lower for term in ['tạm trú', 'thường trú']):
            return [
                "Thủ tục cấp thẻ tạm trú",
                "Điều kiện chuyển tạm trú thành thường trú",
                "Gia hạn thẻ tạm trú"
            ]
        
        return [
            "Thủ tục xuất nhập cảnh",
            "Cấp hộ chiếu",
            "Cấp thị thực"
        ]
    
    async def rebuild_vector_store(self) -> Dict[str, Any]:
        """Rebuild vector store (calls external build script)"""
        try:
            logger.info("📚 Rebuilding vector store...")
            return await self.vector_store.initialize(force_rebuild=True)
        except Exception as e:
            logger.error(f"❌ Rebuild failed: {e}")
            return {'success': False, 'message': f'Rebuild failed: {e}'}
    
    async def search_only(self, query: str) -> Dict[str, Any]:
        """Search without LLM generation (for debugging)"""
        try:
            logger.info(f"🔍 Search only: {query[:50]}...")
            
            # Classify query
            features = self.query_classifier.classify(query)
            
            # Execute search
            search_results = await self._search(query, features)
            
            # Optimize context
            context = self.context_optimizer.optimize_context(search_results, features)
            
            return {
                'success': True,
                'query_features': {
                    'intent': features.primary_intent,
                    'confidence': features.confidence,
                    'search_strategy': features.search_strategy,
                    'has_legal_article': features.has_specific_article
                },
                'search_results': len(search_results),
                'context_info': {
                    'context_type': context.context_type,
                    'confidence': context.confidence_score,
                    'sources': context.total_sources,
                    'context_length': len(context.context)
                },
                'raw_context': context.context[:500] + "..." if len(context.context) > 500 else context.context
            }
            
        except Exception as e:
            logger.error(f"❌ Search only failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            'is_initialized': self.is_initialized,
            'components': {
                'vector_store': self.vector_store.get_stats(),
                'web_processor': self.web_processor.get_stats(),
                'llm_handler': self.llm_handler.get_provider_status()
            },
            'settings': {
                'min_confidence': self.min_confidence
            }
        }
    
    def clear_cache(self):
        """Clear all caches"""
        try:
            self.vector_store.embedding_model.clear_cache()
            self.web_processor.clear_cache()
            logger.info("🗑️ All caches cleared")
        except Exception as e:
            logger.error(f"❌ Clear cache failed: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """System health check"""
        health = {
            'system_status': 'healthy' if self.is_initialized else 'not_initialized',
            'components': {},
            'issues': []
        }
        
        # Check vector store
        try:
            vs_stats = self.vector_store.get_stats()
            health['components']['vector_store'] = {
                'status': 'healthy' if vs_stats['total_documents'] > 0 else 'empty',
                'documents': vs_stats['total_documents']
            }
            if vs_stats['total_documents'] == 0:
                health['issues'].append('Vector store is empty')
        except Exception as e:
            health['components']['vector_store'] = {'status': 'error', 'error': str(e)}
            health['issues'].append(f'Vector store error: {e}')
        
        # Check LLM providers
        try:
            llm_status = self.llm_handler.get_provider_status()
            available_providers = [name for name, info in llm_status['providers'].items() 
                                 if info['available']]
            
            health['components']['llm'] = {
                'status': 'healthy' if available_providers else 'no_providers',
                'available_providers': available_providers
            }
            if not available_providers:
                health['issues'].append('No LLM providers available')
        except Exception as e:
            health['components']['llm'] = {'status': 'error', 'error': str(e)}
            health['issues'].append(f'LLM error: {e}')
        
        # Check web processor
        try:
            web_stats = self.web_processor.get_stats()
            health['components']['web_processor'] = {
                'status': 'healthy',
                'cached_procedures': web_stats['cached_procedures']
            }
        except Exception as e:
            health['components']['web_processor'] = {'status': 'error', 'error': str(e)}
            health['issues'].append(f'Web processor error: {e}')
        
        # Overall status
        if health['issues']:
            health['system_status'] = 'degraded' if self.is_initialized else 'unhealthy'
        
        return health