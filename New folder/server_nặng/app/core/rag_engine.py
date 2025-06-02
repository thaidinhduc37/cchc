"""
🤖 RAG Engine - Legal Q&A Engine với Hybrid Search
Priority: Excel Q&A → Vector Search → LLM Generation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json
import pickle
from pathlib import Path
from fuzzywuzzy import fuzz, process
import re

# Vector search imports
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False
    logging.warning("Vector search dependencies not available")

logger = logging.getLogger(__name__)

class SearchMethod(Enum):
    EXCEL_EXACT = "excel_exact"
    EXCEL_FUZZY = "excel_fuzzy"
    VECTOR_SEARCH = "vector_search"
    LLM_GENERATION = "llm_generation"
    HYBRID = "hybrid"

class ConfidenceLevel(Enum):
    HIGH = "high"      # > 0.8
    MEDIUM = "medium"  # 0.5 - 0.8
    LOW = "low"        # < 0.5

@dataclass
class SearchResult:
    """Kết quả search từ một method"""
    content: str
    confidence: float
    method: SearchMethod
    source: str
    metadata: Dict[str, Any] = None

@dataclass
class RAGResponse:
    """Response từ RAG Engine"""
    answer: str
    confidence: float
    confidence_level: ConfidenceLevel
    sources: List[SearchResult]
    method_used: SearchMethod
    suggest_flow: Optional[str] = None
    follow_up_questions: List[str] = None
    metadata: Dict[str, Any] = None

class RAGEngine:
    """
    RAG Engine - Core engine cho Legal Q&A
    Hybrid search với multiple fallback strategies
    """
    
    def __init__(self, data_path: str = "data", model_name: str = "all-MiniLM-L6-v2"):
        self.data_path = Path(data_path)
        self.model_name = model_name
        
        # Initialize components
        self.excel_data = {}  # Cache Excel data per domain
        self.vector_collections = {}  # ChromaDB collections per domain
        self.embedding_model = None
        self.chroma_client = None
        
        # Search thresholds
        self.excel_exact_threshold = 0.95
        self.excel_fuzzy_threshold = 0.75
        self.vector_similarity_threshold = 0.7
        
        # Initialize vector search if available
        if VECTOR_AVAILABLE:
            self._initialize_vector_search()

    def _initialize_vector_search(self):
        """Initialize vector search components"""
        try:
            self.embedding_model = SentenceTransformer(self.model_name)
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.data_path / "shared" / "vector_db")
            )
            logger.info("Vector search initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector search: {e}")
            self.embedding_model = None
            self.chroma_client = None

    def search_legal_qa(self, query: str, domain: str) -> RAGResponse:
        """
        Main search method - hybrid search với multiple strategies
        
        Args:
            query: User query
            domain: Domain to search in
            
        Returns:
            RAGResponse với best answer found
        """
        try:
            # Normalize query
            normalized_query = self._normalize_query(query)
            
            # Track all search results
            all_results = []
            
            # 1. Excel exact search
            excel_results = self._search_excel_qa(normalized_query, domain)
            all_results.extend(excel_results)
            
            # 2. Vector search (if available and Excel results not confident enough)
            best_excel_confidence = max([r.confidence for r in excel_results], default=0)
            if VECTOR_AVAILABLE and best_excel_confidence < self.excel_exact_threshold:
                vector_results = self._search_vector_documents(normalized_query, domain)
                all_results.extend(vector_results)
            
            # 3. Cross-domain search if domain-specific results are weak
            domain_results = [r for r in all_results if domain in r.source]
            if not domain_results or max([r.confidence for r in domain_results], default=0) < 0.6:
                cross_domain_results = self._search_cross_domain(normalized_query)
                all_results.extend(cross_domain_results)
            
            # 4. Select best result and generate response
            if all_results:
                best_result = max(all_results, key=lambda r: r.confidence)
                return self._generate_rag_response(query, best_result, all_results, domain)
            else:
                # 5. LLM generation as fallback
                return self._generate_llm_fallback(query, domain)
                
        except Exception as e:
            logger.error(f"Error in search_legal_qa: {e}")
            return self._create_error_response(str(e))

    def _search_excel_qa(self, query: str, domain: str) -> List[SearchResult]:
        """Search trong Excel Q&A data"""
        
        results = []
        
        try:
            # Load Excel data for domain
            excel_data = self._load_excel_data(domain)
            if excel_data.empty:
                return results
            
            # Ensure required columns exist
            required_cols = ['question', 'answer']
            if not all(col in excel_data.columns for col in required_cols):
                logger.warning(f"Missing required columns in Excel data for {domain}")
                return results
            
            # Exact match search
            for idx, row in excel_data.iterrows():
                question = str(row['question']).strip()
                answer = str(row['answer']).strip()
                
                # Exact match
                exact_score = fuzz.ratio(query.lower(), question.lower()) / 100
                if exact_score >= self.excel_exact_threshold:
                    results.append(SearchResult(
                        content=answer,
                        confidence=exact_score,
                        method=SearchMethod.EXCEL_EXACT,
                        source=f"{domain}/question.xlsx",
                        metadata={
                            "question": question,
                            "row_index": idx,
                            "exact_match": True
                        }
                    ))
            
            # Fuzzy match search if no exact matches
            if not results:
                fuzzy_matches = process.extract(
                    query, 
                    excel_data['question'].tolist(), 
                    limit=3,
                    scorer=fuzz.token_sort_ratio
                )
                
                for question, score in fuzzy_matches:
                    if score / 100 >= self.excel_fuzzy_threshold:
                        # Find corresponding answer
                        answer_row = excel_data[excel_data['question'] == question]
                        if not answer_row.empty:
                            answer = str(answer_row.iloc[0]['answer'])
                            results.append(SearchResult(
                                content=answer,
                                confidence=score / 100,
                                method=SearchMethod.EXCEL_FUZZY,
                                source=f"{domain}/question.xlsx",
                                metadata={
                                    "question": question,
                                    "fuzzy_score": score,
                                    "exact_match": False
                                }
                            ))
            
            logger.info(f"Excel search found {len(results)} results for domain {domain}")
            return results
            
        except Exception as e:
            logger.error(f"Error in Excel search for {domain}: {e}")
            return results

    def _search_vector_documents(self, query: str, domain: str) -> List[SearchResult]:
        """Search trong vector database của documents"""
        
        results = []
        
        if not VECTOR_AVAILABLE or not self.embedding_model:
            return results
        
        try:
            # Get or create collection for domain
            collection = self._get_vector_collection(domain)
            if not collection:
                return results
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Search in vector database
            search_results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                include=['documents', 'metadatas', 'distances']
            )
            
            if search_results['documents']:
                for i, (doc, metadata, distance) in enumerate(zip(
                    search_results['documents'][0],
                    search_results['metadatas'][0],
                    search_results['distances'][0]
                )):
                    # Convert distance to confidence (lower distance = higher confidence)
                    confidence = max(0, 1 - distance)
                    
                    if confidence >= self.vector_similarity_threshold:
                        results.append(SearchResult(
                            content=doc,
                            confidence=confidence,
                            method=SearchMethod.VECTOR_SEARCH,
                            source=f"{domain}/documents/{metadata.get('filename', 'unknown')}",
                            metadata={
                                "chunk_id": metadata.get('chunk_id'),
                                "distance": distance,
                                "page": metadata.get('page')
                            }
                        ))
            
            logger.info(f"Vector search found {len(results)} results for domain {domain}")
            return results
            
        except Exception as e:
            logger.error(f"Error in vector search for {domain}: {e}")
            return results

    def _search_cross_domain(self, query: str) -> List[SearchResult]:
        """Search across all domains"""
        
        results = []
        
        try:
            # Search shared/common Q&A
            shared_excel = self._load_excel_data("shared")
            if not shared_excel.empty:
                shared_results = self._search_excel_qa(query, "shared")
                results.extend(shared_results)
            
            # Search other domains with lower confidence
            available_domains = self._get_available_domains()
            for domain in available_domains:
                if domain != "shared":
                    domain_results = self._search_excel_qa(query, domain)
                    # Reduce confidence for cross-domain results
                    for result in domain_results:
                        result.confidence *= 0.8  # Cross-domain penalty
                        result.metadata["cross_domain"] = True
                    results.extend(domain_results)
            
            logger.info(f"Cross-domain search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in cross-domain search: {e}")
            return results

    def _generate_rag_response(self, original_query: str, best_result: SearchResult, 
                             all_results: List[SearchResult], domain: str) -> RAGResponse:
        """Generate final RAG response"""
        
        # Determine confidence level
        confidence_level = self._get_confidence_level(best_result.confidence)
        
        # Format answer
        answer = self._format_answer(best_result, original_query)
        
        # Generate follow-up questions
        follow_ups = self._generate_follow_up_questions(original_query, best_result, domain)
        
        # Suggest flow if appropriate
        flow_suggestion = self._suggest_relevant_flow(original_query, domain)
        
        return RAGResponse(
            answer=answer,
            confidence=best_result.confidence,
            confidence_level=confidence_level,
            sources=all_results[:3],  # Top 3 sources
            method_used=best_result.method,
            suggest_flow=flow_suggestion,
            follow_up_questions=follow_ups,
            metadata={
                "original_query": original_query,
                "domain": domain,
                "search_time": "now",
                "total_sources_found": len(all_results)
            }
        )

    def _generate_llm_fallback(self, query: str, domain: str) -> RAGResponse:
        """Generate LLM fallback response when no good matches found"""
        
        # This would integrate with Gemma service
        fallback_answer = (
            f"Xin lỗi, tôi không tìm thấy thông tin cụ thể về câu hỏi của bạn trong cơ sở dữ liệu "
            f"pháp luật về {domain}. Bạn có thể:\n\n"
            f"1. Đặt lại câu hỏi với từ khóa khác\n"
            f"2. Sử dụng chức năng hướng dẫn từng bước\n"
            f"3. Liên hệ cơ quan chức năng để được hỗ trợ trực tiếp"
        )
        
        return RAGResponse(
            answer=fallback_answer,
            confidence=0.3,
            confidence_level=ConfidenceLevel.LOW,
            sources=[],
            method_used=SearchMethod.LLM_GENERATION,
            suggest_flow=self._suggest_relevant_flow(query, domain),
            follow_up_questions=[
                f"Hướng dẫn thủ tục {domain}",
                f"Quy định về {domain}",
                f"Phí và lệ phí {domain}"
            ],
            metadata={
                "original_query": query,
                "domain": domain,
                "fallback_reason": "No matching content found"
            }
        )

    def _load_excel_data(self, domain: str) -> pd.DataFrame:
        """Load Excel Q&A data for domain"""
        
        if domain in self.excel_data:
            return self.excel_data[domain]
        
        try:
            if domain == "shared":
                excel_file = self.data_path / "shared" / "common_qa.xlsx"
            else:
                excel_file = self.data_path / domain / "question.xlsx"
            
            if excel_file.exists():
                df = pd.read_excel(excel_file)
                # Clean data
                df = df.dropna(subset=['question', 'answer'])
                df['question'] = df['question'].astype(str).str.strip()
                df['answer'] = df['answer'].astype(str).str.strip()
                
                self.excel_data[domain] = df
                logger.info(f"Loaded {len(df)} Q&A pairs for domain {domain}")
                return df
            else:
                logger.warning(f"Excel file not found: {excel_file}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error loading Excel data for {domain}: {e}")
            return pd.DataFrame()

    def _get_vector_collection(self, domain: str):
        """Get or create ChromaDB collection for domain"""
        
        if not self.chroma_client:
            return None
        
        collection_name = f"{domain}_documents"
        
        try:
            if collection_name in self.vector_collections:
                return self.vector_collections[collection_name]
            
            # Get or create collection
            collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={"domain": domain}
            )
            
            self.vector_collections[collection_name] = collection
            return collection
            
        except Exception as e:
            logger.error(f"Error getting vector collection for {domain}: {e}")
            return None

    def _normalize_query(self, query: str) -> str:
        """Normalize user query"""
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Remove special characters but keep Vietnamese
        normalized = re.sub(r'[^\w\s\?]', ' ', normalized)
        
        return normalized

    def _format_answer(self, result: SearchResult, query: str) -> str:
        """Format answer with source attribution"""
        
        answer = result.content
        
        # Add source attribution
        if result.method == SearchMethod.EXCEL_EXACT:
            answer += f"\n\n📋 *Nguồn: Câu hỏi thường gặp*"
        elif result.method == SearchMethod.EXCEL_FUZZY:
            answer += f"\n\n📋 *Nguồn: Câu hỏi tương tự*"
        elif result.method == SearchMethod.VECTOR_SEARCH:
            filename = result.metadata.get('filename', 'văn bản pháp luật')
            answer += f"\n\n📄 *Nguồn: {filename}*"
        
        # Add confidence indicator
        if result.confidence >= 0.9:
            answer += " ✅"
        elif result.confidence >= 0.7:
            answer += " ⚠️"
        
        return answer

    def _get_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Determine confidence level"""
        
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.5:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _generate_follow_up_questions(self, query: str, result: SearchResult, domain: str) -> List[str]:
        """Generate contextual follow-up questions"""
        
        follow_ups = []
        
        # Domain-specific follow-ups
        if domain == "xuatnhapcanh":
            follow_ups = [
                "Thủ tục làm hộ chiếu như thế nào?",
                "Phí làm hộ chiếu bao nhiêu?",
                "Thời gian làm hộ chiếu bao lâu?",
                "Cần giấy tờ gì để làm hộ chiếu?"
            ]
        elif domain == "cancuoc":
            follow_ups = [
                "Cách làm căn cước công dân",
                "Phí làm CCCD",
                "Thời gian làm CCCD",
                "Giấy tờ cần thiết làm CCCD"
            ]
        
        return follow_ups[:3]  # Return top 3

    def _suggest_relevant_flow(self, query: str, domain: str) -> Optional[str]:
        """Suggest relevant flow based on query"""
        
        if domain == "xuatnhapcanh":
            if any(word in query.lower() for word in ["làm", "cấp", "thủ tục", "hướng dẫn"]):
                if any(word in query.lower() for word in ["mới", "lần đầu"]):
                    return "cap_moi_tu_14"
                elif any(word in query.lower() for word in ["hết hạn", "cấp lại"]):
                    return "cap_lai_het_han"
        
        return None

    def _get_available_domains(self) -> List[str]:
        """Get list of available domains"""
        
        domains = []
        for item in self.data_path.iterdir():
            if item.is_dir() and item.name not in ["shared", "processed"]:
                domains.append(item.name)
        return domains

    def _create_error_response(self, error_msg: str) -> RAGResponse:
        """Create error response"""
        
        return RAGResponse(
            answer=f"Xin lỗi, đã xảy ra lỗi: {error_msg}",
            confidence=0.0,
            confidence_level=ConfidenceLevel.LOW,
            sources=[],
            method_used=SearchMethod.LLM_GENERATION,
            metadata={"error": error_msg}
        )

    def rebuild_vector_index(self, domain: str) -> bool:
        """Rebuild vector index for domain (admin function)"""
        
        if not VECTOR_AVAILABLE:
            logger.error("Vector search not available")
            return False
        
        try:
            # This would process documents and rebuild embeddings
            # Implementation depends on document processing pipeline
            logger.info(f"Vector index rebuild started for {domain}")
            
            # Delete existing collection
            collection_name = f"{domain}_documents"
            try:
                self.chroma_client.delete_collection(collection_name)
            except:
                pass
            
            # Create new collection
            collection = self.chroma_client.create_collection(
                name=collection_name,
                metadata={"domain": domain}
            )
            
            # Process documents (placeholder)
            # This would read PDFs, split into chunks, create embeddings
            
            logger.info(f"Vector index rebuild completed for {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Error rebuilding vector index for {domain}: {e}")
            return False

# Test cases
if __name__ == "__main__":
    rag = RAGEngine("data")
    
    test_queries = [
        "Phí làm hộ chiếu bao nhiêu?",
        "Thủ tục cấp hộ chiếu như thế nào?",
        "Thời gian làm hộ chiếu bao lâu?",
        "Cần giấy tờ gì để làm CCCD?",
        "Quy định về xuất nhập cảnh",
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        response = rag.search_legal_qa(query, "xuatnhapcanh")
        print(f"📝 Answer: {response.answer[:100]}...")
        print(f"🎯 Confidence: {response.confidence:.2f} ({response.confidence_level.value})")
        print(f"🔧 Method: {response.method_used.value}")
        if response.suggest_flow:
            print(f"📋 Suggested flow: {response.suggest_flow}")