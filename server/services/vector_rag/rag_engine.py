# services/vector_rag/rag_engine.py - SIMPLIFIED JSON USAGE
"""
Updated RAG Engine - Simplified admin_units.json usage
🎯 FIX: Simple JSON structure, focused parsing
📋 KEEP: Existing pipeline logic
✅ GOAL: Clean context passing without over-engineering
"""
import asyncio
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from dataclasses import dataclass

from services.vector_rag.rag_config import config
from services.vector_rag.vector_store import VectorSearcher
from services.vector_rag.reranker import ReRanker
from services.vector_rag.llm_handler import LLMHandler
from services.vector_rag.context_optimizer import ContextOptimizer

logger = logging.getLogger(__name__)

@dataclass
class ResponseContext:
    """Simple context for LLM generation - no complexity"""
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
    """Updated RAG Engine - Simplified JSON usage"""
    
    def __init__(self):
        self.vector_searcher = VectorSearcher() 
        self.reranker = ReRanker()
        self.context_optimizer = ContextOptimizer()
        self.llm_handler = LLMHandler()
        
        # Load simplified admin config
        self.admin_config = self._load_admin_config()
        
        self.is_initialized = False
        self.stats = {
            'total_queries': 0,
            'with_unified_context': 0,
            'successful_responses': 0,
            'response_context_used': 0,
            'context_enhanced': 0,
            'avg_response_time': 0.0,
            'pipeline_errors': 0
        }
        
        logger.info("🎯 RAG Engine with simplified admin_units.json")

    def _load_admin_config(self) -> dict:
        """Load simplified admin_units.json"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'admin_units.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate essential keys
            required_keys = ['location_variants', 'citizen_profile_patterns', 'search_boost_config']
            missing_keys = [key for key in required_keys if key not in config_data]
            
            if missing_keys:
                logger.warning(f"Missing keys in admin_units.json: {missing_keys}")
                return {}
            
            logger.info("✅ Admin config loaded successfully")
            return config_data
            
        except Exception as e:
            logger.warning(f"Failed to load admin config: {e}")
            return {}

    async def initialize(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Initialize RAG Engine - UNCHANGED"""
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
                'message': f'Simplified RAG Engine ready with {total_docs} documents',
                'capabilities': {
                    'simplified_context_processing': True,
                    'focused_citizen_profiling': True,
                    'enhanced_search_boosting': True,
                    'response_context_support': True,
                    'natural_response_generation': True
                }
            }
            
        except Exception as e:
            logger.error(f"❌ RAG Engine init failed: {e}")
            return {'success': False, 'message': f'Initialization failed: {str(e)}'}
    
    async def query(self, processed_query: str, session_id: str = None, unified_data: dict = None) -> Dict[str, Any]:
        """
        UPDATED Query Processing - Simplified context handling
        """
        start_time = datetime.now()
        self.stats['total_queries'] += 1
        
        if not self.is_initialized:
            return self._create_error_response('RAG Engine not initialized')
        
        if not processed_query or not processed_query.strip():
            return self._create_error_response('Empty query provided')
        
        # Extract unified context with simplified parsing
        unified_context = self._extract_unified_context_simple(unified_data)
        
        if unified_context['has_context']:
            self.stats['with_unified_context'] += 1
            logger.info(f"🎯 Processing with context: {unified_context['summary']}")
        
        logger.info(f"🔍 RAG: '{processed_query[:50]}...'")
        
        try:
            # Enhanced search with boost config
            search_results = await self._enhanced_search(
                processed_query, 
                unified_context,
                k=config.search_k * 2
            )
            
            if not search_results:
                return await self._handle_no_results(processed_query, unified_context)
            
            logger.debug(f"✅ Enhanced search: {len(search_results)} documents found")
            
            # Context-aware reranking
            reranked_results = await self._context_aware_reranking(
                processed_query,
                search_results,
                unified_context
            )
            
            if not reranked_results:
                return await self._handle_no_results(processed_query, unified_context)
            
            logger.debug(f"✅ Reranking: {len(reranked_results)} results processed")
            
            # Build rich context
            rich_context = await self._build_rich_context(
                processed_query,
                reranked_results,
                unified_context
            )
            
            # Build ResponseContext with enhanced templates
            response_context = self._build_enhanced_response_context(
                processed_query, rich_context, unified_context
            )
            
            if response_context:
                self.stats['response_context_used'] += 1
                logger.debug(f"✅ Enhanced ResponseContext: {response_context.context_note}")
            
            # Generate response
            unified_query_features = type('QueryFeatures', (), {
                'original_query': unified_context['original_query'],
                'citizen_profile': unified_context['citizen_profile'], 
                'conversation_context': unified_context['conversation_context'],
                'topic_thread': unified_context.get('topic_thread'),
                'needs_conclusion': getattr(rich_context, 'needs_conclusion', False),
                'answer_type': getattr(rich_context, 'answer_type', 'legal'),
                'unified_context': unified_context
            })()

            # Generate response - UNIFIED METHOD CALL
            if response_context:
                # Use ResponseContext as context_result
                response_result = await self.llm_handler.generate_response(
                    processed_query, response_context, unified_query_features
                )
            else:
                # Use rich_context as context_result
                response_result = await self.llm_handler.generate_response(
                    processed_query, rich_context, unified_query_features
                )

            if not response_result.get('success'):
                return await self._handle_llm_failure(processed_query, rich_context, unified_context)
            
            # SUCCESS
            total_time = (datetime.now() - start_time).total_seconds()
            self._update_success_stats(total_time)
            
            final_response = {
                'success': True,
                'answer': response_result['answer'],
                'pipeline_info': {
                    'version': 'Simplified RAG v2.2',
                    'total_time': total_time,
                    'documents_processed': len(search_results),
                    'unified_context_used': unified_context['has_context'],
                    'response_context_used': response_context is not None,
                    'generation_method': response_result.get('provider', 'unknown')
                }
            }
            
            logger.info(f"✅ Simplified RAG completed in {total_time:.2f}s")
            return final_response
            
        except Exception as e:
            logger.error(f"❌ RAG pipeline failed: {e}")
            self.stats['pipeline_errors'] += 1
            return await self._handle_system_error(processed_query, unified_context)
    
    def _extract_unified_context_simple(self, unified_data: dict) -> Dict[str, Any]:
        """SIMPLIFIED: Extract context using JSON config"""
        if not unified_data:
            return {
                'has_context': False,
                'original_query': '',
                'conversation_context': '',
                'context_summary': {},
                'citizen_profile': {},
                'response_requirements': {},
                'search_focus': {},
                'summary': 'No context'
            }

        original_query = unified_data.get('original_query', '')
        conversation_history = unified_data.get('conversation_history', [])
        entities = unified_data.get('entities', {})
        topic_thread = unified_data.get('topic_thread')
        
        # Build enhanced context
        enhanced_context = self._build_enhanced_context(
            topic_thread, conversation_history, entities, 
            unified_data.get('enhanced_context', '')
        )
        
        # Parse citizen profile using JSON patterns
        citizen_profile = self._parse_citizen_profile_json(enhanced_context)
        
        # Build context summary
        context_summary = self._build_context_summary_json(enhanced_context)
        
        response_requirements = unified_data.get('response_requirements', {})
        search_focus = unified_data.get('search_focus', {})
        
        summary_parts = []
        if original_query:
            summary_parts.append("original_query")
        if citizen_profile:
            summary_parts.append(f"citizen_profile({len(citizen_profile)})")
        if context_summary:
            summary_parts.append(f"context_summary({len(context_summary.get('keywords', []))})")
        
        return {
            'has_context': bool(original_query or citizen_profile or enhanced_context),
            'original_query': original_query,
            'conversation_context': enhanced_context,
            'context_summary': context_summary,
            'citizen_profile': citizen_profile,
            'response_requirements': response_requirements,
            'search_focus': search_focus,
            'topic_thread': self._extract_topic_thread_json(enhanced_context),
            'summary': ' + '.join(summary_parts) if summary_parts else 'basic'
        }
    
    def _build_enhanced_context(self, topic_thread: str, conversation_history: List[str], 
                              entities: Dict, fallback_context: str) -> str:
        """Build enhanced context from components"""
        context_parts = []
        
        if topic_thread:
            context_parts.append(f"topic: {topic_thread}")
        
        if conversation_history:
            recent_history = ' | '.join(conversation_history[-2:])
            context_parts.append(f"history: {recent_history}")
        
        if entities:
            entity_str = ', '.join(f"{k}:{v}" for k, v in entities.items())
            context_parts.append(f"entities: {entity_str}")
        
        return ' '.join(context_parts) if context_parts else fallback_context
    
    def _parse_citizen_profile_json(self, context: str) -> Dict[str, Any]:
        """SIMPLE: Parse citizen profile"""
        profile = {}
        
        if not context:
            return profile
        
        context_lower = context.lower()
        
        # Age - chỉ 2 cases chính
        if any(word in context_lower for word in ['trẻ em', 'dưới 14', 'con nhỏ']):
            profile['age_group'] = 'minor'
        elif any(word in context_lower for word in ['cao tuổi', 'người già']):
            profile['age_group'] = 'elderly'
        
        # Location - chỉ major cities
        location_map = {
            'hà nội': 'Hà Nội', 'hn': 'Hà Nội',
            'hcm': 'TP.HCM', 'sài gòn': 'TP.HCM', 'tphcm': 'TP.HCM',
            'đà nẵng': 'Đà Nẵng', 'đắk lắk': 'Đắk Lắk'
        }
        
        for variant, province in location_map.items():
            if variant in context_lower:
                profile['location'] = province
                break
        
        # Document status - 3 cases chính
        if any(word in context_lower for word in ['hết hạn', 'quá hạn']):
            profile['passport_status'] = 'expired'
        elif any(word in context_lower for word in ['chưa có', 'chưa làm']):
            profile['passport_status'] = 'not_have'
        elif any(word in context_lower for word in ['còn hạn', 'còn hiệu lực']):
            profile['passport_status'] = 'valid'
        
        return profile
    
    def _build_context_summary_json(self, context: str) -> Dict[str, Any]:
        """Build context summary using JSON config"""
        if not context or not self.admin_config:
            return {}
        
        context_lower = context.lower()
        enhancement_config = self.admin_config.get('context_enhancement', {})
        
        # Find topic keywords
        topic_keywords = enhancement_config.get('topic_keywords', {})
        found_topics = []
        priority_aspect = 'legal'
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                found_topics.append(topic)
                if topic == 'procedure':
                    priority_aspect = 'procedure'
                elif topic == 'passport':
                    priority_aspect = 'passport'
        
        # Check for vague patterns
        vague_patterns = enhancement_config.get('vague_patterns', [])
        has_vague = any(pattern in context_lower for pattern in vague_patterns)
        
        return {
            'keywords': found_topics,
            'priority_aspect': priority_aspect,
            'has_vague_query': has_vague
        }
    
    def _extract_topic_thread_json(self, context: str) -> str:
        """Extract topic thread using JSON config"""
        if not context or not self.admin_config:
            return ""
        
        context_lower = context.lower()
        topic_keywords = self.admin_config.get('context_enhancement', {}).get('topic_keywords', {})
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                return topic
        
        return ""
    
    def _build_enhanced_response_context(self, query: str, rich_context: Any, unified_context: Dict) -> Optional[ResponseContext]:
        """Build enhanced ResponseContext using JSON templates"""
        try:
            primary_content = getattr(rich_context, 'primary_content', '')
            primary_citation = getattr(rich_context, 'primary_citation', '')
            
            if not primary_content:
                return None
            
            # Build context note using JSON templates
            context_note, citizen_note = self._build_context_notes_json(unified_context)
            
            # Check needs conclusion
            needs_conclusion = getattr(rich_context, 'needs_conclusion', False)
            
            # Get supporting contents
            supporting_contents = []
            if hasattr(rich_context, 'supporting_contents'):
                for support in rich_context.supporting_contents[:2]:
                    if isinstance(support, dict):
                        content = support.get('content', '')
                        if content:
                            supporting_contents.append(content[:200] + "..." if len(content) > 200 else content)
                    elif isinstance(support, str):
                        supporting_contents.append(support[:200] + "..." if len(support) > 200 else support)
            
            # Determine answer type
            answer_type = getattr(rich_context, 'answer_type', 'legal')
            
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
            
            logger.debug(f"🎯 Enhanced ResponseContext: context='{context_note}', citizen='{citizen_note}'")
            return response_context
            
        except Exception as e:
            logger.error(f"❌ Enhanced ResponseContext building failed: {e}")
            return None
    
    def _build_context_notes_json(self, unified_context: Dict) -> tuple:
        """Build context notes using JSON templates"""
        context_note = ""
        citizen_note = ""
        
        if not self.admin_config:
            return context_note, citizen_note
        
        templates = self.admin_config.get('response_templates', {})
        greeting_contexts = templates.get('greeting_contexts', {})
        citizen_notes = templates.get('citizen_notes', {})
        
        # Build context note from topic
        topic_thread = unified_context.get('topic_thread')
        if topic_thread and topic_thread in greeting_contexts:
            context_note = greeting_contexts[topic_thread]
        
        # Add location
        citizen_profile = unified_context.get('citizen_profile', {})
        location = citizen_profile.get('location')
        if location:
            context_note += f" tại {location}" if context_note else f"tại {location}"
        
        # Build citizen note
        age_group = citizen_profile.get('age_group')
        if age_group == 'minor' and 'minor' in citizen_notes:
            citizen_note = citizen_notes['minor']
        elif age_group == 'elderly' and 'elderly' in citizen_notes:
            citizen_note = citizen_notes['elderly']
        
        # Add document status note
        passport_status = citizen_profile.get('passport_status')
        if passport_status == 'not_have' and 'first_time' in citizen_notes:
            if citizen_note:
                citizen_note += " " + citizen_notes['first_time']
            else:
                citizen_note = citizen_notes['first_time']
        
        return context_note, citizen_note
    
    async def _enhanced_search(self, query: str, unified_context: Dict[str, Any], k: int = 15) -> List[Dict]:
        """Enhanced search with boost config"""
        try:
            # Pass boost config to searcher
            search_context = {
                'original_query': unified_context['original_query'],
                'citizen_profile': unified_context['citizen_profile'],
                'context_summary': unified_context['context_summary'],
                'search_focus': unified_context['search_focus'],
                'has_context': unified_context['has_context'],
                'boost_config': self.admin_config.get('search_boost_config', {})  # NEW
            }
            
            results = await self.vector_searcher.search(query, query_features=search_context, k=k)
            return results
        except Exception as e:
            logger.error(f"Enhanced search failed: {e}")
            return []
    
    # Keep all existing methods unchanged
    async def _context_aware_reranking(self, query: str, search_results: List[Dict], unified_context: Dict[str, Any]) -> List[Dict]:
        """UNCHANGED"""
        try:
            rerank_context = {
                'original_query': unified_context['original_query'],
                'citizen_profile': unified_context['citizen_profile'],
                'conversation_context': unified_context['conversation_context'],
                'context_summary': unified_context['context_summary'],
                'response_requirements': unified_context['response_requirements'],
                'has_context': unified_context['has_context']
            }
            reranked_results = self.reranker.rerank(query=query, chunks=search_results, context_tier='unified', query_features=rerank_context)
            return reranked_results
        except Exception as e:
            logger.error(f"Context-aware reranking failed: {e}")
            return search_results
    
    async def _build_rich_context(self, query: str, reranked_results: List[Dict], unified_context: Dict[str, Any]) -> Any:
        """UNCHANGED"""
        try:
            enhanced_query_features = type('QueryFeatures', (), {
                'original_query': unified_context['original_query'] or query,
                'citizen_profile': unified_context['citizen_profile'],
                'context_summary': unified_context['context_summary'],
                'response_requirements': unified_context['response_requirements'],
                'conversation_context': unified_context['conversation_context'],
                'needs_conclusion': unified_context['response_requirements'].get('needs_conclusion', False),
                'format_type': unified_context['response_requirements'].get('format', 'standard')
            })()
            
            context_result = await self.context_optimizer.optimize_context(reranked_results, enhanced_query_features)
            context_result.unified_context = unified_context
            return context_result
        except Exception as e:
            logger.error(f"Rich context building failed: {e}")
            return type('ContextResult', (), {
                'query': query,
                'primary_content': reranked_results[0].get('content', '') if reranked_results else '',
                'primary_citation': '',
                'context': reranked_results[0].get('content', '') if reranked_results else '',
                'supporting_contents': [],
                'unified_context': unified_context
            })()
    
    # Keep all existing error handling and utility methods unchanged
    async def _handle_no_results(self, query: str, unified_context: Dict[str, Any]) -> Dict[str, Any]:
        """UNCHANGED"""
        response = "Không tìm thấy thông tin cụ thể cho câu hỏi này.\n\nĐể được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"
        
        return {
            'success': True,
            'answer': response,
            'method': 'no_results'
        }
    
    async def _handle_llm_failure(self, query: str, rich_context: Any, unified_context: Dict[str, Any]) -> Dict[str, Any]:
        """UNCHANGED"""
        if hasattr(rich_context, 'primary_content') and rich_context.primary_content:
            content_preview = rich_context.primary_content[:150] + "..." if len(rich_context.primary_content) > 150 else rich_context.primary_content
            citation = getattr(rich_context, 'primary_citation', '')
            
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
        """UNCHANGED"""
        response = "Hệ thống gặp sự cố kỹ thuật nghiêm trọng.\n\nĐể được tư vấn chính xác vui lòng liên hệ cán bộ hướng dẫn hoặc truy cập website: https://dichvucong.bocongan.gov.vn"
        
        return {
            'success': True,
            'answer': response,
            'method': 'system_error'
        }
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """UNCHANGED"""
        return {
            'success': False,
            'answer': message,
            'method': 'error_response'
        }
    
    def _update_success_stats(self, response_time: float):
        """UNCHANGED"""
        self.stats['successful_responses'] += 1
        
        total = self.stats['total_queries']
        current_avg = self.stats['avg_response_time']
        self.stats['avg_response_time'] = (current_avg * (total - 1) + response_time) / total
    
    def get_stats(self) -> Dict[str, Any]:
        """UPDATED - simplified version stats"""
        total = self.stats['total_queries']
        success_rate = self.stats['successful_responses'] / total if total > 0 else 0
        context_usage_rate = self.stats['with_unified_context'] / total if total > 0 else 0
        response_context_rate = self.stats['response_context_used'] / total if total > 0 else 0
        
        return {
            'system_info': {
                'version': 'Simplified RAG v2.2',
                'status': 'ready' if self.is_initialized else 'not_initialized',
                'admin_config_loaded': bool(self.admin_config),
                'capabilities': [
                    'simplified_context_processing',
                    'json_based_profiling',
                    'enhanced_search_boosting',
                    'response_context_support',
                    'natural_response_generation'
                ],
                'total_documents': self.vector_searcher.get_stats().get('documents_loaded', 0) if hasattr(self, 'vector_searcher') else 0
            },
            'performance': {
                'total_queries': total,
                'success_rate': round(success_rate, 3),
                'context_usage_rate': round(context_usage_rate, 3),
                'response_context_rate': round(response_context_rate, 3),
                'avg_response_time': round(self.stats['avg_response_time'], 3)
            },
            'config_status': {
                'admin_config_keys': list(self.admin_config.keys()) if self.admin_config else [],
                'location_variants_count': len(self.admin_config.get('location_variants', {})),
                'citizen_patterns_loaded': bool(self.admin_config.get('citizen_profile_patterns')),
                'boost_config_loaded': bool(self.admin_config.get('search_boost_config'))
            }
        }
    
    async def quick_query(self, query: str) -> str:
        """UNCHANGED"""
        result = await self.query(query)
        return result.get('answer', 'Could not process this question.')
    
    def reset_stats(self):
        """UNCHANGED"""
        self.stats = {
            'total_queries': 0,
            'with_unified_context': 0,
            'successful_responses': 0,
            'response_context_used': 0,
            'avg_response_time': 0.0,
            'pipeline_errors': 0
        }
        logger.info("📊 Simplified RAG Engine statistics reset")