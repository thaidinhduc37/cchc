# server/services/vector_rag/build_vector.py - REWRITTEN FOR DOCX Q&A
"""
🔨 VECTOR DATABASE BUILDER - Rewritten for DOCX Q&A Support
✅ UPDATED: Clean build process với DOCX Q&A support
✅ UPDATED: Sync với document processor mới (legal_document + qa_entry)
✅ UPDATED: Sync với vector store mới (enhanced stats)
🎯 APPROACH: Legal Article Extraction + DOCX Q&A Processing
"""
import asyncio
import argparse
import logging
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from app.services.vector_rag.rag_config import config, configure_for_simple_mode
from app.services.vector_rag.core.document_processor import DocumentProcessor
from app.services.vector_rag.core.embeddings import VietnameseEmbeddingModel
from app.services.vector_rag.core.vector_store import VectorStore

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BuildLogger:
    """📝 Simple logging for build process"""
    
    def __init__(self, vector_store_path: str):
        self.log_file = os.path.join(vector_store_path, "build_log.json")
        self.build_start = datetime.now()
        
        self.log_data = {
            'build_session': {
                'start_time': self.build_start.isoformat(),
                'approach': 'Legal Article Extraction + DOCX Q&A',
                'domain': config.domain,
                'embedding_model': config.embedding_model
            },
            'processing': {
                'files_processed': [],
                'content_summary': {}
            },
            'build_stats': {},
            'errors': []
        }
        
        os.makedirs(vector_store_path, exist_ok=True)
        logger.info("📝 Build logger initialized")
    
    def log_error(self, error_type: str, message: str, details: Dict = None):
        """Log error"""
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'message': message,
            'details': details or {}
        }
        self.log_data['errors'].append(error_info)
        logger.error(f"❌ {error_type}: {message}")
    
    def finalize_log(self, success: bool, final_stats: Dict):
        """Finalize and save logs"""
        self.log_data['build_session']['end_time'] = datetime.now().isoformat()
        self.log_data['build_session']['duration_seconds'] = (
            datetime.now() - self.build_start
        ).total_seconds()
        self.log_data['build_session']['success'] = success
        self.log_data['build_stats'] = final_stats
        
        # Save JSON log
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.log_data, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"📝 Build log saved: {self.log_file}")
        except Exception as e:
            logger.error(f"Failed to save build log: {e}")

class RAGBuilder:
    """🏗️ RAG Builder for Legal Chatbot - DOCX Q&A Support"""
    
    def __init__(self, domain: str = "xuatnhapcanh"):
        self.domain = domain
        self.vector_store = VectorStore()
        self.document_processor = DocumentProcessor()
        
        # Initialize logger
        self.logger = BuildLogger(config.vector_store_path)
        
        # Stats tracking
        self.stats = {
            'start_time': datetime.now(),
            'domain': domain,
            'files_processed': 0,
            'total_chunks': 0,
            'build_time': 0.0
        }
        
        logger.info(f"🏗️ RAG Builder initialized for domain: {domain}")
        logger.info(f"📁 Documents: {config.documents_path}")
        logger.info(f"💾 Vector store: {config.vector_store_path}")
        logger.info(f"🎯 Approach: Legal Article Extraction + DOCX Q&A")
    
    async def build(self, force_rebuild: bool = False) -> Dict[str, Any]:
        """🚀 Build vector database with DOCX Q&A support"""
        build_success = False
        
        try:
            logger.info("🔨 Starting build process...")
            start_time = time.time()
            
            # STEP 1: Process documents
            logger.info("📄 Processing documents...")
            documents = self.document_processor.process_directory(config.documents_path)
            
            if not documents:
                error_msg = "No documents found - check paths and file formats (.docx)"
                self.logger.log_error("NO_DOCUMENTS", error_msg)
                raise Exception(error_msg)
            
            # STEP 2: Analyze processed documents
            doc_analysis = self._analyze_documents(documents)
            logger.info(f"📊 Document analysis:")
            logger.info(f"   📄 Files processed: {doc_analysis['files_count']}")
            logger.info(f"   📦 Total chunks: {doc_analysis['total_chunks']}")
            logger.info(f"   ❓ Q&A entries: {doc_analysis['qa_entries']}")
            logger.info(f"   ⚖️ Legal documents: {doc_analysis['legal_documents']}")
            
            # STEP 3: Build vector store
            logger.info("🧮 Building vector database...")
            build_result = await self.vector_store.build_if_needed(force_rebuild=force_rebuild)
            
            if not build_result['success']:
                error_msg = f"Vector store build failed: {build_result.get('message', 'Unknown error')}"
                self.logger.log_error("VECTOR_BUILD_FAILED", error_msg, build_result)
                raise Exception(error_msg)
            
            # STEP 4: Quick verification
            logger.info("🧪 Verifying build...")
            verification = await self._verify_build()
            
            if not verification['success']:
                logger.warning(f"Build verification had issues: {verification.get('message')}")
                # Don't fail build for verification issues, just warn
            
            # SUCCESS
            build_time = time.time() - start_time
            self.stats['build_time'] = build_time
            self.stats['files_processed'] = doc_analysis['files_count']
            self.stats['total_chunks'] = doc_analysis['total_chunks']
            
            # Get vector store stats
            vector_stats = build_result.get('stats', {})
            
            final_result = {
                'success': True,
                'approach': 'Legal Article Extraction + DOCX Q&A',
                'domain': self.domain,
                'build_time': build_time,
                'files_processed': self.stats['files_processed'],
                'total_chunks': self.stats['total_chunks'],
                'qa_entries': doc_analysis['qa_entries'],
                'legal_documents': doc_analysis['legal_documents'],
                'law_units_found': vector_stats.get('law_units_found', 0),
                'vector_stats': vector_stats,
                'verification': verification,
                'message': f'✅ Built vector database with {self.stats["total_chunks"]} chunks in {build_time:.1f}s',
                'log_file': self.logger.log_file
            }
            
            build_success = True
            logger.info("✅ Build completed successfully!")
            
            return final_result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ BUILD FAILED: {error_msg}")
            
            self.logger.log_error("BUILD_FAILED", error_msg, {'stats': self.stats})
            
            return {
                'success': False,
                'error': error_msg,
                'domain': self.domain,
                'stats': self.stats,
                'log_file': self.logger.log_file
            }
        
        finally:
            # Always save logs
            try:
                self.logger.finalize_log(build_success, self.stats)
            except Exception as log_error:
                logger.error(f"Failed to save logs: {log_error}")
    
    def _analyze_documents(self, documents: List) -> Dict[str, Any]:
        """📊 Analyze processed documents"""
        analysis = {
            'total_chunks': len(documents),
            'qa_entries': 0,
            'legal_documents': 0,
            'files_count': 0,
            'content_types': {}
        }
        
        files_seen = set()
        
        for doc in documents:
            # Track unique files
            source = doc.metadata.get('source', 'unknown')
            files_seen.add(source)
            
            # Track content types
            content_type = doc.metadata.get('content_type', 'unknown')
            analysis['content_types'][content_type] = analysis['content_types'].get(content_type, 0) + 1
            
            if content_type == 'qa_entry':
                analysis['qa_entries'] += 1
            elif content_type == 'legal_document':
                analysis['legal_documents'] += 1
        
        analysis['files_count'] = len(files_seen)
        return analysis
    
    async def _verify_build(self) -> Dict[str, Any]:
        """🧪 Simple build verification"""
        try:
            # Initialize vector store
            init_result = await self.vector_store.initialize()
            if not init_result['success']:
                return {
                    'success': False,
                    'message': f"Vector store initialization failed: {init_result.get('message')}"
                }
            
            # Test searches with different types of queries
            test_queries = [
                "Điều kiện cấp hộ chiếu",           # Legal query
                "Trẻ em dưới 14 tuổi",             # Age-specific query  
                "Thủ tục làm hộ chiếu cho con tôi", # Q&A style query
                "Lệ phí xuất cảnh"                 # Fee query
            ]
            
            verification_results = []
            
            for query in test_queries:
                try:
                    results = await self.vector_store.search(query, k=3)
                    verification_results.append({
                        'query': query,
                        'results_count': len(results),
                        'success': len(results) > 0,
                        'has_qa': any(r.get('metadata', {}).get('content_type') == 'qa_entry' for r in results),
                        'has_legal': any(r.get('metadata', {}).get('content_type') == 'legal_document' for r in results)
                    })
                except Exception as e:
                    verification_results.append({
                        'query': query,
                        'results_count': 0,
                        'success': False,
                        'error': str(e)
                    })
            
            # Overall verification
            successful_queries = sum(1 for r in verification_results if r['success'])
            qa_working = any(r.get('has_qa', False) for r in verification_results)
            legal_working = any(r.get('has_legal', False) for r in verification_results)
            
            verification_success = successful_queries >= len(test_queries) // 2
            
            verification = {
                'success': verification_success,
                'test_queries_passed': f"{successful_queries}/{len(test_queries)}",
                'qa_system_working': qa_working,
                'legal_system_working': legal_working,
                'results': verification_results,
                'message': 'Build verification passed' if verification_success else 'Build verification had issues'
            }
            
            logger.info(f"🧪 Verification: {successful_queries}/{len(test_queries)} queries passed")
            logger.info(f"   Q&A system: {'✅' if qa_working else '❌'}")
            logger.info(f"   Legal system: {'✅' if legal_working else '❌'}")
            
            return verification
            
        except Exception as e:
            self.logger.log_error("VERIFICATION_ERROR", str(e))
            return {
                'success': False,
                'message': f"Verification error: {str(e)}"
            }
    
    # Utility methods
    async def clear_domain(self) -> Dict[str, Any]:
        """🗑️ Clear domain data"""
        try:
            logger.info(f"🗑️ Clearing domain: {self.domain}")
            
            files = [
                "documents.pkl", "metadata.pkl", "faiss_index.bin", 
                "build_log.json", "embeddings_cache_enhanced.pkl"
            ]
            
            removed = 0
            for filename in files:
                filepath = os.path.join(config.vector_store_path, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    removed += 1
            
            logger.info(f"✅ Removed {removed} files")
            
            return {
                'success': True,
                'message': f'Cleared {removed} files for domain {self.domain}',
                'files_removed': removed
            }
            
        except Exception as e:
            logger.error(f"❌ Clear failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def quick_test(self, query: str = None) -> Dict[str, Any]:
        """🧪 Quick search test"""
        if not query:
            query = "Con tôi 5 tuổi có được làm hộ chiếu không?"
        
        logger.info(f"🧪 Quick test: '{query}'")
        
        try:
            init_result = await self.vector_store.initialize()
            
            if not init_result['success']:
                return {
                    'success': False,
                    'query': query,
                    'error': 'Vector store not ready - run --build first'
                }
            
            results = await self.vector_store.search(query, k=5)
            health = self.vector_store.get_health_status()
            
            # Analyze results
            qa_results = [r for r in results if r.get('metadata', {}).get('content_type') == 'qa_entry']
            legal_results = [r for r in results if r.get('metadata', {}).get('content_type') == 'legal_document']
            
            logger.info(f"   📊 Results: {len(results)} total ({len(qa_results)} Q&A, {len(legal_results)} legal)")
            
            return {
                'success': len(results) > 0,
                'query': query,
                'results_count': len(results),
                'qa_results': len(qa_results),
                'legal_results': len(legal_results),
                'database_ready': len(results) > 0,
                'sample_results': [
                    {
                        'content_preview': result.get('content', '')[:100] + '...',
                        'score': result.get('score', 0),
                        'type': result.get('metadata', {}).get('content_type', 'unknown'),
                        'source': result.get('metadata', {}).get('source', 'unknown')
                    }
                    for result in results[:3]
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Quick test failed: {e}")
            return {'success': False, 'error': str(e), 'query': query}
    
    def get_stats(self) -> Dict[str, Any]:
        """📊 Get comprehensive stats"""
        try:
            health = self.vector_store.get_health_status()
            
            return {
                'domain': self.domain,
                'approach': 'Legal Article Extraction + DOCX Q&A',
                'build_stats': self.stats,
                'vector_health': health,
                'paths': {
                    'documents': config.documents_path,
                    'vector_store': config.vector_store_path
                },
                'log_file': self.logger.log_file,
                'features': [
                    'Legal document processing (Điều/Khoản/Điểm)',
                    'DOCX Q&A processing (CÂU HỎI/TRẢ LỜI)',
                    'Enhanced embeddings với Vietnamese support',
                    'Content priority search (Q&A priority)',
                    'Intent-aware search'
                ]
            }
        except Exception as e:
            return {'error': f'Failed to get stats: {e}'}


async def main():
    """🚀 Main function"""
    parser = argparse.ArgumentParser(description="Vector Database Builder for Legal RAG Chatbot")
    
    # Domain
    parser.add_argument('--domain', '-d', default='xuatnhapcanh', 
                       help='Domain to build')
    
    # Actions
    parser.add_argument('--force', '-f', action='store_true', 
                       help='Force rebuild')
    parser.add_argument('--build', '-b', action='store_true', 
                       help='Build database')
    parser.add_argument('--clear', '-c', action='store_true', 
                       help='Clear data')
    parser.add_argument('--stats', '-s', action='store_true', 
                       help='Show stats')
    parser.add_argument('--quick-test', '-q', type=str, nargs='?', const='', 
                       help='Quick test with optional custom query')
    
    # Config
    parser.add_argument('--simple-mode', action='store_true', 
                       help='Enable simple mode config')
    
    args = parser.parse_args()
    
    # Apply simple mode config
    if args.simple_mode:
        configure_for_simple_mode()
        logger.info("🎯 Simple mode config applied")
    
    # Initialize builder
    builder = RAGBuilder(domain=args.domain)
    
    # Execute commands
    if args.clear:
        result = await builder.clear_domain()
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result.get('error')}")
        return
    
    if args.stats:
        stats = builder.get_stats()
        if 'error' in stats:
            print(f"❌ {stats['error']}")
        else:
            print(f"📂 Domain: {stats['domain']}")
            print(f"🎯 Approach: {stats['approach']}")
            print(f"📄 Files: {stats['build_stats']['files_processed']}")
            print(f"📦 Total chunks: {stats['build_stats']['total_chunks']}")
            print(f"📝 Log: {stats['log_file']}")
            
            health = stats['vector_health']
            if 'searcher_stats' in health:
                vs = health['searcher_stats']
                print(f"🧮 Vectors: {vs.get('documents_loaded', 0)}")
                print(f"🔍 Searches: {vs.get('search_performance', {}).get('total_searches', 0)}")
        return
    
    if args.quick_test is not None:
        query = args.quick_test if args.quick_test else None
        result = await builder.quick_test(query)
        
        print(f"🧪 Quick Test:")
        print(f"   Query: {result['query']}")
        print(f"   Ready: {'✅' if result['success'] else '❌'}")
        print(f"   Results: {result.get('results_count', 0)}")
        if 'qa_results' in result:
            print(f"   Q&A: {result['qa_results']}, Legal: {result['legal_results']}")
        
        if result.get('error'):
            print(f"   Error: {result['error']}")
        return
    
    # Build command
    if args.force or args.build:
        force = args.force
        action = "Force rebuilding" if force else "Building"
        
        logger.info(f"🔨 {action} vector database for {args.domain}")
        
        result = await builder.build(force_rebuild=force)
        
        if result['success']:
            print(f"\n🎉 BUILD SUCCESSFUL!")
            print(f"   Approach: {result['approach']}")
            print(f"   Domain: {result['domain']}")
            print(f"   Files: {result['files_processed']}")
            print(f"   Total chunks: {result['total_chunks']}")
            print(f"   Q&A entries: {result['qa_entries']}")
            print(f"   Legal documents: {result['legal_documents']}")
            print(f"   Law units found: {result['law_units_found']}")
            print(f"   Build time: {result['build_time']:.1f}s")
            print(f"\n📝 Build log: {result['log_file']}")
            
            # Show verification results
            verification = result.get('verification', {})
            if verification:
                print(f"\n🧪 Verification: {verification['test_queries_passed']} test queries passed")
                print(f"   Q&A system: {'✅' if verification.get('qa_system_working') else '❌'}")
                print(f"   Legal system: {'✅' if verification.get('legal_system_working') else '❌'}")
                
        else:
            print(f"\n❌ BUILD FAILED!")
            print(f"Error: {result.get('error')}")
            if 'log_file' in result:
                print(f"\n📝 Check build log: {result['log_file']}")
            sys.exit(1)
        return
    
    # No action - show help
    print("🔨 Vector Database Builder for Legal RAG Chatbot:")
    print("  --force (-f)     : Force rebuild")
    print("  --build (-b)     : Build database")  
    print("  --clear (-c)     : Clear data")
    print("  --stats (-s)     : Show stats")
    print("  --quick-test (-q): Quick test [optional custom query]")
    print("  --simple-mode    : Enable simple mode config")
    print("\nApproach: Legal Article Extraction + DOCX Q&A")
    print("\nKey Features:")
    print("  ✅ Legal document processing (Điều/Khoản/Điểm structure)")
    print("  ✅ DOCX Q&A support (CÂU HỎI/TRẢ LỜI format)")
    print("  ✅ Enhanced Vietnamese embeddings")
    print("  ✅ Content priority search (Q&A gets priority)")
    print("  ✅ Build verification with test queries")
    print("\nExamples:")
    print("  python build_vector.py --domain xuatnhapcanh --build --simple-mode")
    print("  python build_vector.py --quick-test \"Con tôi 5 tuổi làm hộ chiếu\"")
    print("  python build_vector.py --stats")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)