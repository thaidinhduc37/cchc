# app/services/debug_vector_search.py
"""
🔍 SIMPLE VECTOR SEARCH DEBUG
🎯 Tìm vấn đề vector search - ngắn gọn
📋 Chỉ log vector search results
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
import re

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from app.services.vector_rag.core.vector_store import VectorSearcher

class SimpleVectorDebugger:
    """Simple vector search debugger"""
    
    def __init__(self):
        self.vector_searcher = None
        
        # Test queries
        self.test_queries = [
            "Điều 1 nói về gì?",
            "Điều 5 quy định gì?", 
            "Điều 14 là điều gì?",
            "Điều 21 về vấn đề gì?",
            "Điều 40 quy định thế nào?",
            "Thủ tục làm hộ chiếu cần giấy tờ gì?",
            "Ai được cấp hộ chiếu ngoại giao?",
            "Tạm hoãn xuất cảnh trong trường hợp nào?"
        ]
        
        # Expected law_units
        self.expected_law_units = {
            "Điều 1 nói về gì?": "1",
            "Điều 5 quy định gì?": "5",
            "Điều 14 là điều gì?": "14",
            "Điều 21 về vấn đề gì?": "21",
            "Điều 40 quy định thế nào?": "40",
            "Thủ tục làm hộ chiếu cần giấy tờ gì?": "15",
            "Ai được cấp hộ chiếu ngoại giao?": "8",
            "Tạm hoãn xuất cảnh trong trường hợp nào?": "36"
        }
    
    def log(self, message):
        """Simple log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    async def debug_vector_search(self):
        """Debug vector search only"""
        self.log("🔍 SIMPLE VECTOR SEARCH DEBUG")
        self.log("=" * 50)
        
        # Initialize
        self.vector_searcher = VectorSearcher()
        init_result = await self.vector_searcher.initialize()
        
        if not init_result.get('success'):
            self.log(f"❌ Init failed: {init_result}")
            return
        
        self.log(f"✅ Initialized: {init_result['stats']['documents']} documents")
        
        # Test each query
        correct_count = 0
        
        for query in self.test_queries:
            self.log(f"\n🔍 Query: '{query}'")
            expected_law_unit = self.expected_law_units.get(query, "unknown")
            self.log(f"   Expected law_unit: {expected_law_unit}")
            
            # DETAILED SEARCH ANALYSIS
            self.log("   🔍 SEARCH PROCESS:")
            
            # Step 1: Check if target article exists in vector store
            target_chunks = await self._find_target_chunks(expected_law_unit)
            self.log(f"   1️⃣ Target chunks in vector store: {len(target_chunks)}")
            if target_chunks:
                for i, chunk in enumerate(target_chunks[:3], 1):
                    law_unit = chunk['metadata'].get('law_unit', 'unknown')
                    content_preview = chunk['content'][:80].replace('\n', ' ')
                    self.log(f"       [{i}] law_unit: {law_unit} | Content: {content_preview}...")
            
            # Step 2: Actual search
            self.log("   2️⃣ Vector search:")
            results = await self.vector_searcher.search(query, k=5)
            
            if not results:
                self.log("       ❌ No results from vector search")
                continue
            
            # Step 3: Search method detection
            search_method = "unknown"
            if hasattr(self.vector_searcher, 'stats'):
                search_method = "detected via stats"
            
            self.log(f"       Search method: {search_method}")
            self.log(f"       Found {len(results)} results")
            
            # Step 4: Detailed result analysis
            self.log("   3️⃣ Result analysis:")
            found_expected = False
            target_in_results = False
            
            for i, result in enumerate(results, 1):
                content = result.get('content', '')
                score = result.get('score', 0)
                metadata = result.get('metadata', {})
                
                # Extract law_unit and article from content
                law_unit = metadata.get('law_unit', 'unknown')
                article_match = re.search(r'Điều\s+(\d+)', content)
                article_in_content = article_match.group(1) if article_match else 'unknown'
                
                # Check if this is expected
                is_expected = (law_unit == expected_law_unit or 
                             law_unit.startswith(expected_law_unit + ".") or
                             article_in_content == expected_law_unit)
                
                if is_expected:
                    target_in_results = True
                    if i == 1:
                        found_expected = True
                
                status = "⭐ EXPECTED" if is_expected else ""
                self.log(f"       [{i}] Score: {score:.4f} | law_unit: {law_unit} | article: {article_in_content} {status}")
            
            # Step 5: Analysis summary
            self.log("   4️⃣ Analysis:")
            if not target_chunks:
                self.log("       ❌ ISSUE: Target article not in vector store")
            elif not target_in_results:
                self.log("       ❌ ISSUE: Target exists but not found by search")
            elif not found_expected:
                self.log("       ❌ ISSUE: Target found but not ranked #1")
            else:
                self.log("       ✅ Working correctly")
            
            if found_expected:
                correct_count += 1
        
        # Summary
        total = len(self.test_queries)
        accuracy = (correct_count / total) * 100
        
        self.log(f"\n📊 SUMMARY:")
        self.log(f"   Correct: {correct_count}/{total}")
        self.log(f"   Accuracy: {accuracy:.1f}%")
        
    
    async def _find_target_chunks(self, target_law_unit: str):
        """Find chunks with target law_unit in vector store"""
        try:
            # Access vector searcher's data
            if not hasattr(self.vector_searcher, 'metadatas'):
                return []
            
            target_chunks = []
            for i, metadata in enumerate(self.vector_searcher.metadatas):
                law_unit = metadata.get('law_unit', '')
                if law_unit == target_law_unit or law_unit.startswith(target_law_unit + "."):
                    target_chunks.append({
                        'index': i,
                        'metadata': metadata,
                        'content': self.vector_searcher.documents[i] if i < len(self.vector_searcher.documents) else ''
                    })
            
            return target_chunks
        except Exception as e:
            self.log(f"       Error finding target chunks: {e}")
            return []

async def main():
    """Main debug function"""
    debugger = SimpleVectorDebugger()
    await debugger.debug_vector_search()

if __name__ == "__main__":
    asyncio.run(main())