# services/debug_rag_pipeline.py - CHECK ĐIỀU LUẬT & DEBUG
"""
🧪 RAG PIPELINE DEBUG - CHECK ĐIỀU LUẬT
🎯 Kiểm tra có đủ 52 điều luật không
📄 Debug tìm kiếm chính xác
"""
import sys
import os
import asyncio
from pathlib import Path

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent))

# Disable framework logs but keep our debug
import logging
logging.getLogger('sentence_transformers').setLevel(logging.CRITICAL)
logging.getLogger('transformers').setLevel(logging.CRITICAL)
logging.getLogger('torch').setLevel(logging.CRITICAL)

async def check_legal_articles():
    """🔍 Check xem có đủ 52 điều luật không"""
    
    print("🔍 CHECKING LEGAL ARTICLES IN VECTOR STORE")
    print("=" * 80)
    
    try:
        from services.vector_rag.vector_store import VectorSearcher
        from services.vector_rag.rag_config import config
        
        # Initialize searcher
        searcher = VectorSearcher()
        init_result = await searcher.initialize()
        
        if not init_result['success']:
            print(f"❌ Vector store initialization failed: {init_result.get('message')}")
            print(f"🔧 Try running: python build_vector.py --build --domain xuatnhapcanh")
            return {}, set()
        
        print(f"📁 Vector store path: {config.vector_store_path}")
        print(f"📁 Documents path: {config.documents_path}")
        
        print(f"📊 TOTAL DOCUMENTS: {len(searcher.documents)}")
        print(f"📊 TOTAL METADATA: {len(searcher.metadatas)}")
        
        if len(searcher.documents) == 0:
            print("❌ No documents found in vector store!")
            print("🔧 Vector store files:")
            
            # Check if files exist
            storage_path = config.vector_store_path
            files_to_check = ['documents.pkl', 'metadata.pkl', 'faiss_index.bin']
            
            for filename in files_to_check:
                filepath = os.path.join(storage_path, filename)
                exists = os.path.exists(filepath)
                size = os.path.getsize(filepath) if exists else 0
                print(f"   {filename}: {'✅' if exists else '❌'} ({size} bytes)")
            
            if not any(os.path.exists(os.path.join(storage_path, f)) for f in files_to_check):
                print("\n🔧 SOLUTION: Build vector database first:")
                print("   python build_vector.py --build --domain xuatnhapcanh")
            
            return {}, set()
        
        # Check for articles in documents
        articles_found = {}
        legal_doc_count = 0
        qa_doc_count = 0
        
        print(f"\n🔍 SCANNING DOCUMENTS FOR ARTICLES...")
        
        for i, (doc, meta) in enumerate(zip(searcher.documents, searcher.metadatas)):
            content_type = meta.get('content_type', 'unknown')
            
            if content_type == 'legal_document':
                legal_doc_count += 1
            elif content_type == 'qa_entry':
                qa_doc_count += 1
            
            # Search for articles in content
            import re
            article_matches = re.findall(r'Điều\s+(\d+)', doc, re.IGNORECASE)
            
            for article_num in article_matches:
                article_num = int(article_num)
                if article_num not in articles_found:
                    articles_found[article_num] = []
                articles_found[article_num].append({
                    'doc_index': i,
                    'content_type': content_type,
                    'preview': doc[:100] + "..." if len(doc) > 100 else doc,
                    'metadata': meta
                })
        
        print(f"\n📊 DOCUMENT BREAKDOWN:")
        print(f"  Legal documents: {legal_doc_count}")
        print(f"  Q&A entries: {qa_doc_count}")
        print(f"  Other: {len(searcher.documents) - legal_doc_count - qa_doc_count}")
        
        print(f"\n📊 ARTICLES FOUND:")
        found_articles = sorted(articles_found.keys())
        print(f"  Total unique articles: {len(found_articles)}")
        print(f"  Article range: {min(found_articles) if found_articles else 'None'} - {max(found_articles) if found_articles else 'None'}")
        print(f"  Articles: {found_articles}")
        
        # Check for missing articles (1-52)
        expected_articles = set(range(1, 53))  # 1 to 52
        missing_articles = expected_articles - set(found_articles)
        
        print(f"\n❌ MISSING ARTICLES ({len(missing_articles)}):")
        if missing_articles:
            missing_sorted = sorted(missing_articles)
            print(f"  {missing_sorted}")
        else:
            print(f"  ✅ All articles 1-52 found!")
        
        # Show details for important articles
        important_articles = [15, 22, 24]  # Articles mentioned in test queries
        
        print(f"\n🎯 IMPORTANT ARTICLES DETAILS:")
        for article_num in important_articles:
            if article_num in articles_found:
                print(f"\n  📄 ĐIỀU {article_num}:")
                for doc_info in articles_found[article_num]:
                    print(f"    Doc {doc_info['doc_index']}: {doc_info['content_type']}")
                    print(f"    Preview: {doc_info['preview']}")
                    if doc_info['metadata']:
                        law_unit = doc_info['metadata'].get('law_unit', 'N/A')
                        print(f"    Law unit: {law_unit}")
            else:
                print(f"\n  ❌ ĐIỀU {article_num}: NOT FOUND")
        
        return articles_found, missing_articles
        
    except Exception as e:
        print(f"❌ CHECK FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {}, set()

async def test_specific_article_search():
    """🔍 Test tìm kiếm điều cụ thể"""
    
    print(f"\n" + "="*80)
    print("🔍 TESTING SPECIFIC ARTICLE SEARCH")
    print("="*80)
    
    test_queries = [
        "Điều 15",
        "Khoản 2 điều 15", 
        "Điều 22",
        "Điều 24"
    ]
    
    try:
        from services.vector_rag.vector_store import VectorSearcher
        
        searcher = VectorSearcher()
        await searcher.initialize()
        
        for query in test_queries:
            print(f"\n🔍 QUERY: '{query}'")
            print("-" * 50)
            
            # Test vector search
            results = await searcher.search(query, k=5)
            
            print(f"📊 Results: {len(results)}")
            
            for i, result in enumerate(results[:3]):  # Show top 3
                score = result.get('score', 0)
                content = result.get('content', '')
                metadata = result.get('metadata', {})
                search_type = result.get('search_type', 'unknown')
                query_type = result.get('query_type', 'unknown')
                
                print(f"\n  Result {i+1}:")
                print(f"    Score: {score:.3f}")
                print(f"    Search type: {search_type}")
                print(f"    Query type: {query_type}")
                print(f"    Content type: {metadata.get('content_type', 'unknown')}")
                print(f"    Law unit: {metadata.get('law_unit', 'N/A')}")
                
                # Check if contains expected article
                expected_article = query.lower().replace('khoản', '').replace('điểm', '').strip()
                if expected_article in content.lower():
                    print(f"    ✅ Contains expected: {expected_article}")
                else:
                    print(f"    ❌ Missing expected: {expected_article}")
                
                # Show preview
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"    Preview: {preview}")
                
    except Exception as e:
        print(f"❌ SEARCH TEST FAILED: {e}")

async def test_full_pipeline():
    """🔍 Test full pipeline với debug"""
    
    print(f"\n" + "="*80)
    print("🔍 TESTING FULL PIPELINE")
    print("="*80)
    
    test_cases = [
        {
            'query': 'Khoản 2 điều 15 Luật xuất nhập cảnh nói về cái gì',
            'expected_article': 'Điều 15',
            'expected_paragraph': 'Khoản 2'
        },
        {
            'query': 'Trẻ em tự đi nước ngoài như thế nào',
            'expected_article': 'Điều 22',  # Usually about children travel
            'expected_paragraph': None
        },
        {
            'query': 'Thủ tục cấp hộ chiếu thế nào',
            'expected_article': None,  # Should find Q&A
            'expected_paragraph': None
        }
    ]
    
    try:
        from services.vector_rag.rag_engine import RAGEngine
        
        rag = RAGEngine()
        await rag.initialize()
        
        for i, test_case in enumerate(test_cases, 1):
            query = test_case['query']
            expected_article = test_case['expected_article']
            
            print(f"\n🧪 TEST CASE {i}: {query}")
            print("-" * 60)
            
            # Mock unified data
            unified_data = {
                'original_query': query,
                'intent_analysis': {
                    'intent_type': 'legal_precise' if 'điều' in query.lower() else 'procedure',
                    'confidence': 0.9,
                    'needs_conclusion': False
                },
                'resolution': {
                    'context_used': False
                }
            }
            
            # Test RAG
            result = await rag.query(query, unified_data=unified_data)
            
            print(f"✅ Success: {result.get('success', False)}")
            
            if result.get('success'):
                answer = result.get('answer', '')
                
                # Check if answer contains expected article
                if expected_article:
                    if expected_article.lower() in answer.lower():
                        print(f"✅ Contains expected: {expected_article}")
                    else:
                        print(f"❌ Missing expected: {expected_article}")
                        print(f"   Looking for: {expected_article}")
                        print(f"   In answer: {answer[:100]}...")
                
                # Show answer preview
                print(f"\n📄 ANSWER PREVIEW:")
                print(f"{answer[:300]}...")
                
                # Show metadata
                metadata = result.get('metadata', {})
                print(f"\n📊 METADATA:")
                print(f"  Context sources: {metadata.get('context_sources', 0)}")
                print(f"  Query intent: {metadata.get('query_intent', 'unknown')}")
                
            else:
                print(f"❌ Failed: {result.get('answer', 'No answer')}")
                
    except Exception as e:
        print(f"❌ PIPELINE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """🚀 Main debug function"""
    
    print("🧪 RAG PIPELINE DEBUG & ARTICLE CHECK")
    print("="*80)
    
    # Step 1: Check articles
    articles_found, missing_articles = await check_legal_articles()
    
    # Step 2: Test specific searches
    await test_specific_article_search()
    
    # Step 3: Test full pipeline
    await test_full_pipeline()
    
    # Summary
    print(f"\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    print(f"  Total articles found: {len(articles_found)}")
    print(f"  Missing articles: {len(missing_articles)}")
    
    if missing_articles:
        print(f"  Missing: {sorted(missing_articles)}")
        print(f"  🔧 RECOMMENDATION: Check document processing and indexing")
    else:
        print(f"  ✅ All articles 1-52 indexed")
        print(f"  🔧 RECOMMENDATION: Check vector search and ranking logic")

if __name__ == "__main__":
    asyncio.run(main())