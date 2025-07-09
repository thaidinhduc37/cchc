# server/services/vector_rag/rag_engine.py - SIMPLIFIED: Focus on core RAG pipeline

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from services.vector_rag.rag_config import config
from services.vector_rag.vector_store import VectorSearcher
from services.vector_rag.reranker import ReRanker
from services.vector_rag.llm_handler import LLMHandler
from services.vector_rag.context_optimizer import ContextOptimizer

logger = logging.getLogger(__name__)

class RAGEngine:
    """
    SIMPLIFIED RAG Engine - Focus on core pipeline
    
    FLOW: Unified Input → Vector Search → Rerank → Context → Generate → Response
    NO MORE: Query classification (moved to Unified)
    """
    
    def __init__(self):
        # Core pipeline components
        self.vector_searcher = VectorSearcher() 
        self.reranker = ReRanker()
        self.context_optimizer = ContextOptimizer()
        self.llm_handler = LLMHandler()
        
        # Simple tracking
        self.is_initialized = False
        self.stats = {
            'total_queries': 0,
            'successful_responses': 0,
            'avg_response_time': 0.0,
            'pipeline_errors': 0
        }
        
        logger.info("🎯 SIMPLIFIED RAG Engine initialized")
    
    async def initialize(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Initialize RAG Engine components"""
        try:
            # Initialize vector searcher
            vector_init = await self.vector_searcher.initialize()
            if not vector_init.get('success'):
                return {
                    'success': False,
                    'message': f"Vector searcher failed: {vector_init.get('message', 'Unknown error')}"
                }
            
            # Get document count
            vector_stats = self.vector_searcher.get_stats()
            total_docs = vector_stats.get('documents_loaded', 0)
            
            if total_docs == 0:
                return {
                    'success': False,
                    'message': 'No documents in vector store. Build indices first.'
                }
            
            # Check LLM providers
            llm_status = self.llm_handler.get_provider_status()
            has_providers = llm_status['gemini_available'] or llm_status['ollama_available']
            
            if not has_providers:
                logger.warning("⚠️ No LLM providers - will use fallback responses")
            
            self.is_initialized = True
            
            return {
                'success': True,
                'message': f'Simplified RAG Engine ready with {total_docs} documents',
                'pipeline_info': {
                    'vector_searcher': 'Ready',
                    'reranker': 'Ready - accuracy-first',
                    'context_optimizer': 'Ready',
                    'llm_handler': f'Ready - {len([p for p, s in llm_status.items() if "available" in p and s])} providers'
                },
                'features': [
                    'Simplified 4-step pipeline',
                    'Unified input processing',
                    'Enhanced context awareness',
                    'Optimized performance'
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ RAG Engine init failed: {e}")
            return {'success': False, 'message': f'Initialization failed: {str(e)}'}
    
    async def query(self, processed_query: str, session_id: str = None, unified_data: dict = None) -> Dict[str, Any]:
        """
        SIMPLIFIED Query Processing - 4 steps only
        
        INPUT from Unified:
        - processed_query: cleaned & resolved query
        - unified_data: intent analysis + context from Unified
        """
        start_time = datetime.now()
        self.stats['total_queries'] += 1
        
        if not self.is_initialized:
            return self._create_error_response('RAG Engine not initialized')
        
        if not processed_query or not processed_query.strip():
            return self._create_error_response('Empty query provided')
        
        processed_query = processed_query.strip()
        unified_data = unified_data or {}
        
        logger.info(f"🎯 RAG Pipeline: '{processed_query[:50]}...'")
        
        try:
            # === STEP 1: ENHANCED VECTOR SEARCH ===
            logger.debug("🔍 Step 1: Enhanced Vector Search...")
            
            try:
                search_results = await self.vector_searcher.search(
                    processed_query,
                    query_features=self._extract_search_hints(unified_data),
                    k=config.search_k * 2
                )
                
                logger.debug(f"✅ Search: {len(search_results)} documents found")
                
                if not search_results:
                    return await self._handle_no_results(processed_query, unified_data)
                
            except Exception as e:
                logger.error(f"❌ Step 1 failed: {e}")
                self.stats['pipeline_errors'] += 1
                return await self._handle_pipeline_error(processed_query, "search", unified_data)
            
            # === STEP 2: ENHANCED RERANKING ===
            logger.debug("🎯 Step 2: Enhanced Reranking...")
            
            try:
                reranked_results = self.reranker.rerank(
                    query=processed_query,
                    chunks=search_results,
                    context_tier='general',
                    query_features=self._extract_rerank_context(unified_data)
                )
                
                logger.debug(f"✅ Reranking: {len(reranked_results)} results processed")
                
                if not reranked_results:
                    return await self._handle_no_results(processed_query, unified_data)
                
            except Exception as e:
                logger.error(f"❌ Step 2 failed: {e}")
                self.stats['pipeline_errors'] += 1
                return await self._handle_pipeline_error(processed_query, "rerank", unified_data)
            
            # === STEP 3: CONTEXT OPTIMIZATION ===
            logger.debug("🎨 Step 3: Context Optimization...")
            
            try:
                optimized_context = await self.context_optimizer.optimize_context(
                    reranked_results, 
                    self._extract_context_features(unified_data)
                )
                
                logger.debug(f"✅ Context optimization completed")
                
            except Exception as e:
                logger.error(f"❌ Step 3 failed: {e}")
                self.stats['pipeline_errors'] += 1
                return await self._handle_pipeline_error(processed_query, "context", unified_data)
            
            # === STEP 4: RESPONSE GENERATION ===
            logger.debug("🤖 Step 4: Response Generation...")
            
            try:
                response_result = await self.llm_handler.generate_response(
                    processed_query,
                    optimized_context,
                    self._extract_generation_context(unified_data)
                )
                
                if not response_result.get('success'):
                    raise Exception("LLM generation failed")
                
                logger.debug(f"✅ Response generation completed")
                
            except Exception as e:
                logger.error(f"❌ Step 4 failed: {e}")
                self.stats['pipeline_errors'] += 1
                return await self._handle_llm_failure(processed_query, optimized_context, unified_data)
            
            # === SUCCESS: COMPILE RESPONSE ===
            total_time = (datetime.now() - start_time).total_seconds()
            self._update_success_stats(total_time)
            
            # Enhanced response with metadata
            final_response = {
                'success': True,
                'answer': response_result['answer'],
                'sources': response_result.get('sources', ''),
                'pipeline_info': {
                    'version': 'Simplified RAG Pipeline v2.0',
                    'total_time': total_time,
                    'documents_processed': len(search_results),
                    'unified_data_used': bool(unified_data),
                    'generation_method': response_result.get('provider', 'unknown')
                },
                'metadata': response_result.get('metadata', {})
            }
            
            logger.info(f"✅ RAG Pipeline completed in {total_time:.2f}s")
            return final_response
            
        except Exception as e:
            logger.error(f"❌ RAG pipeline failed: {e}")
            self.stats['pipeline_errors'] += 1
            return await self._handle_system_error(processed_query, unified_data)
    
    def _extract_search_hints(self, unified_data: dict) -> dict:
        """Extract search hints from unified data"""
        intent_analysis = unified_data.get('intent_analysis', {})
        
        return {
            'needs_conclusion': intent_analysis.get('needs_conclusion', False),
            'is_procedure': intent_analysis.get('is_procedure', False),
            'age_constraint': intent_analysis.get('age_constraint'),
            'legal_status': intent_analysis.get('legal_status'),
            'confidence': intent_analysis.get('confidence', 0.6)
        }
    
    def _extract_rerank_context(self, unified_data: dict) -> dict:
        """Extract reranking context from unified data"""
        intent_analysis = unified_data.get('intent_analysis', {})
        
        return {
            'intent_type': intent_analysis.get('intent_summary', {}).get('type', 'general'),
            'has_constraints': intent_analysis.get('intent_summary', {}).get('has_constraints', False),
            'confidence_level': intent_analysis.get('intent_summary', {}).get('confidence_level', 'medium'),
            'original_query': unified_data.get('original_query', ''),
            'context_used': unified_data.get('resolution', {}).get('context_used', False)
        }
    
    def _extract_context_features(self, unified_data: dict) -> dict:
        """Extract context features from unified data"""
        return {
            'original_query': unified_data.get('original_query', ''),
            'needs_conclusion': unified_data.get('intent_analysis', {}).get('needs_conclusion', False),
            'has_constraints': unified_data.get('intent_analysis', {}).get('intent_summary', {}).get('has_constraints', False)
        }
    
    def _extract_generation_context(self, unified_data: dict) -> dict:
        """Extract generation context from unified data"""
        return {
            'original_query': unified_data.get('original_query', ''),
            'intent_analysis': unified_data.get('intent_analysis', {}),
            'context_info': unified_data.get('resolution', {})
        }
    
    async def _handle_no_results(self, query: str, unified_data: dict) -> Dict[str, Any]:
        """Handle no search results"""
        original_query = unified_data.get('original_query', query)
        
        response = f"""Chào bạn, dựa trên quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam, tôi xin trả lời câu hỏi: "{original_query}" như sau:

Không tìm thấy thông tin cụ thể cho câu hỏi này trong cơ sở dữ liệu hiện tại.

📞 **Để được tư vấn trực tiếp:**
• Hotline: 069.1000.000
• Website: https://dichvucong.bocongan.gov.vn

Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
        
        return {
            'success': True,
            'answer': response,
            'method': 'no_results_fallback',
            'pipeline_info': {'documents_found': 0}
        }
    
    async def _handle_pipeline_error(self, query: str, stage: str, unified_data: dict) -> Dict[str, Any]:
        """Handle pipeline stage errors"""
        original_query = unified_data.get('original_query', query)
        
        response = f"""Chào bạn, dựa trên quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam, tôi xin trả lời câu hỏi: "{original_query}" như sau:

Hệ thống gặp sự cố kỹ thuật khi xử lý câu hỏi này.

📞 **Để được hỗ trợ ngay lập tức:**
• Hotline: 069.1000.000
• Website: https://dichvucong.bocongan.gov.vn

Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
        
        return {
            'success': True,
            'answer': response,
            'method': f'{stage}_error_fallback',
            'pipeline_info': {'stage_failed': stage}
        }
    
    async def _handle_llm_failure(self, query: str, context_result: Any, unified_data: dict) -> Dict[str, Any]:
        """Handle LLM failures with context-based response"""
        original_query = unified_data.get('original_query', query)
        
        if hasattr(context_result, 'context') and context_result.context:
            context_preview = context_result.context[:300] + "..." if len(context_result.context) > 300 else context_result.context
            
            response = f"""Chào bạn, dựa trên quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam, tôi xin trả lời câu hỏi: "{original_query}" như sau:

Căn cứ các quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam:

    "{context_preview}"

📞 **Để được tư vấn chi tiết:**
• Hotline: 069.1000.000
• Website: https://dichvucong.bocongan.gov.vn

Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
        else:
            response = f"""Chào bạn, dựa trên quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam, tôi xin trả lời câu hỏi: "{original_query}" như sau:

Hệ thống gặp sự cố kỹ thuật khi tạo phản hồi.

📞 **Để được hỗ trợ:**
• Hotline: 069.1000.000
• Website: https://dichvucong.bocongan.gov.vn

Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
        
        return {
            'success': True,
            'answer': response,
            'method': 'llm_failure_fallback',
            'pipeline_info': {'stage_failed': 'llm', 'context_available': bool(context_result)}
        }
    
    async def _handle_system_error(self, query: str, unified_data: dict) -> Dict[str, Any]:
        """Handle system errors"""
        original_query = unified_data.get('original_query', query)
        
        response = f"""Chào bạn, dựa trên quy định của Luật Xuất cảnh, nhập cảnh của công dân Việt Nam, tôi xin trả lời câu hỏi: "{original_query}" như sau:

Hệ thống gặp sự cố kỹ thuật nghiêm trọng.

📞 **Liên hệ hỗ trợ:**
• Hotline: 069.1000.000
• Website: https://dichvucong.bocongan.gov.vn

Đây là thông tin tham khảo, để được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"""
        
        return {
            'success': True,
            'answer': response,
            'method': 'system_error_fallback',
            'pipeline_info': {'stage_failed': 'system'}
        }
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create standard error response"""
        return {
            'success': False,
            'answer': message,
            'method': 'error_response'
        }
    
    def _update_success_stats(self, response_time: float):
        """Update success statistics"""
        self.stats['successful_responses'] += 1
        
        # Update average response time
        total = self.stats['total_queries']
        current_avg = self.stats['avg_response_time']
        self.stats['avg_response_time'] = (current_avg * (total - 1) + response_time) / total
    
    def get_stats(self) -> Dict[str, Any]:
        """Get simplified pipeline statistics"""
        total = self.stats['total_queries']
        success_rate = self.stats['successful_responses'] / total if total > 0 else 0
        error_rate = self.stats['pipeline_errors'] / total if total > 0 else 0
        
        return {
            'system_info': {
                'version': 'Simplified RAG Pipeline v2.0',
                'status': 'ready' if self.is_initialized else 'not_initialized',
                'pipeline_steps': 4,
                'total_documents': self.vector_searcher.get_stats().get('documents_loaded', 0) if hasattr(self, 'vector_searcher') else 0
            },
            'performance': {
                'total_queries': total,
                'success_rate': round(success_rate, 3),
                'error_rate': round(error_rate, 3),
                'avg_response_time': round(self.stats['avg_response_time'], 3)
            },
            'pipeline_info': {
                'steps': ['Enhanced Vector Search', 'Enhanced Reranking', 'Context Optimization', 'Response Generation'],
                'unified_integration': True,
                'query_preprocessing': 'Handled by Unified Processor'
            }
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for simplified pipeline"""
        health = {'overall_status': 'healthy', 'component_health': {}, 'issues': []}
        
        try:
            # Check components
            components = [
                ('vector_searcher', self.vector_searcher),
                ('reranker', self.reranker),
                ('context_optimizer', self.context_optimizer),
                ('llm_handler', self.llm_handler)
            ]
            
            for name, component in components:
                try:
                    if hasattr(component, 'get_stats'):
                        component.get_stats()
                        health['component_health'][name] = 'healthy'
                    else:
                        health['component_health'][name] = 'unknown'
                except:
                    health['component_health'][name] = 'error'
                    health['issues'].append(f'{name}: component error')
            
            # Check vector store documents
            if hasattr(self.vector_searcher, 'get_stats'):
                vector_stats = self.vector_searcher.get_stats()
                if vector_stats.get('documents_loaded', 0) == 0:
                    health['issues'].append('No documents in vector store')
                    health['overall_status'] = 'degraded'
            
            # Check LLM providers
            llm_status = self.llm_handler.get_provider_status()
            if not (llm_status.get('gemini_available') or llm_status.get('ollama_available')):
                health['issues'].append('No LLM providers available')
                health['overall_status'] = 'degraded'
            
            if health['issues'] and health['overall_status'] == 'healthy':
                health['overall_status'] = 'degraded'
        
        except Exception as e:
            health['overall_status'] = 'error'
            health['issues'].append(f'Health check failed: {str(e)}')
        
        return health
    
    # Convenience methods
    async def quick_query(self, query: str) -> str:
        """Quick query that returns just the answer text"""
        result = await self.query(query)
        return result.get('answer', 'Could not process this question.')
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_queries': 0,
            'successful_responses': 0,
            'avg_response_time': 0.0,
            'pipeline_errors': 0
        }
        logger.info("📊 Simplified RAG Engine statistics reset")