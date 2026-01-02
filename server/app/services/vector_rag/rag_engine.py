# app/services/vector_rag/rag_engine.py - FIXED WITHOUT CONTEXT_OPTIMIZER
"""
RAG Engine - Fixed without context_optimizer
🎯 rag_mapping: điều hướng vector_store (thay thế admin_units.json)
📋 Bỏ: context_optimizer, GIỮ: ResponseContext cho llm_handler
🚀 Flow: unified_processor → rag_engine → rag_mapping → vector_store → reranker (top 3) → ResponseContext → llm_handler
"""
import asyncio
import os
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from dataclasses import dataclass

from app.services.vector_rag.rag_config import config
from app.services.vector_rag.rag_mapping import create_xuatnhapcanh_mapping
from app.services.vector_rag.core.vector_store import VectorSearcher
from app.services.vector_rag.core.reranker import ReRanker
from app.services.vector_rag.llm.llm_handler import LLMHandler


logger = logging.getLogger(__name__)

@dataclass
class ResponseContext:
    """Context for LLM generation - Ngữ cảnh để llm_handler hiểu và trả lời tự nhiên"""
    query: str
    primary_content: str
    primary_citation: str
    context_note: str = ""
    citizen_note: str = ""
    needs_conclusion: bool = False
    supporting_contents: List[str] = None
    context: str = ""
    answer_type: str = "legal"
    
    def __post_init__(self):
        if self.supporting_contents is None:
            self.supporting_contents = []
        if not self.context and self.primary_content:
            self.context = self.primary_content

class RAGEngine:
    """RAG Engine - mapping điều hướng, ResponseContext cho LLM"""
    
    def __init__(self):
        self.vector_searcher = VectorSearcher() 
        self.reranker = ReRanker()
        self.llm_handler = LLMHandler()
        
        # NEW: Domain mapping để điều hướng vector_store (thay admin_units.json)
        self.domain_mapping = create_xuatnhapcanh_mapping()
        
        # REMOVED: context_optimizer 
        
        self.is_initialized = False
        self.stats = {
            'total_queries': 0,
            'with_unified_context': 0,
            'successful_responses': 0,
            'response_context_used': 0,
            'avg_response_time': 0.0,
            'pipeline_errors': 0,
            'mapping_optimizations': 0
        }
        
        logger.info("🎯 RAG Engine với mapping navigation (no context_optimizer)")

    async def initialize(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Initialize RAG Engine"""
        try:
            vector_init = await self.vector_searcher.initialize()
            if not vector_init.get('success'):
                return {
                    'success': False,
                    'message': f"Vector searcher failed: {vector_init.get('message', 'Unknown error')}"
                }
            
            vector_stats = self.vector_searcher.get_stats()
            total_docs = vector_stats.get('documents_loaded', 0)
            
            if total_docs == 0:
                return {
                    'success': False,
                    'message': 'No documents in vector store. Build indices first.'
                }
            
            llm_status = self.llm_handler.get_provider_status()
            has_providers = llm_status.get('any_provider_available', False)
            
            if not has_providers:
                logger.warning("⚠️ No LLM providers - will use fallback responses")
            
            self.is_initialized = True
            
            return {
                'success': True,
                'message': f'RAG Engine ready with {total_docs} documents',
                'capabilities': {
                    'mapping_navigation': True,
                    'top3_result_selection': True,
                    'response_context_for_llm': True,
                    'no_complex_context_processing': True
                }
            }
            
        except Exception as e:
            logger.error(f"❌ RAG Engine init failed: {e}")
            return {'success': False, 'message': f'Initialization failed: {str(e)}'}
    
    async def query(self, processed_query: str, session_id: str = None, unified_data: dict = None) -> Dict[str, Any]:
        """
        Main query processing - mapping navigation + ResponseContext for LLM
        """
        start_time = datetime.now()
        self.stats['total_queries'] += 1
        
        if not self.is_initialized:
            return self._create_error_response('RAG Engine not initialized')
        
        if not processed_query or not processed_query.strip():
            return self._create_error_response('Empty query provided')
        
        # Extract unified context - SIMPLIFIED (no complex processing)
        unified_context = self._extract_simple_context(unified_data)
        
        if unified_context['has_context']:
            self.stats['with_unified_context'] += 1
            logger.info(f"🎯 Processing with context: {unified_context['summary']}")
        
        logger.info(f"🔍 RAG: '{processed_query[:50]}...'")
        
        try:
            # STEP 1: Enhanced search với mapping navigation
            search_results = await self._enhanced_search(
                processed_query, 
                unified_context,
                k=config.search_k * 2
            )
            
            if not search_results:
                return await self._handle_no_results(processed_query, unified_context)
            
            logger.debug(f"✅ Enhanced search: {len(search_results)} documents found")
            
            # STEP 2: Reranking → TOP 3
            reranked_results = await self._context_aware_reranking(
                processed_query,
                search_results,
                unified_context
            )
            
            if not reranked_results:
                return await self._handle_no_results(processed_query, unified_context)
            
            logger.debug(f"✅ Reranking: {len(reranked_results)} → TOP 3 results")
            
            # STEP 3: Build ResponseContext trực tiếp từ reranked results
            response_context = await self._build_response_context_direct(
                processed_query,
                reranked_results,
                unified_context
            )
            
            # STEP 4: Generate response với ResponseContext
            query_features = self._build_query_features_for_llm(unified_context)

            if response_context:
                self.stats['response_context_used'] += 1
                response_result = await self.llm_handler.generate_response(
                    processed_query, response_context, query_features
                )
            else:
                # Fallback: tạo basic context từ top result
                basic_context = self._create_basic_context(processed_query, reranked_results)
                response_result = await self.llm_handler.generate_response(
                    processed_query, basic_context, query_features
                )

            if not response_result.get('success'):
                return await self._handle_llm_failure(processed_query, response_context, unified_context)
            
            # SUCCESS
            total_time = (datetime.now() - start_time).total_seconds()
            self._update_success_stats(total_time)
            
            final_response = {
                'success': True,
                'answer': response_result['answer'],
                'pipeline_info': {
                    'version': 'Mapping Navigation RAG v2.0 (no context_optimizer)',
                    'total_time': total_time,
                    'documents_processed': len(search_results),
                    'unified_context_used': unified_context['has_context'],
                    'response_context_used': response_context is not None,
                    'generation_method': response_result.get('provider', 'unknown')
                }
            }
            
            logger.info(f"✅ RAG completed in {total_time:.2f}s")
            return final_response
            
        except Exception as e:
            logger.error(f"❌ RAG pipeline failed: {e}")
            self.stats['pipeline_errors'] += 1
            return await self._handle_system_error(processed_query, unified_context)
    
    def _extract_simple_context(self, unified_data: dict) -> Dict[str, Any]:
        if not unified_data:
            return {
                'has_context': False,
                'original_query': '',
                'conversation_context': '',
                'citizen_profile': {},
                'response_requirements': {},
                'search_focus': {},
                'summary': 'No context'
            }
        original_query = unified_data.get('original_query', '')
        conversation_history = unified_data.get('conversation_history', [])
        entities = unified_data.get('entities', {})
        topic_thread = unified_data.get('topic_thread')
        intent_analysis = unified_data.get('intent_analysis', {})
        simple_context = original_query + ' ' + ' '.join(conversation_history[-2:]) if conversation_history else original_query
        citizen_profile = entities
        response_requirements = {'needs_conclusion': intent_analysis.get('needs_conclusion', False)}
        search_focus = {}
        article_match = re.search(r'điều\s+(\d+)', original_query.lower())
        if article_match:
            search_focus['article'] = article_match.group(1)
            unified_data['law_unit_filter'] = f"^{article_match.group(1)}($|\\.)"  # Match "1", "1.x"
            logger.debug("Set law_unit_filter: {}".format(unified_data['law_unit_filter']))
        summary_parts = []
        if original_query:
            summary_parts.append("original_query")
        if citizen_profile:
            summary_parts.append(f"citizen_profile({len(citizen_profile)})")
        if topic_thread:
            summary_parts.append(f"topic({topic_thread})")
        return {
            'has_context': bool(original_query or citizen_profile or simple_context),
            'original_query': original_query,
            'conversation_context': simple_context,
            'citizen_profile': citizen_profile,
            'response_requirements': response_requirements,
            'search_focus': search_focus,
            'topic_thread': topic_thread,
            'intent_analysis': intent_analysis,
            'summary': ' + '.join(summary_parts) if summary_parts else 'basic',
            'law_unit_filter': unified_data.get('law_unit_filter')
        }
    
    async def _enhanced_search(self, query: str, unified_context: Dict[str, Any], k: int = 15) -> List[Dict]:
        try:
            search_config = self.domain_mapping.get_vector_search_config(
                query=query,
                intent_analysis=unified_context.get('intent_analysis', {}),
                unified_context=unified_context
            )
            search_context = {
                'original_query': unified_context['original_query'],
                'citizen_profile': unified_context['citizen_profile'],
                'search_focus': unified_context['search_focus'],
                'has_context': unified_context['has_context'],
                'mapping_config': search_config,
                'target_articles': search_config.get('target_articles', []),
                'boost_keywords': search_config.get('boost_keywords', []),
                'search_strategy': search_config.get('search_strategy', 'standard'),
                'law_unit_filter': search_config.get('law_unit_filter', unified_context.get('law_unit_filter')),
                'short_content_boost': search_config.get('short_content_boost', 1.0),
                'expected_law_unit': search_config.get('expected_law_unit', None)  # Thêm expected_law_unit
            }
            k_optimized = int(k * search_config.get('k_multiplier', 1.0))
            results = await self.vector_searcher.search(query, query_features=search_context, k=max(k_optimized, 150))  # Tăng k tối thiểu
            logger.info("Raw results: " + str([f"law_unit: {r.get('metadata', {}).get('law_unit', '')}, content: {r.get('content', '')[:50]}" for r in results]))
            return results
        except Exception as e:
            logger.error("Enhanced search failed: {}".format(str(e)))
            return []

    async def _context_aware_reranking(self, query: str, search_results: List[Dict], unified_context: Dict[str, Any]) -> List[Dict]:
        """Context-aware reranking → TOP 3 results - FIXED"""
        try:
            # Build simple query_features object
            query_features = type('QueryFeatures', (), {
                'primary_intent': unified_context.get('intent_analysis', {}).get('intent_type', 'GENERAL'),
                'original_query': unified_context['original_query'],
                'citizen_profile': unified_context['citizen_profile'],
                'conversation_context': unified_context['conversation_context'],
                'has_context': unified_context['has_context']
            })()
            
            # FIXED: Properly await async rerank
            reranked_results = await self.reranker.rerank(
                query=query, 
                chunks=search_results, 
                context_tier='unified', 
                query_features=query_features
            )
            
            # Return TOP 3 results
            top_3_results = reranked_results[:3]
            logger.debug(f"✅ Reranking: {len(reranked_results)} → TOP 3 results")
            
            return top_3_results
            
        except Exception as e:
            logger.error(f"Context-aware reranking failed: {e}")
            return search_results[:3]
    
    async def _build_response_context_direct(self, query: str, reranked_results: List[Dict], unified_context: Dict[str, Any]) -> Optional[ResponseContext]:
        """Build ResponseContext trực tiếp từ reranked results - THAY THẾ context_optimizer"""
        try:
            if not reranked_results:
                return None
            
            # Lấy primary content từ top result
            top_result = reranked_results[0]
            primary_content = top_result.get('content', '')
            
            if not primary_content:
                return None
            
            # Extract citation từ metadata hoặc content
            primary_citation = self._extract_citation(top_result)
            
            # Build context notes từ unified_context
            context_note = ""
            citizen_note = ""
            
            topic_thread = unified_context.get('topic_thread')
            if topic_thread:
                context_note = f"về {topic_thread}"
            
            citizen_profile = unified_context.get('citizen_profile', {})
            if citizen_profile.get('age_group') == 'minor':
                citizen_note = "cho trẻ em"
            elif citizen_profile.get('location'):
                citizen_note = f"tại {citizen_profile['location']}"
            
            # Check if needs conclusion (có được không?)
            needs_conclusion = unified_context.get('response_requirements', {}).get('needs_conclusion', False)
            
            # Supporting contents từ các results khác
            supporting_contents = []
            for result in reranked_results[1:3]:  # Top 2-3 results
                content = result.get('content', '')
                if content and content != primary_content:
                    # Truncate for context
                    supporting_contents.append(content[:200] + "..." if len(content) > 200 else content)
            
            # Determine answer type
            answer_type = "legal"
            if any(word in query.lower() for word in ['thủ tục', 'làm', 'hồ sơ']):
                answer_type = "procedure"
            elif any(word in query.lower() for word in ['có được', 'được không']):
                answer_type = "eligibility"
            
            response_context = ResponseContext(
                query=unified_context.get('original_query', query),
                primary_content=primary_content,
                primary_citation=primary_citation,
                context_note=context_note,
                citizen_note=citizen_note,
                needs_conclusion=needs_conclusion,
                supporting_contents=supporting_contents,
                context=primary_content,
                answer_type=answer_type
            )
            
            return response_context
            
        except Exception as e:
            logger.error(f"ResponseContext building failed: {e}")
            return None
    
    def _extract_citation(self, result: Dict) -> str:
        """Extract citation từ result"""
        metadata = result.get('metadata', {})
        content = result.get('content', '')
        
        # Try from metadata first
        if metadata.get('law_unit'):
            return f"Điều {metadata['law_unit']}"
        
        if metadata.get('source_file'):
            source = metadata['source_file']
            if 'luat' in source.lower():
                return "Luật xuất nhập cảnh của công dân Việt Nam"
        
        # Try extract from content
        import re
        article_match = re.search(r'Điều\s+(\d+)', content)
        if article_match:
            return f"Điều {article_match.group(1)}"
        
        return "quy định pháp luật"
    
    def _create_basic_context(self, query: str, reranked_results: List[Dict]) -> ResponseContext:
        """Tạo basic context nếu build ResponseContext thất bại"""
        if reranked_results:
            content = reranked_results[0].get('content', '')
            citation = self._extract_citation(reranked_results[0])
        else:
            content = "Không tìm thấy thông tin phù hợp."
            citation = ""
        
        return ResponseContext(
            query=query,
            primary_content=content,
            primary_citation=citation,
            context=content,
            answer_type="general"
        )

    def _build_query_features_for_llm(self, unified_context: Dict) -> Any:
        """Build query features cho LLM"""
        return type('QueryFeatures', (), {
            'original_query': unified_context['original_query'],
            'citizen_profile': unified_context['citizen_profile'], 
            'conversation_context': unified_context['conversation_context'],
            'topic_thread': unified_context.get('topic_thread'),
            'unified_context': unified_context
        })()

    # Error handling methods
    async def _handle_no_results(self, query: str, unified_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle no results"""
        response = "Không tìm thấy thông tin cụ thể cho câu hỏi này.\n\nĐể được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"
        
        return {
            'success': True,
            'answer': response,
            'method': 'no_results'
        }
    
    async def _handle_llm_failure(self, query: str, response_context: ResponseContext, unified_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle LLM failure"""
        if response_context and response_context.primary_content:
            content_preview = response_context.primary_content[:150] + "..." if len(response_context.primary_content) > 150 else response_context.primary_content
            citation = response_context.primary_citation
            
            if citation:
                response = f"Căn cứ {citation}:\n\n\"{content_preview}\"\n\nĐể được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"
            else:
                response = f"Căn cứ quy định pháp luật:\n\n\"{content_preview}\"\n\nĐể được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"
        else:
            response = "Hệ thống gặp sự cố kỹ thuật khi tạo phản hồi.\n\nĐể được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"
        
        return {
            'success': True,
            'answer': response,
            'method': 'llm_failure'
        }
    
    async def _handle_system_error(self, query: str, unified_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system error"""
        response = "Hệ thống gặp sự cố kỹ thuật nghiêm trọng.\n\nĐể được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"
        
        return {
            'success': True,
            'answer': response,
            'method': 'system_error'
        }
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create error response"""
        return {
            'success': False,
            'answer': message,
            'method': 'error_response'
        }
    
    def _update_success_stats(self, response_time: float):
        """Update success statistics"""
        self.stats['successful_responses'] += 1
        
        total = self.stats['total_queries']
        current_avg = self.stats['avg_response_time']
        self.stats['avg_response_time'] = (current_avg * (total - 1) + response_time) / total
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        total = self.stats['total_queries']
        success_rate = self.stats['successful_responses'] / total if total > 0 else 0
        context_usage_rate = self.stats['with_unified_context'] / total if total > 0 else 0
        response_context_rate = self.stats['response_context_used'] / total if total > 0 else 0
        mapping_rate = self.stats['mapping_optimizations'] / total if total > 0 else 0
        
        return {
            'system_info': {
                'version': 'Mapping Navigation RAG v2.0 (no context_optimizer)',
                'status': 'ready' if self.is_initialized else 'not_initialized',
                'capabilities': [
                    'mapping_navigation',
                    'response_context_for_llm',
                    'top3_result_selection',
                    'direct_context_building'
                ],
                'total_documents': self.vector_searcher.get_stats().get('documents_loaded', 0) if hasattr(self, 'vector_searcher') else 0
            },
            'performance': {
                'total_queries': total,
                'success_rate': round(success_rate, 3),
                'context_usage_rate': round(context_usage_rate, 3),
                'response_context_rate': round(response_context_rate, 3),
                'mapping_navigation_rate': round(mapping_rate, 3),
                'avg_response_time': round(self.stats['avg_response_time'], 3)
            },
            'mapping_stats': self.domain_mapping.get_stats() if hasattr(self, 'domain_mapping') else {}
        }
    
    async def quick_query(self, query: str) -> str:
        """Quick query method"""
        result = await self.query(query)
        return result.get('answer', 'Could not process this question.')
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_queries': 0,
            'with_unified_context': 0,
            'successful_responses': 0,
            'response_context_used': 0,
            'avg_response_time': 0.0,
            'pipeline_errors': 0,
            'mapping_optimizations': 0
        }
        logger.info("📊 RAG Engine statistics reset")