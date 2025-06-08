# server/services/vector_rag/build_vector.py
"""
Build Vector Store Script - CẬP NHẬT: Tương thích với logic mới
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.vector_rag.rag_config import config, get_config_summary_enhanced
from services.vector_rag.document_processor import DocumentProcessor
from services.vector_rag.vector_store import VectorStore
from services.vector_rag.embeddings import VietnameseEmbeddingModel

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'build_vector_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

class VectorStoreBuilder:
    """CẬP NHẬT: Vector Store Builder với logic mới"""
    
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore()
        self.embedding_model = VietnameseEmbeddingModel()
        
        logger.info("🔧 VectorStoreBuilder initialized với logic mới")
        
        # CẬP NHẬT: Log model info
        stats = self.embedding_model.get_stats()
        logger.info(f"📊 Embedding Model: {stats['model_name']}")
        logger.info(f"   Dimension: {stats['dimension']}")
        logger.info(f"   E5 prefixes: {stats.get('use_e5_prefixes', False)}")
        logger.info(f"   Normalization: {stats.get('normalize_embeddings', False)}")
    
    async def build(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """CẬP NHẬT: Build vector store với enhanced processing"""
        try:
            start_time = datetime.now()
            logger.info("🚀 Starting vector store build với logic mới...")
            
            # Step 1: Check if rebuild needed
            if not force_rebuild:
                existing_stats = self.vector_store.get_stats()
                if existing_stats['total_documents'] > 0:
                    user_input = input(f"Vector store exists with {existing_stats['total_documents']} documents. Rebuild? (y/N): ")
                    if user_input.lower() != 'y':
                        logger.info("❌ Build cancelled by user")
                        return {'success': False, 'message': 'Cancelled by user'}
            
            # Step 2: Initialize vector store
            logger.info("🗑️ Clearing existing vector store...")
            await self.vector_store.initialize(force_rebuild=True)
            
            # Step 3: CẬP NHẬT - Process documents với legal chunking
            logger.info("📄 Processing documents với legal structure chunking...")
            documents = self.document_processor.process_directory()
            
            if not documents:
                logger.error("❌ No documents found")
                return {
                    'success': False,
                    'message': 'No documents found in directory',
                    'directory': config.documents_path
                }
            
            # CẬP NHẬT: Enhanced logging
            legal_chunks = sum(1 for d in documents if d.metadata.get('has_legal_structure', False))
            articles_found = sum(d.metadata.get('contains_articles', 0) for d in documents)
            
            logger.info(f"✅ Processed {len(documents)} document chunks")
            logger.info(f"   ⚖️ Legal structure chunks: {legal_chunks}")
            logger.info(f"   📜 Articles found: {articles_found}")
            
            # Step 4: Add documents to vector store
            logger.info("🧮 Adding documents to vector store...")
            success = await self.vector_store.add_documents(documents)
            
            if not success:
                logger.error("❌ Failed to add documents to vector store")
                return {
                    'success': False,
                    'message': 'Failed to add documents to vector store'
                }
            
            # Step 5: CẬP NHẬT - Enhanced final stats
            final_stats = self.vector_store.get_stats()
            embedding_stats = self.embedding_model.get_stats()
            build_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'message': f'Vector store built successfully in {build_time:.2f}s',
                'stats': {
                    'total_documents': final_stats['total_documents'],
                    'build_time_seconds': build_time,
                    'embedding_model': final_stats['embedding_model'],
                    'dimension': final_stats.get('dimension', 'unknown'),
                    'legal_chunks': legal_chunks,
                    'articles_found': articles_found,
                    'cache_size_mb': embedding_stats.get('cache_size_mb', 0),
                    'use_e5_prefixes': embedding_stats.get('use_e5_prefixes', False)
                }
            }
            
            logger.info("🎉 Vector store build completed successfully!")
            logger.info(f"   📊 Documents: {final_stats['total_documents']}")
            logger.info(f"   ⚖️ Legal chunks: {legal_chunks}")
            logger.info(f"   📜 Articles: {articles_found}")
            logger.info(f"   ⏱️ Time: {build_time:.2f}s")
            logger.info(f"   🧠 Model: {final_stats['embedding_model']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Build failed: {e}")
            return {
                'success': False,
                'message': f'Build failed: {str(e)}',
                'error': str(e)
            }
    
    async def test_embeddings(self, test_queries: list = None) -> Dict[str, Any]:
        """CẬP NHẬT: Test embeddings với E5-base"""
        if test_queries is None:
            test_queries = [
                "Điều kiện cấp hộ chiếu phổ thông",
                "Thủ tục làm thị thực du lịch", 
                "Lệ phí gia hạn tạm trú",
                "Điều 15 Luật xuất nhập cảnh",
                "Thành phần hồ sơ làm hộ chiếu"
            ]
        
        try:
            logger.info("🧪 Testing embeddings với queries mới...")
            
            # CẬP NHẬT: Use new test method
            result = self.embedding_model.test_embeddings(test_queries)
            
            if result['success']:
                logger.info(f"✅ Embedding test passed")
                logger.info(f"   📐 Dimension: {result['embedding_dimension']}")
                logger.info(f"   📊 Avg self-similarity: {result['average_self_similarity']}")
                logger.info(f"   🔧 Model features:")
                
                model_stats = result['model_stats']
                if model_stats.get('use_e5_prefixes'):
                    logger.info(f"      E5 query prefix: '{model_stats.get('query_prefix', 'None')}'")
                    logger.info(f"      E5 doc prefix: '{model_stats.get('doc_prefix', 'None')}'")
                
                logger.info(f"      Normalization: {model_stats.get('normalize_embeddings', False)}")
            else:
                logger.error(f"❌ Embedding test failed: {result.get('error', 'Unknown')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Embedding test failed: {e}")
            return {
                'success': False,
                'message': f'Test failed: {str(e)}',
                'error': str(e)
            }
    
    async def test_vector_search(self, test_queries: list = None) -> Dict[str, Any]:
        """CẬP NHẬT: Test vector search với entity reranking"""
        if test_queries is None:
            test_queries = [
                "hộ chiếu trẻ em",  # Should trigger entity reranking
                "Điều 10 luật xuất nhập cảnh",  # Legal specific
                "lệ phí làm thị thực"  # Procedure + entity
            ]
        
        try:
            logger.info("🔍 Testing vector search với entity reranking...")
            
            if self.vector_store.get_stats()['total_documents'] == 0:
                return {
                    'success': False,
                    'message': 'Vector store is empty, build first'
                }
            
            search_results = {}
            
            for query in test_queries:
                logger.info(f"   Testing: '{query}'")
                
                # Extract entities for testing
                entities = []
                if 'hộ chiếu' in query.lower():
                    entities.append('hộ chiếu')
                if 'trẻ em' in query.lower():
                    entities.append('trẻ em')
                if 'lệ phí' in query.lower():
                    entities.append('lệ phí')
                if 'thị thực' in query.lower():
                    entities.append('thị thực')
                
                # Test search với entity reranking
                results = await self.vector_store.search(
                    query, 
                    k=3, 
                    query_entities=entities
                )
                
                search_results[query] = {
                    'results_count': len(results),
                    'entities_used': entities,
                    'top_scores': [r.get('final_score', r.get('score', 0)) for r in results[:2]]
                }
                
                logger.info(f"      Found: {len(results)} results")
                if results:
                    logger.info(f"      Top score: {results[0].get('final_score', results[0].get('score', 0)):.3f}")
            
            return {
                'success': True,
                'search_results': search_results,
                'vector_store_stats': self.vector_store.get_stats()
            }
            
        except Exception as e:
            logger.error(f"❌ Vector search test failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_build_stats(self) -> Dict[str, Any]:
        """CẬP NHẬT: Enhanced build stats"""
        config_summary = get_config_summary_enhanced()
        
        return {
            'config': config_summary,
            'vector_store': self.vector_store.get_stats(),
            'embedding_model': self.embedding_model.get_stats(),
            'enhanced_features': [
                'legal_structure_chunking',
                'entity_reranking_support', 
                'e5_base_optimization',
                'query_doc_prefixes',
                'normalized_embeddings'
            ]
        }

async def main():
    """CẬP NHẬT: Main build function với enhanced options"""
    print("🚀 Vietnamese Legal RAG - Vector Store Builder v2.0")
    print("=" * 55)
    
    builder = VectorStoreBuilder()
    
    # Check arguments
    force_rebuild = '--force' in sys.argv or '-f' in sys.argv
    test_only = '--test' in sys.argv or '-t' in sys.argv
    search_test = '--search' in sys.argv or '-s' in sys.argv
    stats_only = '--stats' in sys.argv
    
    if stats_only:
        # Show current stats only
        print("📊 Current build stats:")
        stats = builder.get_build_stats()
        print(f"✅ Config: {stats['config']}")
        return
    
    if test_only:
        # Test embeddings only
        print("🧪 Testing embeddings...")
        result = await builder.test_embeddings()
        print(f"✅ Test result: {result}")
        return
    
    if search_test:
        # Test vector search only
        print("🔍 Testing vector search...")
        result = await builder.test_vector_search()
        print(f"✅ Search test: {result}")
        return
    
    # CẬP NHẬT: Enhanced build process
    print(f"🔧 Using embedding model: {config.embedding_model}")
    print(f"📁 Documents path: {config.documents_path}")
    print(f"💾 Vector store path: {config.vector_store_path}")
    print()
    
    # Build vector store
    result = await builder.build(force_rebuild=force_rebuild)
    
    if result['success']:
        print("\n🎉 BUILD SUCCESSFUL!")
        print(f"📊 {result['stats']['total_documents']} documents indexed")
        print(f"⚖️ {result['stats']['legal_chunks']} legal structure chunks")
        print(f"📜 {result['stats']['articles_found']} articles found")
        print(f"⏱️ Build time: {result['stats']['build_time_seconds']:.2f}s")
        
        # CẬP NHẬT: Enhanced post-build options
        print("\n🧪 Post-build tests:")
        
        # Test embeddings
        test_input = input("Test embeddings? (y/N): ")
        if test_input.lower() == 'y':
            test_result = await builder.test_embeddings()
            if test_result['success']:
                print("✅ Embedding test passed!")
            else:
                print(f"❌ Embedding test failed: {test_result.get('message', 'Unknown error')}")
        
        # Test vector search
        search_input = input("Test vector search với entity reranking? (y/N): ")
        if search_input.lower() == 'y':
            search_result = await builder.test_vector_search()
            if search_result['success']:
                print("✅ Vector search test passed!")
                print(f"📊 Search results: {search_result['search_results']}")
            else:
                print(f"❌ Vector search test failed: {search_result.get('error', 'Unknown error')}")
        
    else:
        print(f"\n❌ BUILD FAILED: {result['message']}")
        if 'error' in result:
            print(f"Error details: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    # CẬP NHẬT: Enhanced usage examples
    print("Usage examples:")
    print("  python build_vector.py          # Normal build with prompts")
    print("  python build_vector.py --force  # Force rebuild")
    print("  python build_vector.py --test   # Test embeddings only")
    print("  python build_vector.py --search # Test vector search only")
    print("  python build_vector.py --stats  # Show current stats")
    print()
    
    asyncio.run(main())