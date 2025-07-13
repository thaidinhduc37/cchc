# server/services/vector_rag/debug_rag_search.py
"""
🔍 DETAILED RAG PIPELINE LOGGER
🎯 Log EXACT content at each step: Vector → Rerank → Context
📋 No LLM, just pipeline debugging
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.vector_rag.rag_engine import RAGEngine
from services.vector_rag.vector_store import VectorSearcher
from services.vector_rag.reranker import ReRanker
from services.vector_rag.context_optimizer import ContextOptimizer

class DetailedRAGLogger:
    """Log exact content at each RAG pipeline step"""
    
    def __init__(self):
        self.log_file = Path("services/vector_rag") / f"rag_pipeline_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.log_file.parent.mkdir(exist_ok=True)
        
        # 4 conversation scenarios to test
        self.scenarios = [
            # Scenario 1: First-time passport guidance
            [
                "Tôi chưa làm hộ chiếu lần nào, hãy hướng dẫn tôi",
                "Tôi tạm trú ở Quảng Ninh thì sao"
            ],
            
            # Scenario 2: Minor travel consultation  
            [
                "12 tuổi tự ra nước ngoài được không",
                "Khoản 2 Điều 33 Luật xuất cảnh, nhập cảnh quy định như thế nào",
            ],
            
            # Scenario 3: Legal situation inquiry
            [
                "Tôi bị khởi tố thì có xuất cảnh được không"
            ],
            
            # Scenario 4: Visa exemption information
            [
                "Có những nước nào miễn visa cho người Việt Nam mang hộ chiếu phổ thông"
            ]
        ]
    
    def log(self, message):
        """Log to both console and file"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")
    
    async def debug_pipeline(self):
        """Debug complete pipeline with detailed logging"""
        self.log("🔍 DETAILED RAG PIPELINE DEBUG")
        self.log("=" * 80)
        
        # Initialize components
        try:
            self.searcher = VectorSearcher()
            await self.searcher.initialize()
            self.reranker = ReRanker()
            self.context_optimizer = ContextOptimizer()
            self.log("✅ All components initialized")
        except Exception as e:
            self.log(f"❌ Component initialization failed: {e}")
            return
        
        for i, scenario in enumerate(self.scenarios, 1):
            self.log(f"\n🧪 SCENARIO {i}")
            self.log("-" * 40)
            
            for j, query in enumerate(scenario):
                self.log(f"\nQuery {j+1}: '{query}'")
                await self._debug_single_query(query)
    
    async def _debug_single_query(self, query):
        """Debug single query with detailed content logging"""
        
        try:
            # STEP 1: VECTOR SEARCH DETAILED
            self.log(f"\n1️⃣ VECTOR SEARCH:")
            search_results = await self.searcher.search(query, k=10)
            
            if not search_results:
                self.log("   ❌ No search results found")
                return
            
            self.log(f"   📊 Found {len(search_results)} results")
            
            # Log top 5 results with actual content
            for i, result in enumerate(search_results[:5], 1):
                content = result.get('content', '')
                content_type = result.get('metadata', {}).get('content_type', 'unknown')
                score = result.get('final_score', 0)
                metadata = result.get('metadata', {})
                
                self.log(f"   [{i}] Type: {content_type}, Score: {score:.3f}")
                self.log(f"       Metadata: {metadata}")
                self.log(f"       Content: {content[:300]}...")
                self.log("-" * 50)
            
            # STEP 2: RERANKING DETAILED
            self.log(f"2️⃣ RERANKING:")
            
            # Build query features
            query_features = {
                'original_query': query,
                'conversation_context': '',
                'context_summary': {},
                'citizen_profile': {},
                'response_requirements': {}
            }
            
            reranked_results = self.reranker.rerank(
                query=query,
                chunks=search_results,
                context_tier='unified',
                query_features=query_features
            )
            
            if not reranked_results:
                self.log("   ❌ No reranked results")
                return
            
            self.log(f"   📊 Reranked {len(reranked_results)} results")
            
            # Log top 3 after reranking
            for i, result in enumerate(reranked_results[:3], 1):
                content = result.get('content', '')
                content_type = result.get('metadata', {}).get('content_type', 'unknown')
                final_score = result.get('final_score', 0)
                match_analysis = result.get('match_analysis', {})
                
                self.log(f"   [{i}] Type: {content_type}, Score: {final_score:.3f}")
                self.log(f"       Question Type: {match_analysis.get('question_type', 'unknown')}")
                self.log(f"       Direct Answer: {match_analysis.get('is_direct_answer', False)}")
                self.log(f"       Answer Quality: {match_analysis.get('answer_quality', 'unknown')}")
                self.log(f"       Content: {content[:300]}...")
                self.log("-" * 50)
            
            # STEP 3: CONTEXT BUILDING DETAILED
            self.log(f"3️⃣ CONTEXT BUILDING:")
            
            # Build query features for context
            context_query_features = type('QueryFeatures', (), {
                'original_query': query,
                'context_summary': {},
                'needs_conclusion': 'được không' in query.lower()
            })()
            
            context_result = await self.context_optimizer.optimize_context(
                reranked_results, 
                context_query_features
            )
            
            if context_result:
                self.log(f"   📊 Primary content length: {len(context_result.primary_content)}")
                self.log(f"   📜 Primary citation: {context_result.primary_citation or 'None'}")
                self.log(f"   🎯 Answer type: {context_result.answer_type}")
                self.log(f"   ❓ Needs conclusion: {context_result.needs_conclusion}")
                self.log(f"   📝 Primary content FULL:")
                self.log(f"       {context_result.primary_content}")
                self.log("=" * 60)
                
                if context_result.supporting_contents:
                    self.log(f"   📚 Supporting contents: {len(context_result.supporting_contents)}")
                    for i, support in enumerate(context_result.supporting_contents[:2], 1):
                        support_content = support.get('content', '') if isinstance(support, dict) else str(support)
                        self.log(f"       Support {i}: {support_content}")
            else:
                self.log("   ❌ Context building failed")
        
        except Exception as e:
            self.log(f"   ❌ Pipeline error: {e}")
            import traceback
            self.log(f"   🔍 Traceback: {traceback.format_exc()}")

async def main():
    """Main debug function"""
    logger = DetailedRAGLogger()
    
    print("🔍 Starting detailed RAG pipeline debug...")
    print(f"📄 Log file: {logger.log_file}")
    
    await logger.debug_pipeline()
    
    print(f"\n✅ Debug completed! Check log file: {logger.log_file}")

if __name__ == "__main__":
    asyncio.run(main())