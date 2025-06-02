# rag_engine.py - RAG Engine chính kết hợp tất cả modules
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from langchain.chains import RetrievalQA
from langchain.schema import Document

from services.vector_rag.config import SystemConfig
from services.vector_rag.document_processor import DocumentProcessor
from services.vector_rag.vector_manager import VectorStoreManager
from services.vector_rag.response_processor import ResponseProcessor, ResponseCache
from services.vector_rag.llm_handler import LLMHandler

logger = logging.getLogger(__name__)

class RAGEngine:
    """RAG Engine chính - kết hợp tất cả modules"""
    
    def __init__(self, 
                 model_path: str = None,
                 system_config: SystemConfig = None):
        
        self.config = system_config or SystemConfig()
        
        # Initialize components
        self.doc_processor = DocumentProcessor(system_config=self.config)
        self.vector_manager = VectorStoreManager(system_config=self.config)
        self.llm_handler = LLMHandler(model_path=model_path)
        
        # Response processing
        self.response_processor = ResponseProcessor()
        self.response_cache = ResponseCache() if self.config.enable_cache else None
        
        # QA chains cho từng domain
        self.qa_chains: Dict[str, RetrievalQA] = {}
        self.domain_stats = {}
        
        # Session management
        self.session_history = []
        self.current_domain = None
    
    def initialize_system(self, 
                         data_path: str = None, 
                         domains: List[str] = None,
                         force_rebuild: bool = False) -> Dict[str, Any]:
        """Khởi tạo toàn bộ hệ thống"""
        
        data_path = data_path or self.config.data_path
        result = {
            'success': True,
            'message': '',
            'domains_created': [],
            'stats': {}
        }
        
        try:
            logger.info("🚀 Initializing RAG system...")
            
            # Check if vector stores exist
            existing_stores = self.vector_manager.load_all_domain_stores()
            
            if existing_stores and not force_rebuild:
                logger.info("📂 Found existing vector stores, loading...")
                self._create_qa_chains_from_stores(existing_stores)
                result['domains_created'] = list(existing_stores.keys())
                result['message'] = "Loaded existing vector stores"
            
            else:
                logger.info("🔨 Building new vector stores...")
                
                if domains:
                    # Build specific domains
                    for domain in domains:
                        self._build_domain_system(data_path, domain)
                        result['domains_created'].append(domain)
                else:
                    # Auto-detect and build all domains
                    documents = self.doc_processor.process_documents(data_path)
                    if documents:
                        stores = self.vector_manager.create_multi_domain_stores(documents)
                        self._create_qa_chains_from_stores(stores)
                        result['domains_created'] = list(stores.keys())
                
                result['message'] = f"Built vector stores for {len(result['domains_created'])} domains"
            
            # Get system stats
            result['stats'] = self._get_system_stats()
            
            logger.info(f"✅ System initialized successfully: {result['domains_created']}")
            
        except Exception as e:
            logger.error(f"❌ Error initializing system: {str(e)}")
            result['success'] = False
            result['message'] = f"Error: {str(e)}"
        
        return result
    
    def _build_domain_system(self, data_path: str, domain: str):
        """Xây dựng hệ thống cho một domain cụ thể"""
        # Process documents for domain
        documents = self.doc_processor.process_documents(
            os.path.join(data_path, domain), 
            domain=domain
        )
        
        if documents:
            # Create vector store
            vector_store = self.vector_manager.create_domain_vector_store(documents, domain)
            
            if vector_store:
                # Create QA chain
                self._create_qa_chain_for_domain(domain, vector_store)
    
    def _create_qa_chains_from_stores(self, vector_stores: Dict[str, Any]):
        """Tạo QA chains từ vector stores"""
        for domain, vector_store in vector_stores.items():
            self._create_qa_chain_for_domain(domain, vector_store)
    
    def _create_qa_chain_for_domain(self, domain: str, vector_store):
        """Tạo QA chain cho domain cụ thể"""
        try:
            # Get retriever
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )
            
            # Get prompt template for domain
            prompt = self.llm_handler.create_prompt_template(domain)
            
            # Create QA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm_handler.llm,
                chain_type="stuff",
                retriever=retriever,
                chain_type_kwargs={"prompt": prompt},
                return_source_documents=True
            )
            
            self.qa_chains[domain] = qa_chain
            logger.info(f"✅ QA chain created for domain: {domain}")
            
        except Exception as e:
            logger.error(f"❌ Error creating QA chain for {domain}: {str(e)}")
    
    def query(self, 
              question: str, 
              domain: str = None,
              use_cache: bool = True,
              return_sources: bool = True) -> Dict[str, Any]:
        """Trả lời câu hỏi với RAG"""
        
        # Check cache first
        if use_cache and self.response_cache:
            cached_response = self.response_cache.get(question, domain)
            if cached_response:
                return {
                    'answer': cached_response,
                    'domain': domain,
                    'source_documents': [],
                    'cached': True,
                    'success': True
                }
        
        try:
            # Auto-detect domain if not specified
            if not domain:
                domain = self._detect_question_domain(question)
            
            # Get appropriate QA chain
            qa_chain = self._get_qa_chain(domain)
            if not qa_chain:
                return self._handle_no_domain_error(domain)
            
            # Execute query
            result = qa_chain({"query": question})
            
            # Process response
            processed_answer = self._process_response(
                result["result"], 
                domain,
                result.get("source_documents", [])
            )
            
            # Cache response
            if use_cache and self.response_cache:
                self.response_cache.set(question, processed_answer, domain)
            
            # Log interaction
            self._log_interaction(question, processed_answer, domain)
            
            response = {
                'answer': processed_answer,
                'domain': domain,
                'source_documents': result.get("source_documents", []) if return_sources else [],
                'cached': False,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing query: {str(e)}")
            return {
                'answer': f"Xin lỗi, đã có lỗi xảy ra khi xử lý câu hỏi: {str(e)}",
                'domain': domain,
                'source_documents': [],
                'cached': False,
                'success': False,
                'error': str(e)
            }
    
    def _detect_question_domain(self, question: str) -> str:
        """Tự động detect domain từ câu hỏi"""
        question_lower = question.lower()
        
        # Keywords cho từng domain
        domain_keywords = {
            'dich_vu_cong': [
                'thủ tục', 'hồ sơ', 'giấy tờ', 'đăng ký', 'cấp phép',
                'dịch vụ công', 'trực tuyến', 'phí lệ phí', 'thời gian xử lý'
            ],
            'luat': [
                'luật', 'điều', 'khoản', 'quy định', 'chế재', 'vi phạm',
                'xử phạt', 'bộ luật', 'hiệu lực'
            ],
            'thong_tu': [
                'thông tư', 'hướng dẫn', 'quy trình', 'triển khai'
            ],
            'nghi_dinh': [
                'nghị định', 'quy định', 'ban hành', 'thi hành'
            ]
        }
        
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in question_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            best_domain = max(domain_scores, key=domain_scores.get)
            return best_domain
        
        # Default fallback
        return list(self.qa_chains.keys())[0] if self.qa_chains else 'general'
    
    def _get_qa_chain(self, domain: str):
        """Lấy QA chain cho domain"""
        if domain in self.qa_chains:
            return self.qa_chains[domain]
        
        # Fallback to first available domain
        if self.qa_chains:
            fallback_domain = list(self.qa_chains.keys())[0]
            logger.warning(f"Domain {domain} not found, using {fallback_domain}")
            return self.qa_chains[fallback_domain]
        
        return None
    
    def _handle_no_domain_error(self, domain: str) -> Dict[str, Any]:
        """Xử lý lỗi khi không tìm thấy domain"""
        available_domains = list(self.qa_chains.keys())
        error_msg = f"Không tìm thấy domain '{domain}'. Domains có sẵn: {available_domains}"
        
        return {
            'answer': error_msg,
            'domain': domain,
            'source_documents': [],
            'success': False,
            'available_domains': available_domains
        }
    
    def _process_response(self, 
                         raw_response: str, 
                         domain: str,
                         source_docs: List[Document]) -> str:
        """Xử lý và format response"""
        
        # Validate response
        validation = self.llm_handler.validate_response(raw_response, domain)
        
        # Format response
        formatted_response = self.response_processor.format_legal_response(
            raw_response, domain
        )
        
        # Add confidence indicator
        if validation['confidence'] < 1.0:
            formatted_response = self.response_processor.add_confidence_indicator(
                formatted_response, validation['confidence']
            )
        
        # Add source references
        if source_docs:
            formatted_response = self.response_processor.add_source_references(
                formatted_response, source_docs[:3]  # Top 3 sources
            )
        
        return formatted_response
    
    def _log_interaction(self, question: str, answer: str, domain: str):
        """Log tương tác để phân tích sau"""
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'answer': answer,
            'domain': domain,
            'session_id': id(self)  # Simple session tracking
        }
        
        self.session_history.append(interaction)
        
        # Keep only last 100 interactions in memory
        if len(self.session_history) > 100:
            self.session_history = self.session_history[-100:]
        
        # Optional: Save to file for analysis
        if self.config.logs_path:
            self._save_interaction_log(interaction)
    
    def _save_interaction_log(self, interaction: Dict[str, Any]):
        """Lưu log tương tác ra file"""
        try:
            log_file = os.path.join(self.config.logs_path, "interactions.jsonl")
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(interaction, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Error saving interaction log: {str(e)}")
    
    def get_conversation_context(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Lấy context cuộc hội thoại gần đây"""
        return self.session_history[-limit:] if self.session_history else []
    
    def multi_domain_search(self, question: str, k: int = 3) -> Dict[str, List[Document]]:
        """Tìm kiếm trong tất cả domains"""
        return self.vector_manager.search_all_domains(question, k)
    
    def add_documents(self, documents: List[Document], domain: str = None):
        """Thêm documents mới vào hệ thống"""
        if not domain:
            # Auto-detect domains from documents
            domain_docs = {}
            for doc in documents:
                doc_domain = doc.metadata.get('domain', 'general')
                if doc_domain not in domain_docs:
                    domain_docs[doc_domain] = []
                domain_docs[doc_domain].append(doc)
            
            for doc_domain, docs in domain_docs.items():
                self.vector_manager.add_documents_to_domain(docs, doc_domain)
        else:
            self.vector_manager.add_documents_to_domain(documents, domain)
        
        logger.info(f"Added {len(documents)} documents to system")
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """Lấy thống kê hệ thống"""
        stats = {
            'domains': list(self.qa_chains.keys()),
            'total_domains': len(self.qa_chains),
            'vector_stats': self.vector_manager.get_domain_stats(),
            'session_interactions': len(self.session_history),
            'cache_size': len(self.response_cache.cache) if self.response_cache else 0,
            'system_config': {
                'cache_enabled': self.config.enable_cache,
                'data_path': self.config.data_path,
                'vector_store_path': self.config.vector_store_path
            }
        }
        return stats
    
    def export_system_state(self) -> Dict[str, Any]:
        """Export trạng thái hệ thống để backup"""
        return {
            'domains': list(self.qa_chains.keys()),
            'stats': self._get_system_stats(),
            'session_history': self.session_history,
            'export_time': datetime.now().isoformat()
        }
    
    def clear_cache(self):
        """Xóa cache"""
        if self.response_cache:
            self.response_cache.clear()
            logger.info("Cache cleared")
    
    def reload_domain(self, domain: str):
        """Reload một domain cụ thể"""
        try:
            # Reload vector store
            vector_store = self.vector_manager.load_domain_vector_store(domain)
            if vector_store:
                # Recreate QA chain
                self._create_qa_chain_for_domain(domain, vector_store)
                logger.info(f"✅ Reloaded domain: {domain}")
                return True
        except Exception as e:
            logger.error(f"❌ Error reloading domain {domain}: {str(e)}")
        return False