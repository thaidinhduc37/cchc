# server/services/vector_rag/lightweight_rag_engine.py
"""
RAG Engine siêu nhẹ tích hợp tất cả components
Thay thế hoàn toàn hệ thống cũ với performance cao
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from .lightweight_config import SYSTEM_CONFIG, get_config_summary
from .lightweight_document_processor import LightweightDocumentProcessor
from .lightweight_vector_manager import LightweightVectorManager, XuatNhapCanhRetriever
from .lightweight_llm_handler import LightweightLLMHandler, XuatNhapCanhPromptBuilder, ResponseValidator

logger = logging.getLogger(__name__)

class LightweightRAGEngine:
    """
    RAG Engine siêu nhẹ và tối ưu cho xuất nhập cảnh
    Memory usage: <500MB (thay vì 2GB+)
    Response time: <3s (thay vì 10s+)
    """
    
    def __init__(self, 
                 gemini_api_key: Optional[str] = None,
                 system_config=None):
        
        self.config = system_config or SYSTEM_CONFIG
        
        # Initialize components
        self.doc_processor = LightweightDocumentProcessor()
        self.vector_manager = LightweightVectorManager()
        self.llm_handler = LightweightLLMHandler()
        
        # Specialized components
        self.retriever = XuatNhapCanhRetriever(self.vector_manager)
        self.prompt_builder = XuatNhapCanhPromptBuilder()
        
        # Session management
        self.session_stats = {
            'queries_processed': 0,
            'cache_hits': 0,
            'avg_response_time': 0,
            'started_at': datetime.now(),
            'errors': []
        }
        
        # Query cache cho session
        self.query_cache = {}
        self.cache_ttl = 1800  # 30 minutes
        
        # System status
        self.is_initialized = False
        self.initialization_error = None
        
        logger.info("🚀 LightweightRAGEngine initialized")
    
    async def initialize_system(self, 
                               force_rebuild: bool = False,
                               documents_path: str = None) -> Dict[str, Any]:
        """
        Khởi tạo hệ thống RAG
        """
        start_time = datetime.now()
        result = {
            'success': False,
            'message': '',
            'stats': {},
            'initialization_time': 0
        }
        
        try:
            logger.info("🔧 Initializing RAG system...")
            
            # Check documents directory
            docs_path = documents_path or self.config.documents_path
            if not os.path.exists(docs_path):
                os.makedirs(docs_path, exist_ok=True)
                result['message'] = f"Created documents directory: {docs_path}"
                result['success'] = True
                return result
            
            # Check if vector store already exists and is recent
            vector_stats = self.vector_manager.get_collection_stats()
            
            if vector_stats.get('total_documents', 0) > 0 and not force_rebuild:
                logger.info("📂 Found existing vector store, loading...")
                result['message'] = "Loaded existing vector store"
                result['stats'] = vector_stats
                self.is_initialized = True
                result['success'] = True
                
            else:
                logger.info("🔨 Building new vector store...")
                
                # Process documents
                logger.info("📄 Processing documents...")
                documents = self.doc_processor.process_documents_directory(docs_path)
                
                if not documents:
                    result['message'] = f"No documents found in {docs_path}"
                    result['success'] = True
                    return result
                
                # Add to vector store
                logger.info("🧮 Building vector store...")
                success = self.vector_manager.add_documents(documents)
                
                if success:
                    result['message'] = f"Successfully processed {len(documents)} document chunks"
                    result['stats'] = self.vector_manager.get_collection_stats()
                    self.is_initialized = True
                    result['success'] = True
                else:
                    result['message'] = "Failed to build vector store"
                    return result
            
            # Verify LLM providers
            logger.info("🤖 Checking LLM providers...")
            provider_status = self.llm_handler.get_provider_status()
            available_providers = [
                name for name, status in provider_status['providers'].items()
                if status['available']
            ]
            
            if not available_providers:
                logger.warning("⚠️ No LLM providers available")
                result['message'] += " (Warning: No LLM providers available)"
            else:
                logger.info(f"✅ Available LLM providers: {available_providers}")
            
            result['stats']['llm_providers'] = available_providers
            result['stats']['config'] = get_config_summary()
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {e}")
            self.initialization_error = str(e)
            result['success'] = False
            result['message'] = f"Initialization failed: {e}"
        
        finally:
            init_time = (datetime.now() - start_time).total_seconds()
            result['initialization_time'] = round(init_time, 2)
            logger.info(f"⏱️ Initialization completed in {init_time:.2f}s")
        
        return result
    
    async def query_async(self, 
                         question: str,
                         k: int = 3,
                         include_sources: bool = True,
                         use_cache: bool = True) -> Dict[str, Any]:
        """
        Async query processing với đầy đủ RAG pipeline
        """
        start_time = datetime.now()
        
        # Check system initialized
        if not self.is_initialized:
            return {
                'success': False,
                'answer': "❌ Hệ thống chưa được khởi tạo. Vui lòng chạy initialize_system() trước.",
                'error': self.initialization_error or "System not initialized"
            }
        
        # Check cache
        cache_key = f"{question}:{k}"
        if use_cache and cache_key in self.query_cache:
            cache_data = self.query_cache[cache_key]
            if datetime.now() - cache_data['timestamp'] < timedelta(seconds=self.cache_ttl):
                self.session_stats['cache_hits'] += 1
                cache_data['result']['cached'] = True
                return cache_data['result']
        
        result = {
            'success': False,
            'answer': '',
            'sources': [],
            'metadata': {
                'question_type': '',
                'retrieval_time': 0,
                'generation_time': 0,
                'total_time': 0,
                'provider_used': '',
                'confidence': 0
            },
            'cached': False
        }
        
        try:
            # Step 1: Retrieve relevant documents
            retrieval_start = datetime.now()
            
            relevant_docs = self.retriever.retrieve_relevant_documents(
                question, k=k, include_legal_refs=True
            )
            
            retrieval_time = (datetime.now() - retrieval_start).total_seconds()
            result['metadata']['retrieval_time'] = round(retrieval_time, 3)
            
            if not relevant_docs:
                result['answer'] = "❌ Không tìm thấy thông tin liên quan trong cơ sở dữ liệu pháp lý."
                result['success'] = True
                return result
            
            # Step 2: Build context
            context_parts = []
            sources = []
            
            for i, doc in enumerate(relevant_docs):
                context_parts.append(f"[Tài liệu {i+1}]: {doc['content']}")
                
                if include_sources:
                    source_info = {
                        'id': doc['id'],
                        'source': doc['metadata'].get('source', 'Unknown'),
                        'doc_type': doc['metadata'].get('doc_type', 'Unknown'),
                        'score': round(doc['score'], 3),
                        'legal_references': doc['metadata'].get('legal_references', [])
                    }
                    sources.append(source_info)
            
            context = "\n\n".join(context_parts)
            result['sources'] = sources
            
            # Step 3: Detect question type và build prompt
            question_type = self.prompt_builder.detect_question_type(question)
            result['metadata']['question_type'] = question_type
            
            # Step 4: Generate response
            generation_start = datetime.now()
            
            llm_result = await self.llm_handler.generate_async(
                prompt="",  # Empty vì dùng context + question
                context=context,
                question=question
            )
            
            generation_time = (datetime.now() - generation_start).total_seconds()
            result['metadata']['generation_time'] = round(generation_time, 3)
            
            if llm_result['success']:
                result['success'] = True
                result['answer'] = llm_result['response']
                result['metadata']['provider_used'] = llm_result['provider']
                
                # Step 5: Validate response
                validation = ResponseValidator.validate_response(
                    llm_result['response'], question
                )
                result['metadata']['confidence'] = round(validation['confidence'], 3)
                
                # Add validation warnings if needed
                if validation['issues']:
                    result['metadata']['validation_issues'] = validation['issues']
                
                # Step 6: Enhance response với legal formatting
                result['answer'] = self._enhance_legal_response(
                    result['answer'], question_type, sources
                )
                
            else:
                result['answer'] = llm_result['response']  # Error message
                result['metadata']['error'] = llm_result.get('error', 'Unknown error')
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            result['answer'] = f"❌ Đã có lỗi xảy ra khi xử lý câu hỏi: {str(e)}"
            result['metadata']['error'] = str(e)
            self.session_stats['errors'].append({
                'question': question,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        
        finally:
            # Calculate total time
            total_time = (datetime.now() - start_time).total_seconds()
            result['metadata']['total_time'] = round(total_time, 3)
            
            # Update session stats
            self.session_stats['queries_processed'] += 1
            
            # Update average response time
            prev_avg = self.session_stats['avg_response_time']
            query_count = self.session_stats['queries_processed']
            self.session_stats['avg_response_time'] = round(
                (prev_avg * (query_count - 1) + total_time) / query_count, 3
            )
            
            # Cache successful results
            if use_cache and result['success'] and not result.get('cached', False):
                self.query_cache[cache_key] = {
                    'result': result.copy(),
                    'timestamp': datetime.now()
                }
            
            logger.info(f"⏱️ Query processed in {total_time:.3f}s")
        
        return result
    
    def query(self, question: str, **kwargs) -> Dict[str, Any]:
        """Sync wrapper cho query_async"""
        return asyncio.run(self.query_async(question, **kwargs))
    
    def _enhance_legal_response(self, 
                               response: str, 
                               question_type: str, 
                               sources: List[Dict]) -> str:
        """Enhance response với legal formatting"""
        
        enhanced = response
        
        # Add source references if not already present
        if sources and "nguồn" not in response.lower():
            enhanced += "\n\n📚 **NGUỒN THAM KHẢO:**\n"
            for i, source in enumerate(sources[:3], 1):
                doc_type = source.get('doc_type', 'Unknown').upper()
                source_name = os.path.basename(source.get('source', 'Unknown'))
                enhanced += f"{i}. {doc_type}: {source_name}\n"
        
        # Add legal references if available
        legal_refs = []
        for source in sources:
            refs = source.get('legal_references', [])
            if isinstance(refs, list):
                legal_refs.extend(refs)
        
        if legal_refs:
            unique_refs = list(set(legal_refs))[:5]  # Top 5 unique refs
            enhanced += f"\n\n⚖️ **CÁC ĐIỀU KHOẢN LIÊN QUAN:** {', '.join(unique_refs)}"
        
        # Add disclaimers cho question types nhạy cảm
        if question_type in ['legal', 'procedure']:
            enhanced += "\n\n⚠️ *Lưu ý: Thông tin này chỉ mang tính tham khảo. " \
                       "Vui lòng liên hệ cơ quan có thẩm quyền để được hỗ trợ chính thức.*"
        
        return enhanced
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Lấy thống kê toàn hệ thống"""
        try:
            vector_stats = self.vector_manager.get_collection_stats()
            llm_status = self.llm_handler.get_provider_status()
            
            return {
                'system': {
                    'is_initialized': self.is_initialized,
                    'config': get_config_summary(),
                    'uptime': str(datetime.now() - self.session_stats['started_at']),
                },
                'vector_store': vector_stats,
                'llm_providers': llm_status,
                'session': self.session_stats,
                'performance': {
                    'avg_response_time': self.session_stats['avg_response_time'],
                    'cache_hit_rate': round(
                        self.session_stats['cache_hits'] / max(1, self.session_stats['queries_processed']) * 100, 2
                    ),
                    'query_cache_size': len(self.query_cache)
                }
            }
        except Exception as e:
            logger.error(f"❌ Failed to get system stats: {e}")
            return {'error': str(e)}
    
    def add_documents_from_directory(self, directory_path: str) -> Dict[str, Any]:
        """Thêm documents từ directory mới"""
        try:
            logger.info(f"📁 Adding documents from: {directory_path}")
            
            # Process new documents
            documents = self.doc_processor.process_documents_directory(directory_path)
            
            if not documents:
                return {
                    'success': True,
                    'message': f"No new documents found in {directory_path}",
                    'documents_added': 0
                }
            
            # Add to vector store
            success = self.vector_manager.add_documents(documents)
            
            if success:
                # Clear query cache to ensure fresh results
                self.query_cache = {}
                
                return {
                    'success': True,
                    'message': f"Successfully added {len(documents)} document chunks",
                    'documents_added': len(documents),
                    'new_stats': self.vector_manager.get_collection_stats()
                }
            else:
                return {
                    'success': False,
                    'message': "Failed to add documents to vector store",
                    'documents_added': 0
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to add documents: {e}")
            return {
                'success': False,
                'message': f"Error adding documents: {e}",
                'documents_added': 0
            }
    
    def search_documents(self, 
                        query: str, 
                        k: int = 5,
                        filter_doc_type: str = None) -> Dict[str, Any]:
        """Tìm kiếm documents không qua LLM"""
        try:
            if filter_doc_type:
                results = self.vector_manager.search_by_document_type(
                    filter_doc_type, query, k
                )
            else:
                results = self.vector_manager.search_similar(query, k)
            
            return {
                'success': True,
                'results': results,
                'total_found': len(results)
            }
            
        except Exception as e:
            logger.error(f"❌ Document search failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    def clear_caches(self):
        """Xóa tất cả caches"""
        self.query_cache = {}
        self.llm_handler.clear_cache()
        logger.info("🗑️ All caches cleared")
    
    def refresh_system(self):
        """Refresh toàn bộ hệ thống"""
        logger.info("🔄 Refreshing system...")
        
        # Refresh LLM providers
        self.llm_handler.refresh_providers()
        
        # Clear caches
        self.clear_caches()
        
        # Reset session stats
        self.session_stats = {
            'queries_processed': 0,
            'cache_hits': 0,
            'avg_response_time': 0,
            'started_at': datetime.now(),
            'errors': []
        }
        
        logger.info("✅ System refreshed")
    
    def export_session_data(self, output_path: str) -> bool:
        """Export session data cho analysis"""
        try:
            session_data = {
                'export_time': datetime.now().isoformat(),
                'session_stats': self.session_stats,
                'system_stats': self.get_system_stats(),
                'query_cache_size': len(self.query_cache)
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📊 Session data exported to: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to export session data: {e}")
            return False

# Async context manager cho RAG Engine
class AsyncRAGEngine:
    """Async context manager cho RAG Engine"""
    
    def __init__(self, **kwargs):
        self.engine = LightweightRAGEngine(**kwargs)
        self.kwargs = kwargs
    
    async def __aenter__(self):
        await self.engine.initialize_system()
        return self.engine
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup nếu cần
        pass

# Utility functions
def create_rag_engine(gemini_api_key: str = None, **kwargs) -> LightweightRAGEngine:
    """Factory function tạo RAG engine"""
    
    # Set API key từ environment nếu không có
    if not gemini_api_key:
        gemini_api_key = os.getenv('GEMINI_API_KEY')
    
    return LightweightRAGEngine(
        gemini_api_key=gemini_api_key,
        **kwargs
    )

async def quick_test_rag(documents_path: str = None, gemini_api_key: str = None):
    """Quick test RAG system"""
    print("🧪 Quick testing RAG system...")
    
    engine = create_rag_engine(gemini_api_key=gemini_api_key)
    
    # Initialize
    init_result = await engine.initialize_system(documents_path=documents_path)
    print(f"🔧 Initialization: {init_result['success']} - {init_result['message']}")
    
    if not init_result['success']:
        return False
    
    # Test query
    test_questions = [
        "Người nước ngoài nhập cảnh Việt Nam cần visa gì?",
        "Thủ tục làm hộ chiếu như thế nào?",
        "Điều kiện cư trú tạm thời tại Việt Nam?"
    ]
    
    for question in test_questions:
        print(f"\n❓ Question: {question}")
        
        result = await engine.query_async(question, k=2)
        
        if result['success']:
            print(f"✅ Answer: {result['answer'][:100]}...")
            print(f"⏱️ Time: {result['metadata']['total_time']}s")
            print(f"🔍 Sources: {len(result['sources'])}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    
    # System stats
    stats = engine.get_system_stats()
    print(f"\n📊 Final stats: {stats['session']['queries_processed']} queries processed")
    
    return True

# Test function
def test_rag_engine():
    """Test RAG engine functionality"""
    return asyncio.run(quick_test_rag())

if __name__ == "__main__":
    test_rag_engine()