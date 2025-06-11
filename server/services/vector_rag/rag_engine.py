# server/services/vector_rag/rag_engine.py
"""
RAG Engine - CẬP NHẬT: Tích hợp logic mới
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
    """RAG Engine với logic mới"""
    
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
        
        # CẬP NHẬT: Chat history cho normalization
        self.chat_history = []
        self.max_history = 5
        
        logger.info("🚀 RAG Engine initialized với logic mới")
    
    async def initialize(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Initialize system"""
        try:
            logger.info("🔧 Initializing RAG system...")
            
            vector_result = await self.vector_store.initialize(force_rebuild=force_rebuild)
            
            if not vector_result['success']:
                return {
                    'success': False,
                    'message': f"Vector store failed: {vector_result['message']}"
                }
            
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
    
    async def query(self, question: str, session_id: str = None) -> Dict[str, Any]:
        """CẬP NHẬT: Process query với normalization và chat history"""
        start_time = datetime.now()
        
        if not self.is_initialized:
            return {
                'success': False,
                'answer': "❌ RAG system chưa khởi tạo",
                'error': 'not_initialized'
            }
        
        try:
            logger.info(f"🎯 Processing: {question[:50]}...")
            
            # 1. CẬP NHẬT: Classify với chat history
            features = self.query_classifier.classify(question, self.chat_history)
            
            # Log normalization results
            if features.context_needed:
                logger.info(f"📝 Normalized: '{features.original_query}' → '{features.normalized_query}'")
            
            # 2. Execute search với enhanced query
            search_results = await self._search_enhanced(features)
            
            if not search_results:
                return self._no_data_response(question, start_time)
            
            # 3. Optimize context với separated sections
            context = self.context_optimizer.optimize_context(search_results, features)
            
            logger.info(f"📊 Context: {context.context_type}, conf: {context.confidence_score:.2f}")
            logger.info(f"📋 Sources: Legal={context.vector_sources}, Procedure={context.web_sources}")
            
            # 4. Generate response với smart prompts
            if context.confidence_score >= self.min_confidence:
                response = await self._generate_response(features.normalized_query, context)
            else:
                response = self._no_data_response(question, start_time)
            
            # 5. CẬP NHẬT: Update chat history
            self._update_chat_history(question)
            
            # 6. Add enhanced metadata
            response['metadata'] = {
                'response_time': (datetime.now() - start_time).total_seconds(),
                'context_sources': context.total_sources,
                'context_type': context.context_type,
                'query_intent': features.primary_intent,
                'query_normalized': features.context_needed,
                'original_query': features.original_query,
                'normalized_query': features.normalized_query,
                'extracted_entities': features.extracted_entities
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
    
    def _update_chat_history(self, question: str):
            """CẬP NHẬT: Update chat history cho context"""
            self.chat_history.append(question)
            
            # Keep only last N messages
            if len(self.chat_history) > self.max_history:
                self.chat_history = self.chat_history[-self.max_history:]
        
    async def _search_enhanced(self, features: Any) -> List[Dict]:
        """SỬA LOGIC: Enhanced search với nhiều results hơn"""
        strategy = features.search_strategy
        all_results = []
        
        try:
            if strategy == 'vector_priority':
                # SỬA: Tăng mạnh để extract đủ legal content  
                vector_results = await self._vector_search_enhanced(features, k=15)  # TỪ 7 → 15
                web_results = await self._web_search(features.normalized_query, features, k=2)
                all_results = vector_results + web_results
                
            elif strategy == 'web_priority':
                web_results = await self._web_search(features.normalized_query, features, k=5)
                # SỬA: Tăng vector backup
                vector_results = await self._vector_search_enhanced(features, k=5)  # TỪ 3 → 5
                all_results = web_results + vector_results
                
            else:  # hybrid
                # SỬA: Tăng cả hai cho hybrid
                vector_task = self._vector_search_enhanced(features, k=8)    # TỪ 5 → 8
                web_task = self._web_search(features.normalized_query, features, k=4)  # TỪ 3 → 4
                
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
    
    async def _vector_search_enhanced(self, features: Any, k: int = 5) -> List[Dict]:
        """SỬA LOGIC: Vector search với comprehensive extraction"""
        try:
            optimized_query = self.query_classifier.format_query_for_vector(
                features.normalized_query, features
            )
            
            # SỬA: Sử dụng comprehensive search cho legal queries
            if features.primary_intent == 'LEGAL' or features.has_specific_article:
                # Use comprehensive search để extract tất cả content liên quan
                results = await self.vector_store.search_comprehensive(
                    optimized_query, 
                    k=k
                )
                logger.info(f"✅ Comprehensive search: {len(results)} results")
            else:
                # Normal search cho non-legal queries
                results = await self.vector_store.search(
                    optimized_query, 
                    k=k*2, 
                    search_type="normal",
                    query_entities=features.extracted_entities
                )
                logger.info(f"✅ Normal search: {len(results)} results")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Vector search error: {e}")
            return []
    
    async def _web_search(self, query: str, features: Any, k: int = 3) -> List[Dict]:
        """Web search (unchanged)"""
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
        """Generate LLM response (unchanged)"""
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
                    'prompt_type': response.get('prompt_type', 'unknown'),
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
    
    async def search_only(self, query: str) -> Dict[str, Any]:
        """CẬP NHẬT: Search only với debug info"""
        try:
            logger.info(f"🔍 Search only: {query[:50]}...")
            
            # Classify with normalization
            features = self.query_classifier.classify(query, self.chat_history)
            
            # Execute search
            search_results = await self._search_enhanced(features)
            
            # Optimize context
            context = self.context_optimizer.optimize_context(search_results, features)
            
            return {
                'success': True,
                'query_analysis': {
                    'original_query': features.original_query,
                    'normalized_query': features.normalized_query,
                    'intent': features.primary_intent,
                    'confidence': features.confidence,
                    'search_strategy': features.search_strategy,
                    'has_legal_article': features.has_specific_article,
                    'extracted_entities': features.extracted_entities,
                    'context_added': features.context_needed
                },
                'search_results': len(search_results),
                'context_info': {
                    'context_type': context.context_type,
                    'confidence': context.confidence_score,
                    'total_sources': context.total_sources,
                    'legal_sources': context.vector_sources,
                    'procedure_sources': context.web_sources,
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
    
    # Các method khác giữ nguyên
    async def rebuild_vector_store(self) -> Dict[str, Any]:
        """Rebuild vector store"""
        try:
            logger.info("📚 Rebuilding vector store...")
            return await self.vector_store.initialize(force_rebuild=True)
        except Exception as e:
            logger.error(f"❌ Rebuild failed: {e}")
            return {'success': False, 'message': f'Rebuild failed: {e}'}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        return {
            'is_initialized': self.is_initialized,
            'chat_history_length': len(self.chat_history),
            'components': {
                'vector_store': self.vector_store.get_stats(),
                'web_processor': self.web_processor.get_stats(),
                'llm_handler': self.llm_handler.get_provider_status()
            },
            'settings': {
                'min_confidence': self.min_confidence,
                'max_chat_history': self.max_history
            }
        }
    
    def clear_chat_history(self):
        """Clear chat history"""
        self.chat_history = []
        logger.info("🗑️ Chat history cleared")
    
    def clear_cache(self):
        """Clear all caches"""
        try:
            self.vector_store.embedding_model.clear_cache()
            self.web_processor.clear_cache()
            self.clear_chat_history()
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