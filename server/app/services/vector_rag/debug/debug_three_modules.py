# app/services/debug_three_modules.py
"""
🔍 DEBUG 3 MODULE VỚI LUẬT 49/2019/QH14
🎯 Mục tiêu: Tìm nguyên nhân accuracy chỉ 25%
📋 Test với file thực tế: server/dataset/xuatnhapcanh/documents/47-2019-QH14.docx
🔧 Kiểm tra từng bước: Document → Embeddings → Vector Search
"""

import sys
import os
import asyncio
import json
import pickle
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import numpy as np

# Add parent to path
current_dir = Path(__file__).parent
sys.path.append(str(current_dir.parent.parent.parent.parent))

from app.services.vector_rag.core.document_processor import DocumentProcessor, Document
from app.services.vector_rag.core.embeddings import VietnameseEmbeddingModel
from app.services.vector_rag.core.vector_store import VectorStore

class ThreeModuleDebugger:
    """Debug 3 module với Luật 49/2019/QH14"""
    
    def __init__(self):
        # Setup log file
        self.log_file = Path("app/services/debug") / f"three_modules_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.log_file.parent.mkdir(exist_ok=True)
        
        # CORRECT PATH: server/dataset/xuatnhapcanh/documents/47-2019-QH14.docx
        # Từ app/services/debug_three_modules.py → server/dataset/
        self.law_file_path = Path("dataset/xuatnhapcanh/documents/47-2019-QH14.docx")
        self.documents_path = Path("dataset/xuatnhapcanh/documents")
        
        # Test queries từ comprehensive debug
        self.test_queries = [
            "Điều 1 nói về gì?",
            "Điều 5 quy định gì?", 
            "Điều 14 là điều gì?",
            "Điều 21 về vấn đề gì?",
            "Điều 40 quy định thế nào?",
            "Ai được cấp hộ chiếu ngoại giao?",
            "Thủ tục làm hộ chiếu cần giấy tờ gì?",
            "Luật này có hiệu lực từ khi nào?"
        ]
        
        # Expected results cho accuracy checking
        self.expected_results = {
            "Điều 1 nói về gì?": "Phạm vi điều chỉnh",
            "Điều 5 quy định gì?": "Quyền và nghĩa vụ của công dân Việt Nam",
            "Điều 14 là điều gì?": "Đối tượng được cấp hộ chiếu phổ thông",
            "Điều 21 về vấn đề gì?": "Từ chối cấp hộ chiếu phổ thông",
            "Điều 40 quy định thế nào?": "Yêu cầu xây dựng và quản lý Cơ sở dữ liệu quốc gia"
        }
        
        # Stats tracking
        self.debug_stats = {
            'document_processor': {},
            'embeddings': {},
            'vector_store': {},
            'overall_accuracy': 0.0
        }
    
    def log(self, message):
        """Log to both console and file"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")
    
    async def debug_all_modules(self):
        """Debug tất cả 3 module với Luật 49/2019/QH14"""
        self.log("🔍 DEBUG 3 MODULE VỚI LUẬT 49/2019/QH14")
        self.log("=" * 80)
        self.log(f"📁 Law file: {self.law_file_path}")
        self.log(f"📁 Documents path: {self.documents_path}")
        
        # Check file existence
        if not self.law_file_path.exists():
            self.log(f"❌ File không tồn tại: {self.law_file_path}")
            return
        
        # STEP 1: Debug Document Processor
        await self._debug_document_processor()
        
        # STEP 2: Debug Embeddings
        await self._debug_embeddings()
        
        # STEP 3: Debug Vector Store
        await self._debug_vector_store()
        
        # STEP 4: End-to-end accuracy test
        await self._test_end_to_end_accuracy()
        
        # STEP 5: Summary và recommendations
        self._provide_debug_summary()
    
    async def _debug_document_processor(self):
        """Debug Document Processor với file thực tế"""
        self.log(f"\n🔍 DEBUG 1: DOCUMENT PROCESSOR")
        self.log("=" * 60)
        
        try:
            processor = DocumentProcessor()
            
            # Test single file processing
            self.log(f"📄 Processing: {self.law_file_path.name}")
            documents = processor.process_file(str(self.law_file_path))
            
            if not documents:
                self.log("❌ Document processor returned NO documents")
                self.debug_stats['document_processor']['status'] = 'FAILED'
                return
            
            self.log(f"✅ Processed {len(documents)} chunks")
            
            # Analyze document structure
            article_analysis = self._analyze_document_structure(documents)
            self.debug_stats['document_processor'] = {
                'status': 'SUCCESS',
                'total_chunks': len(documents),
                'analysis': article_analysis
            }
            
            # Sample document analysis
            self.log(f"\n📊 DOCUMENT ANALYSIS:")
            self.log(f"   Total chunks: {len(documents)}")
            self.log(f"   Articles found: {article_analysis['articles_found']}")
            self.log(f"   Has Điều 1: {article_analysis['has_dieu_1']}")
            self.log(f"   Has Điều 5: {article_analysis['has_dieu_5']}")
            self.log(f"   Has Điều 14: {article_analysis['has_dieu_14']}")
            self.log(f"   Has Điều 21: {article_analysis['has_dieu_21']}")
            self.log(f"   Has Điều 40: {article_analysis['has_dieu_40']}")
            
            # Show sample chunks
            self.log(f"\n📝 SAMPLE CHUNKS:")
            for i, doc in enumerate(documents[:5]):
                content_preview = doc.content[:150].replace('\n', ' ')
                metadata = doc.metadata
                law_unit = metadata.get('law_unit', 'Unknown')
                
                self.log(f"   [{i+1}] Law Unit: {law_unit}")
                self.log(f"       Content: {content_preview}...")
                self.log(f"       Metadata: {metadata.get('content_type', 'Unknown')}")
            
            # Test specific articles
            self._test_specific_articles(documents)
            
        except Exception as e:
            self.log(f"❌ Document processor failed: {e}")
            self.debug_stats['document_processor']['status'] = 'ERROR'
            import traceback
            self.log(f"   Traceback: {traceback.format_exc()}")
    
    def _analyze_document_structure(self, documents: List[Document]) -> Dict:
        """Analyze document structure for articles"""
        analysis = {
            'total_chunks': len(documents),
            'articles_found': [],
            'has_dieu_1': False,
            'has_dieu_5': False,
            'has_dieu_14': False,
            'has_dieu_21': False,
            'has_dieu_40': False,
            'content_types': {}
        }
        
        for doc in documents:
            content = doc.content
            metadata = doc.metadata
            
            # Count content types
            content_type = metadata.get('content_type', 'unknown')
            analysis['content_types'][content_type] = analysis['content_types'].get(content_type, 0) + 1
            
            # Check for specific articles
            if 'Điều 1' in content:
                analysis['has_dieu_1'] = True
            if 'Điều 5' in content:
                analysis['has_dieu_5'] = True
            if 'Điều 14' in content:
                analysis['has_dieu_14'] = True
            if 'Điều 21' in content:
                analysis['has_dieu_21'] = True
            if 'Điều 40' in content:
                analysis['has_dieu_40'] = True
            
            # Extract article numbers
            article_matches = re.findall(r'Điều\s+(\d+)', content)
            analysis['articles_found'].extend(article_matches)
        
        # Remove duplicates and sort
        analysis['articles_found'] = sorted(list(set(analysis['articles_found'])), key=int)
        
        return analysis
    
    def _test_specific_articles(self, documents: List[Document]):
        """Test specific articles mentioned in queries"""
        self.log(f"\n🔍 SPECIFIC ARTICLE TESTING:")
        
        target_articles = ['1', '5', '14', '21', '40']
        
        for article_num in target_articles:
            found_docs = []
            for doc in documents:
                if f'Điều {article_num}' in doc.content:
                    found_docs.append(doc)
            
            if found_docs:
                self.log(f"   ✅ Điều {article_num}: Found {len(found_docs)} chunk(s)")
                # Show first match
                first_doc = found_docs[0]
                preview = first_doc.content[:200].replace('\n', ' ')
                self.log(f"       Preview: {preview}...")
            else:
                self.log(f"   ❌ Điều {article_num}: NOT FOUND")
    
    async def _debug_embeddings(self):
        """Debug Embeddings với sample text"""
        self.log(f"\n🔍 DEBUG 2: EMBEDDINGS")
        self.log("=" * 60)
        
        try:
            embedding_model = VietnameseEmbeddingModel()
            
            # Test embedding generation
            sample_texts = [
                "Điều 1. Phạm vi điều chỉnh",
                "Điều 5. Quyền và nghĩa vụ của công dân Việt Nam", 
                "Điều 14. Đối tượng được cấp hộ chiếu phổ thông",
                "Điều 21. Từ chối cấp hộ chiếu phổ thông",
                "Điều 40. Yêu cầu xây dựng và quản lý Cơ sở dữ liệu quốc gia"
            ]
            
            self.log(f"📊 Testing embedding generation:")
            self.log(f"   Sample texts: {len(sample_texts)}")
            
            # Generate embeddings
            embeddings = embedding_model.embed_documents(sample_texts)
            
            if not embeddings:
                self.log("❌ Embedding generation failed")
                self.debug_stats['embeddings']['status'] = 'FAILED'
                return
            
            self.log(f"✅ Generated {len(embeddings)} embeddings")
            self.log(f"   Dimension: {len(embeddings[0])}")
            
            # Test query embedding
            test_query = "Điều 1 nói về gì?"
            query_embedding = embedding_model.embed_query(test_query)
            
            if not query_embedding:
                self.log("❌ Query embedding failed")
                self.debug_stats['embeddings']['status'] = 'FAILED'
                return
            
            self.log(f"✅ Query embedding generated: {len(query_embedding)} dimensions")
            
            # Test similarity calculation
            self.log(f"\n🔍 SIMILARITY TESTING:")
            for i, text in enumerate(sample_texts):
                similarity = embedding_model.calculate_similarity(query_embedding, embeddings[i])
                self.log(f"   Query vs Text {i+1}: {similarity:.4f}")
                self.log(f"       Text: {text}")
            
            # Test with different queries
            self.log(f"\n🔍 MULTIPLE QUERY TESTING:")
            test_queries = [
                "Điều 1 nói về gì?",
                "Điều 5 quy định gì?",
                "Điều 14 là điều gì?"
            ]
            
            query_embeddings = embedding_model.embed_documents(test_queries)
            
            for i, query in enumerate(test_queries):
                self.log(f"   Query: {query}")
                best_match_idx = -1
                best_similarity = -1
                
                for j, embedding in enumerate(embeddings):
                    similarity = embedding_model.calculate_similarity(query_embeddings[i], embedding)
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match_idx = j
                
                if best_match_idx >= 0:
                    self.log(f"       Best match: Text {best_match_idx + 1} (similarity: {best_similarity:.4f})")
                    self.log(f"       Content: {sample_texts[best_match_idx]}")
                else:
                    self.log(f"       No good match found")
            
            # Get embedding stats
            stats = embedding_model.get_stats()
            self.debug_stats['embeddings'] = {
                'status': 'SUCCESS',
                'model_name': stats['model_info']['model_name'],
                'dimension': stats['model_info']['dimension'],
                'performance': stats['performance']
            }
            
        except Exception as e:
            self.log(f"❌ Embeddings failed: {e}")
            self.debug_stats['embeddings']['status'] = 'ERROR'
            import traceback
            self.log(f"   Traceback: {traceback.format_exc()}")
    
    async def _debug_vector_store(self):
        """Debug Vector Store với actual data"""
        self.log(f"\n🔍 DEBUG 3: VECTOR STORE")
        self.log("=" * 60)
        
        try:
            # Initialize vector store
            vector_store = VectorStore()
            
            # Build from documents
            self.log(f"🔨 Building vector store from {self.documents_path}")
            build_result = await vector_store.build_if_needed(str(self.documents_path), force_rebuild=True)
            
            if not build_result['success']:
                self.log(f"❌ Vector store build failed: {build_result['message']}")
                self.debug_stats['vector_store']['status'] = 'BUILD_FAILED'
                return
            
            self.log(f"✅ Vector store built successfully")
            self.log(f"   Stats: {build_result.get('stats', {})}")
            
            # Initialize for search
            init_result = await vector_store.initialize()
            if not init_result['success']:
                self.log(f"❌ Vector store init failed: {init_result['message']}")
                self.debug_stats['vector_store']['status'] = 'INIT_FAILED'
                return
            
            self.log(f"✅ Vector store initialized")
            
            # Test search functionality
            self.log(f"\n🔍 SEARCH TESTING:")
            search_results = {}
            
            for query in self.test_queries[:5]:  # Test first 5 queries
                self.log(f"   Query: '{query}'")
                
                results = await vector_store.search(query, k=5)
                search_results[query] = results
                
                if results:
                    self.log(f"       Found {len(results)} results")
                    # Show top result
                    top_result = results[0]
                    score = top_result.get('score', 0)
                    content_preview = top_result.get('content', '')[:100].replace('\n', ' ')
                    
                    self.log(f"       Top result: Score={score:.4f}")
                    self.log(f"       Content: {content_preview}...")
                    
                    # Check if result matches expected
                    if query in self.expected_results:
                        expected = self.expected_results[query]
                        is_correct = expected.lower() in content_preview.lower()
                        self.log(f"       Expected: {expected}")
                        self.log(f"       Correct: {'✅' if is_correct else '❌'}")
                else:
                    self.log(f"       ❌ No results found")
            
            # Get vector store stats
            health_status = vector_store.get_health_status()
            self.debug_stats['vector_store'] = {
                'status': 'SUCCESS',
                'health_status': health_status,
                'search_results': search_results
            }
            
        except Exception as e:
            self.log(f"❌ Vector store failed: {e}")
            self.debug_stats['vector_store']['status'] = 'ERROR'
            import traceback
            self.log(f"   Traceback: {traceback.format_exc()}")
    
    async def _test_end_to_end_accuracy(self):
        """Test end-to-end accuracy"""
        self.log(f"\n🔍 END-TO-END ACCURACY TEST")
        self.log("=" * 60)
        
        try:
            # Re-initialize vector store for clean test
            vector_store = VectorStore()
            init_result = await vector_store.initialize()
            
            if not init_result['success']:
                self.log(f"❌ Cannot initialize vector store for accuracy test")
                return
            
            correct_count = 0
            total_count = len(self.test_queries)
            
            for query in self.test_queries:
                self.log(f"🧪 Testing: '{query}'")
                
                results = await vector_store.search(query, k=3)
                
                if results:
                    top_result = results[0]
                    content = top_result.get('content', '')
                    score = top_result.get('score', 0)
                    
                    # Check accuracy
                    is_correct = False
                    if query in self.expected_results:
                        expected = self.expected_results[query]
                        is_correct = expected.lower() in content.lower()
                    
                    status = "✅ CORRECT" if is_correct else "❌ INCORRECT"
                    self.log(f"   Result: {status} (Score: {score:.4f})")
                    
                    if is_correct:
                        correct_count += 1
                else:
                    self.log(f"   ❌ NO RESULTS")
            
            accuracy = (correct_count / total_count) * 100
            self.debug_stats['overall_accuracy'] = accuracy
            
            self.log(f"\n📊 ACCURACY SUMMARY:")
            self.log(f"   Correct: {correct_count}/{total_count}")
            self.log(f"   Accuracy: {accuracy:.1f}%")
            
        except Exception as e:
            self.log(f"❌ End-to-end test failed: {e}")
            import traceback
            self.log(f"   Traceback: {traceback.format_exc()}")
    
    def _provide_debug_summary(self):
        """Provide debug summary and recommendations"""
        self.log(f"\n🔍 DEBUG SUMMARY & RECOMMENDATIONS")
        self.log("=" * 80)
        
        # Module status summary
        doc_status = self.debug_stats.get('document_processor', {}).get('status', 'NOT_TESTED')
        emb_status = self.debug_stats.get('embeddings', {}).get('status', 'NOT_TESTED')
        vec_status = self.debug_stats.get('vector_store', {}).get('status', 'NOT_TESTED')
        accuracy = self.debug_stats.get('overall_accuracy', 0)
        
        self.log(f"📊 MODULE STATUS:")
        self.log(f"   Document Processor: {doc_status}")
        self.log(f"   Embeddings: {emb_status}")
        self.log(f"   Vector Store: {vec_status}")
        self.log(f"   Overall Accuracy: {accuracy:.1f}%")
        
        # Identify problems
        self.log(f"\n🔍 PROBLEMS IDENTIFIED:")
        
        if doc_status != 'SUCCESS':
            self.log(f"   ❌ Document Processor: {doc_status}")
            self.log(f"       → Check file processing logic")
            self.log(f"       → Verify regex patterns")
            self.log(f"       → Check chunking strategy")
        
        if emb_status != 'SUCCESS':
            self.log(f"   ❌ Embeddings: {emb_status}")
            self.log(f"       → Check model loading")
            self.log(f"       → Verify text preprocessing")
            self.log(f"       → Test similarity calculation")
        
        if vec_status != 'SUCCESS':
            self.log(f"   ❌ Vector Store: {vec_status}")
            self.log(f"       → Check FAISS index building")
            self.log(f"       → Verify search logic")
            self.log(f"       → Test indexing process")
        
        if accuracy < 50:
            self.log(f"   ❌ Low Accuracy: {accuracy:.1f}%")
            self.log(f"       → Review entire pipeline")
            self.log(f"       → Check document-query matching")
            self.log(f"       → Verify embedding quality")
        
        # Recommendations
        self.log(f"\n💡 RECOMMENDATIONS:")
        
        if accuracy < 25:
            self.log(f"   🚨 CRITICAL: Complete pipeline review needed")
            self.log(f"       1. Verify source document quality")
            self.log(f"       2. Simplify document processing")
            self.log(f"       3. Test with minimal example")
            self.log(f"       4. Check each step individually")
        elif accuracy < 50:
            self.log(f"   ⚠️ MODERATE: Focus on specific issues")
            self.log(f"       1. Improve document chunking")
            self.log(f"       2. Optimize embedding model")
            self.log(f"       3. Fine-tune search parameters")
        else:
            self.log(f"   ✅ GOOD: Minor optimizations needed")
            self.log(f"       1. Fine-tune scoring")
            self.log(f"       2. Optimize performance")
            self.log(f"       3. Add more test cases")
        
        self.log(f"\n📄 Full debug log: {self.log_file}")

async def main():
    """Main debug function"""
    debugger = ThreeModuleDebugger()
    
    print("🔍 Starting 3-Module Debug với Luật 49/2019/QH14...")
    print(f"📄 Log file: {debugger.log_file}")
    print(f"📁 Source file: {debugger.law_file_path}")
    print("🎯 Mục tiêu: Tìm nguyên nhân accuracy 25%")
    
    await debugger.debug_all_modules()

if __name__ == "__main__":
    asyncio.run(main())