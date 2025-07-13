# services/debug_rag_services.py - DETAILED LOGGING + API TESTING
"""
🧪 RAG PIPELINE DETAILED DEBUG - WITH API TESTING
🎯 Log everything to file, minimal console, test actual API responses
📋 Test different scenarios, validate final answers
"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime
import json

# Add parent to path  
sys.path.append(str(Path(__file__).parent.parent))

# Also add services to path for imports
sys.path.append(str(Path(__file__).parent))

# Disable framework logs
import logging
logging.getLogger('sentence_transformers').setLevel(logging.CRITICAL)
logging.getLogger('transformers').setLevel(logging.CRITICAL)
logging.getLogger('torch').setLevel(logging.CRITICAL)

from services.unified_processor import UnifiedProcessor, process_user_query
from services.vector_rag.rag_engine import RAGEngine, ResponseContext

class DetailedRAGDebugger:
    """Detailed RAG Debugger với comprehensive logging + API testing"""
    
    def __init__(self):
        self.unified = UnifiedProcessor()
        self.rag_engine = None
        
        # Setup detailed log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = Path(f"debug_rag_detailed_{timestamp}.log")
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"RAG PIPELINE DETAILED DEBUG - {datetime.now()}\n")
            f.write("="*100 + "\n\n")
    
    def log_detailed(self, step: str, data: any, description: str = ""):
        """Log chi tiết mọi thứ vào file với datetime handling"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {step}\n")
            f.write("-" * 80 + "\n")
            
            if description:
                f.write(f"Description: {description}\n\n")
            
            if isinstance(data, dict):
                # Convert datetime objects to string before JSON
                cleaned_data = self._clean_data_for_json(data)
                f.write(json.dumps(cleaned_data, indent=2, ensure_ascii=False))
            elif isinstance(data, list):
                f.write(f"List with {len(data)} items:\n")
                for i, item in enumerate(data[:5]):  # Show first 5
                    f.write(f"  [{i}] {str(item)[:200]}...\n")
                if len(data) > 5:
                    f.write(f"  ... and {len(data) - 5} more items\n")
            else:
                f.write(str(data))
            
            f.write("\n\n" + "="*80 + "\n\n")
    
    def _clean_data_for_json(self, data):
        """Clean data để JSON serializable"""
        if isinstance(data, dict):
            cleaned = {}
            for key, value in data.items():
                if isinstance(value, datetime):
                    cleaned[key] = value.isoformat()
                elif isinstance(value, dict):
                    cleaned[key] = self._clean_data_for_json(value)
                elif isinstance(value, list):
                    cleaned[key] = [self._clean_data_for_json(item) if isinstance(item, (dict, list)) else str(item) if isinstance(item, datetime) else item for item in value]
                else:
                    cleaned[key] = value
            return cleaned
        elif isinstance(data, list):
            return [self._clean_data_for_json(item) if isinstance(item, (dict, list)) else str(item) if isinstance(item, datetime) else item for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data
    
    async def initialize(self):
        """Initialize với detailed logging"""
        print("🔧 Initializing RAG Pipeline...")
        
        try:
            self.rag_engine = RAGEngine()
            init_result = await self.rag_engine.initialize()
            
            self.log_detailed("RAG_ENGINE_INIT", init_result, "RAG Engine initialization result")
            
            if init_result['success']:
                print(f"✅ RAG Engine ready")
                return True
            else:
                print(f"❌ RAG Engine failed: {init_result['message']}")
                return False
                
        except Exception as e:
            print(f"❌ RAG Engine exception: {e}")
            self.log_detailed("RAG_ENGINE_INIT_ERROR", {"error": str(e)}, "RAG Engine initialization error")
            return False
    
    async def test_comprehensive_scenarios(self):
        """Test different scenarios với detailed logging"""
        print("\n" + "="*60)
        print("🧪 RAG PIPELINE DETAILED DEBUG")
        print(f"📄 Detailed logs: {self.log_file}")
        print("="*60)
        
        if not await self.initialize():
            print("❌ Cannot proceed - RAG Engine failed")
            return
        
        # Test scenarios với different questions
        await self.test_scenario("Làm hộ chiếu mới cần gì?", "test_procedure", "Simple Procedure")
        await self.test_scenario("Con tôi 8 tuổi đi Singapore cần thủ tục gì?", "test_minor", "Minor Travel")
        await self.test_scenario("Khoản 3 Điều 15 quy định thế nào?", "test_legal", "Legal Reference")
        
        # Multi-turn conversation
        await self.test_multiturn_conversation()
        
        print(f"\n✅ All tests completed. Check detailed logs: {self.log_file}")
    
    async def test_scenario(self, query: str, user_id: str, scenario_name: str):
        """Test single scenario với full pipeline"""
        print(f"\n🎯 {scenario_name}: '{query}'")
        
        self.log_detailed("SCENARIO_START", {
            "scenario": scenario_name,
            "query": query,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }, f"Starting scenario: {scenario_name}")
        
        # === STEP 1: UNIFIED PROCESSING ===
        try:
            # Get conversation context
            conversation_context = self.unified.conversation.get_conversation_context(user_id)
            self.log_detailed("CONVERSATION_CONTEXT", conversation_context, "Current conversation context")
            
            # Resolve vague query
            resolved_query = self.unified.conversation.resolve_vague_query(user_id, query)
            self.log_detailed("VAGUE_QUERY_RESOLUTION", {
                "original": query,
                "resolved": resolved_query,
                "changed": resolved_query != query
            }, "Vague query resolution")
            
            # Extract entities
            entities = self.unified.conversation._extract_entities(query)
            self.log_detailed("ENTITY_EXTRACTION", entities, "Extracted entities from query")
            
            # Query analysis
            query_analysis = self.unified._analyze_query(resolved_query, conversation_context)
            self.log_detailed("QUERY_ANALYSIS", query_analysis, "Query analysis result")
            
            # Build RAG context
            rag_context = self.unified._build_rag_context(
                resolved_query, query, conversation_context, query_analysis, "xuatnhapcanh"
            )
            self.log_detailed("RAG_CONTEXT_BUILT", rag_context, "Built RAG context for processing")
            
        except Exception as e:
            print(f"   ❌ Unified processing failed: {e}")
            self.log_detailed("UNIFIED_ERROR", {"error": str(e)}, "Unified processing error")
            return
        
        # === STEP 2: RAG ENGINE PROCESSING ===
        try:
            # Extract unified context
            unified_context = self.rag_engine._extract_unified_context(rag_context)
            self.log_detailed("UNIFIED_CONTEXT_EXTRACTED", unified_context, "RAG Engine unified context extraction")
            
            # Vector search
            search_results = await self.rag_engine._context_aware_search(
                resolved_query, unified_context, k=10
            )
            self.log_detailed("VECTOR_SEARCH_RESULTS", {
                "query": resolved_query,
                "results_count": len(search_results),
                "results": search_results[:3]  # Top 3 for logging
            }, "Vector search results")
            
            # Reranking
            reranked_results = await self.rag_engine._context_aware_reranking(
                resolved_query, search_results, unified_context
            )
            self.log_detailed("RERANKED_RESULTS", {
                "query": resolved_query,
                "results_count": len(reranked_results),
                "results": reranked_results[:3]  # Top 3 for logging
            }, "Reranked results")
            
            # Context optimization
            rich_context = await self.rag_engine._build_rich_context(
                resolved_query, reranked_results, unified_context
            )
            self.log_detailed("RICH_CONTEXT_BUILT", {
                "primary_content": getattr(rich_context, 'primary_content', '')[:300],
                "primary_citation": getattr(rich_context, 'primary_citation', ''),
                "answer_type": getattr(rich_context, 'answer_type', ''),
                "needs_conclusion": getattr(rich_context, 'needs_conclusion', False)
            }, "Rich context optimization result")
            
            # Build response context
            response_context = self.rag_engine._build_response_context(
                resolved_query, rich_context, unified_context
            )
            self.log_detailed("RESPONSE_CONTEXT_BUILT", {
                "query": response_context.query if response_context else None,
                "context_note": response_context.context_note if response_context else None,
                "citizen_note": response_context.citizen_note if response_context else None,
                "primary_citation": response_context.primary_citation if response_context else None,
                "has_response_context": response_context is not None
            }, "Response context building result")
            
        except Exception as e:
            print(f"   ❌ RAG processing failed: {e}")
            self.log_detailed("RAG_PROCESSING_ERROR", {"error": str(e)}, "RAG processing error")
            return
        
        # === STEP 3: LLM RESPONSE GENERATION ===
        try:
            if response_context:
                # Use ResponseContext method
                llm_result = await self.rag_engine.llm_handler.generate_response_with_context(response_context)
                self.log_detailed("LLM_RESPONSE_WITH_CONTEXT", {
                    "success": llm_result.get('success'),
                    "provider": llm_result.get('provider'),
                    "method": llm_result.get('method'),
                    "answer_length": len(llm_result.get('answer', '')),
                    "answer_preview": llm_result.get('answer', '')[:200]
                }, "LLM response with ResponseContext")
            else:
                # Fallback method
                llm_result = await self.rag_engine.llm_handler.generate_response(
                    resolved_query, rich_context, {"unified_context": unified_context}
                )
                self.log_detailed("LLM_RESPONSE_FALLBACK", {
                    "success": llm_result.get('success'),
                    "provider": llm_result.get('provider'),
                    "answer_length": len(llm_result.get('answer', '')),
                    "answer_preview": llm_result.get('answer', '')[:200]
                }, "LLM response fallback method")
            
            # Show final answer
            if llm_result.get('success'):
                final_answer = llm_result['answer']
                print(f"   ✅ Response generated ({llm_result.get('provider', 'unknown')})")
                print(f"   📝 Answer preview: {final_answer[:100]}...")
                
                # Log full answer
                self.log_detailed("FINAL_ANSWER", {
                    "full_answer": final_answer,
                    "provider": llm_result.get('provider'),
                    "method": llm_result.get('method'),
                    "word_count": len(final_answer.split()),
                    "has_citation": any(word in final_answer for word in ['Điều', 'Khoản', 'Căn cứ']),
                    "has_greeting": final_answer.startswith('Chào'),
                    "has_disclaimer": 'thông tin tham khảo' in final_answer.lower()
                }, "Final answer analysis")
                
                # Update conversation
                self.unified.conversation.add_interaction(user_id, query, final_answer, "rag")
                
            else:
                print(f"   ❌ LLM failed: {llm_result.get('error', 'Unknown error')}")
                self.log_detailed("LLM_FAILED", llm_result, "LLM response failed")
            
        except Exception as e:
            print(f"   ❌ LLM exception: {e}")
            self.log_detailed("LLM_ERROR", {"error": str(e)}, "LLM response error")
        
        self.log_detailed("SCENARIO_END", {
            "scenario": scenario_name,
            "completed": True,
            "timestamp": datetime.now().isoformat()
        }, f"Completed scenario: {scenario_name}")
    
    async def test_multiturn_conversation(self):
        """Test multi-turn conversation với detailed tracking"""
        print(f"\n🔄 Multi-turn Conversation Test")
        user_id = "test_multiturn"
        
        conversations = [
            ("Tôi muốn làm hộ chiếu cho con", "Turn 1 - Context Setup"),
            ("Con tôi 10 tuổi", "Turn 2 - Age Information"),
            ("Ở Đà Nẵng làm ở đâu?", "Turn 3 - Location Query"),
            ("Lệ phí bao nhiêu?", "Turn 4 - Cost Query")
        ]
        
        self.log_detailed("MULTITURN_START", {
            "user_id": user_id,
            "total_turns": len(conversations),
            "conversation_plan": conversations
        }, "Starting multi-turn conversation test")
        
        for turn, (query, description) in enumerate(conversations, 1):
            print(f"   Turn {turn}: {query}")
            
            # Log turn start
            self.log_detailed(f"TURN_{turn}_START", {
                "turn": turn,
                "query": query,
                "description": description
            }, f"Starting turn {turn}")
            
            # Test the turn
            await self.test_scenario(query, user_id, f"Multiturn Turn {turn}")
            
            # Log conversation state after turn
            conversation_state = self.unified.conversation.get_conversation_context(user_id)
            self.log_detailed(f"TURN_{turn}_STATE", conversation_state, f"Conversation state after turn {turn}")
        
        # Final conversation analysis
        final_state = self.unified.conversation.get_conversation_context(user_id)
        self.log_detailed("MULTITURN_FINAL_ANALYSIS", {
            "total_interactions": final_state.get('query_count', 0),
            "accumulated_entities": final_state.get('entities', {}),
            "topic_thread": final_state.get('topic_thread'),
            "conversation_summary": final_state.get('conversation_summary', ''),
            "memory_working": len(final_state.get('recent_queries', [])) > 0
        }, "Multi-turn conversation final analysis")
        
        print(f"   ✅ Multi-turn test completed")
    
    async def test_single_query(self, query: str):
        """Test single query với detailed logging"""
        print(f"\n🔍 Single Query Test: '{query}'")
        await self.test_scenario(query, "single_test", "Single Query Test")

async def main():
    """Main debug function"""
    debugger = DetailedRAGDebugger()
    
    if len(sys.argv) > 1:
        # Test single query
        query = ' '.join(sys.argv[1:])
        await debugger.test_single_query(query)
    else:
        # Test all scenarios
        await debugger.test_comprehensive_scenarios()
    
    print(f"\n📄 Check detailed logs: {debugger.log_file}")

if __name__ == "__main__":
    asyncio.run(main())