# server/services/vector_rag/build_vector.py
"""
Build Vector Store Script - OPTIMIZED & SIMPLE
"""
import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.vector_rag.rag_config import config
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
    """Simplified Vector Store Builder"""
    
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.vector_store = VectorStore()
        self.embedding_model = VietnameseEmbeddingModel()
        
        logger.info("🔧 VectorStoreBuilder initialized")
    
    async def build(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """Build vector store from documents"""
        try:
            start_time = datetime.now()
            logger.info("🚀 Starting vector store build...")
            
            # Step 1: Check if rebuild needed
            if not force_rebuild:
                existing_stats = self.vector_store.get_stats()
                if existing_stats['total_documents'] > 0:
                    user_input = input(f"Vector store exists with {existing_stats['total_documents']} documents. Rebuild? (y/N): ")
                    if user_input.lower() != 'y':
                        logger.info("❌ Build cancelled by user")
                        return {'success': False, 'message': 'Cancelled by user'}
            
            # Step 2: Initialize vector store (force rebuild)
            logger.info("🗑️ Clearing existing vector store...")
            await self.vector_store.initialize(force_rebuild=True)
            
            # Step 3: Process documents
            logger.info("📄 Processing documents...")
            documents = self.document_processor.process_directory()
            
            if not documents:
                logger.error("❌ No documents found")
                return {
                    'success': False,
                    'message': 'No documents found in directory',
                    'directory': config.documents_path
                }
            
            logger.info(f"✅ Processed {len(documents)} document chunks")
            
            # Step 4: Add documents to vector store
            logger.info("🧮 Adding documents to vector store...")
            success = await self.vector_store.add_documents(documents)
            
            if not success:
                logger.error("❌ Failed to add documents to vector store")
                return {
                    'success': False,
                    'message': 'Failed to add documents to vector store'
                }
            
            # Step 5: Get final stats
            final_stats = self.vector_store.get_stats()
            build_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'message': f'Vector store built successfully in {build_time:.2f}s',
                'stats': {
                    'total_documents': final_stats['total_documents'],
                    'build_time_seconds': build_time,
                    'embedding_model': final_stats['embedding_model'],
                    'dimension': final_stats.get('dimension', 'unknown')
                }
            }
            
            logger.info("🎉 Vector store build completed successfully!")
            logger.info(f"   📊 Documents: {final_stats['total_documents']}")
            logger.info(f"   ⏱️  Time: {build_time:.2f}s")
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
        """Test embeddings with sample queries"""
        if test_queries is None:
            test_queries = [
                "Điều kiện cấp hộ chiếu phổ thông",
                "Thủ tục làm thị thực",
                "Điều 15 Luật xuất nhập cảnh"
            ]
        
        try:
            logger.info("🧪 Testing embeddings...")
            
            # Generate embeddings for test queries
            embeddings = self.embedding_model.embed_documents(test_queries)
            
            if not embeddings or len(embeddings) != len(test_queries):
                return {
                    'success': False,
                    'message': 'Embedding generation failed'
                }
            
            # Test similarity calculations
            similarities = []
            for i in range(len(embeddings)):
                for j in range(i+1, len(embeddings)):
                    sim = self.embedding_model.calculate_similarity(embeddings[i], embeddings[j])
                    similarities.append(sim)
            
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0
            
            result = {
                'success': True,
                'test_queries': test_queries,
                'embeddings_generated': len(embeddings),
                'embedding_dimension': len(embeddings[0]) if embeddings else 0,
                'average_similarity': round(avg_similarity, 3),
                'embedding_stats': self.embedding_model.get_stats()
            }
            
            logger.info(f"✅ Embedding test passed")
            logger.info(f"   📐 Dimension: {result['embedding_dimension']}")
            logger.info(f"   📊 Avg similarity: {result['average_similarity']}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Embedding test failed: {e}")
            return {
                'success': False,
                'message': f'Test failed: {str(e)}'
            }
    
    def get_build_stats(self) -> Dict[str, Any]:
        """Get build environment stats"""
        return {
            'config': {
                'documents_path': config.documents_path,
                'vector_store_path': config.vector_store_path,
                'embedding_model': config.embedding_model,
                'chunk_size': config.chunk_size,
                'chunk_overlap': config.chunk_overlap
            },
            'vector_store': self.vector_store.get_stats(),
            'embedding_model': self.embedding_model.get_stats()
        }

async def main():
    """Main build function"""
    print("🚀 Vietnamese Legal RAG - Vector Store Builder")
    print("=" * 50)
    
    builder = VectorStoreBuilder()
    
    # Check arguments
    force_rebuild = '--force' in sys.argv or '-f' in sys.argv
    test_only = '--test' in sys.argv or '-t' in sys.argv
    
    if test_only:
        # Test embeddings only
        print("🧪 Testing embeddings...")
        result = await builder.test_embeddings()
        print(f"✅ Test result: {result}")
        return
    
    # Build vector store
    result = await builder.build(force_rebuild=force_rebuild)
    
    if result['success']:
        print("\n🎉 BUILD SUCCESSFUL!")
        print(f"📊 {result['stats']['total_documents']} documents indexed")
        print(f"⏱️  Build time: {result['stats']['build_time_seconds']:.2f}s")
        
        # Optional: Test embeddings after build
        test_input = input("\n🧪 Test embeddings? (y/N): ")
        if test_input.lower() == 'y':
            test_result = await builder.test_embeddings()
            if test_result['success']:
                print("✅ Embedding test passed!")
            else:
                print(f"❌ Embedding test failed: {test_result['message']}")
    else:
        print(f"\n❌ BUILD FAILED: {result['message']}")
        sys.exit(1)

if __name__ == "__main__":
    # Usage examples:
    # python build_vector.py          # Normal build (with prompts)
    # python build_vector.py --force  # Force rebuild
    # python build_vector.py --test   # Test embeddings only
    
    asyncio.run(main())