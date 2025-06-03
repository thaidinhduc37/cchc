# server/services/vector_rag/build_vector.py
"""
Script xây dựng vector store cho lĩnh vực xuất nhập cảnh
Thay thế setup_vector.py với version tối ưu
"""
import os
import sys
import argparse
import asyncio
from pathlib import Path
from datetime import datetime
import logging

# Fix import paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Use relative imports now
from .lightweight_config import SYSTEM_CONFIG
from .lightweight_rag_engine import LightweightRAGEngine, create_rag_engine

# Rest of the file remains the same...
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VectorBuilder:
    """Builder cho vector store xuất nhập cảnh"""
    
    def __init__(self, gemini_api_key: str = None):
        self.config = SYSTEM_CONFIG
        self.gemini_api_key = gemini_api_key or os.getenv('GEMINI_API_KEY')
        
        # Paths
        self.domain = "xuatnhapcanh"
        self.documents_path = os.path.join(self.config.data_path, self.domain, "documents")
        self.process_path = os.path.join(self.config.data_path, self.domain, "process")
        self.vector_store_path = os.path.join(self.process_path, "vectorstore")
        
        # Stats
        self.build_stats = {
            'started_at': None,
            'completed_at': None,
            'total_files': 0,
            'processed_files': 0,
            'total_chunks': 0,
            'build_time': 0,
            'errors': []
        }
    
    def check_prerequisites(self) -> bool:
        """Kiểm tra prerequisites"""
        logger.info("🔍 Checking prerequisites...")
        
        issues = []
        
        # Check documents directory
        if not os.path.exists(self.documents_path):
            issues.append(f"Documents directory not found: {self.documents_path}")
        else:
            # Count files
            supported_formats = ['.pdf', '.txt', '.docx']
            files = []
            for ext in supported_formats:
                files.extend(Path(self.documents_path).rglob(f"*{ext}"))
            
            self.build_stats['total_files'] = len(files)
            
            if len(files) == 0:
                issues.append(f"No supported documents found in {self.documents_path}")
            else:
                logger.info(f"📄 Found {len(files)} document files")
        
        # Check dependencies
        try:
            import chromadb
            logger.info("✅ ChromaDB available")
        except ImportError:
            issues.append("ChromaDB not installed. Run: pip install chromadb")
        
        try:
            import sentence_transformers
            logger.info("✅ sentence-transformers available")
        except ImportError:
            issues.append("sentence-transformers not installed. Run: pip install sentence-transformers")
        
        # Check LLM availability (warning only)
        if self.gemini_api_key:
            logger.info("✅ Gemini API key configured")
        else:
            logger.warning("⚠️ No Gemini API key found. Set GEMINI_API_KEY environment variable")
        
        # Check Ollama (optional)
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                logger.info("✅ Ollama server available")
            else:
                logger.info("ℹ️ Ollama server not responding")
        except:
            logger.info("ℹ️ Ollama server not available")
        
        if issues:
            logger.error("❌ Prerequisites check failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False
        
        logger.info("✅ Prerequisites check passed")
        return True
    
    def setup_directories(self):
        """Tạo directories cần thiết"""
        logger.info("📁 Setting up directories...")
        
        directories = [
            self.documents_path,
            self.process_path,
            self.vector_store_path,
            os.path.join(self.process_path, "cache"),
            os.path.join(self.process_path, "logs")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.info(f"✅ Directory: {directory}")
    
    async def build_vector_store(self, force_rebuild: bool = False) -> bool:
        """Xây dựng vector store"""
        logger.info("🔨 Building vector store...")
        self.build_stats['started_at'] = datetime.now()
        
        try:
            # Create RAG engine
            engine = create_rag_engine(gemini_api_key=self.gemini_api_key)
            
            # Initialize system
            result = await engine.initialize_system(
                force_rebuild=force_rebuild,
                documents_path=self.documents_path
            )
            
            if result['success']:
                self.build_stats['completed_at'] = datetime.now()
                self.build_stats['build_time'] = (
                    self.build_stats['completed_at'] - self.build_stats['started_at']
                ).total_seconds()
                
                # Get final stats
                system_stats = engine.get_system_stats()
                vector_stats = system_stats.get('vector_store', {})
                
                self.build_stats['total_chunks'] = vector_stats.get('total_documents', 0)
                self.build_stats['processed_files'] = sum(vector_stats.get('file_types', {}).values())
                
                logger.info("✅ Vector store built successfully!")
                logger.info(f"📊 Stats:")
                logger.info(f"  - Total chunks: {self.build_stats['total_chunks']}")
                logger.info(f"  - Build time: {self.build_stats['build_time']:.2f}s")
                logger.info(f"  - Storage path: {self.vector_store_path}")
                
                return True
            else:
                logger.error(f"❌ Failed to build vector store: {result['message']}")
                self.build_stats['errors'].append(result['message'])
                return False
        
        except Exception as e:
            logger.error(f"❌ Build failed with exception: {e}")
            self.build_stats['errors'].append(str(e))
            return False
    
    def clean_vector_store(self):
        """Xóa vector store hiện có"""
        logger.info("🗑️ Cleaning existing vector store...")
        
        try:
            if os.path.exists(self.vector_store_path):
                import shutil
                shutil.rmtree(self.vector_store_path)
                logger.info(f"✅ Cleaned: {self.vector_store_path}")
            
            # Recreate directory
            os.makedirs(self.vector_store_path, exist_ok=True)
            
        except Exception as e:
            logger.error(f"❌ Failed to clean vector store: {e}")
            raise
    
    def validate_build(self) -> bool:
        """Validate build kết quả"""
        logger.info("🔍 Validating build result...")
        
        try:
            # Check vector store directory exists và có files
            if not os.path.exists(self.vector_store_path):
                logger.error("❌ Vector store directory not found")
                return False
            
            # Check ChromaDB files
            chroma_files = list(Path(self.vector_store_path).rglob("*"))
            if not chroma_files:
                logger.error("❌ No vector store files found")
                return False
            
            logger.info(f"✅ Found {len(chroma_files)} vector store files")
            
            # Test quick query
            logger.info("🧪 Testing quick query...")
            
            async def test_query():
                engine = create_rag_engine(gemini_api_key=self.gemini_api_key)
                await engine.initialize_system(documents_path=self.documents_path)
                
                # Test search without LLM
                search_result = engine.search_documents("visa nhập cảnh", k=2)
                return search_result['success'] and len(search_result['results']) > 0
            
            test_passed = asyncio.run(test_query())
            
            if test_passed:
                logger.info("✅ Validation passed")
                return True
            else:
                logger.error("❌ Validation failed - no search results")
                return False
                
        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            return False
    
    def print_build_summary(self):
        """In tóm tắt build"""
        print("\n" + "="*60)
        print("📊 BUILD SUMMARY")
        print("="*60)
        
        print(f"Domain: {self.domain}")
        print(f"Documents path: {self.documents_path}")
        print(f"Vector store path: {self.vector_store_path}")
        print()
        
        if self.build_stats['started_at']:
            print(f"Started at: {self.build_stats['started_at']}")
            
        if self.build_stats['completed_at']:
            print(f"Completed at: {self.build_stats['completed_at']}")
            print(f"Build time: {self.build_stats['build_time']:.2f} seconds")
        
        print(f"Total files: {self.build_stats['total_files']}")
        print(f"Processed files: {self.build_stats['processed_files']}")
        print(f"Total chunks: {self.build_stats['total_chunks']}")
        
        if self.build_stats['errors']:
            print(f"\n❌ Errors ({len(self.build_stats['errors'])}):")
            for error in self.build_stats['errors']:
                print(f"  - {error}")
        else:
            print("\n✅ No errors")
        
        print("="*60)

def show_example_usage():
    """Hiển thị example usage"""
    print("""
📚 HƯỚNG DẪN SỬ DỤNG:

1. CẤU TRÚC THƯ MỤC:
   server/dataset/xuatnhapcanh/
   ├── documents/           # Chứa files PDF, TXT, DOCX
   │   ├── luat_xnc_2014.pdf
   │   ├── nghidinh_08_2015.txt
   │   └── thongtu_01_2016.docx
   └── process/            # Tự động tạo
       ├── vectorstore/    # Vector store
       ├── cache/          # Cache
       └── logs/           # Logs

2. CÀI ĐẶT DEPENDENCIES:
   pip install chromadb sentence-transformers google-generativeai

3. CẤU HÌNH:
   export GEMINI_API_KEY="your-gemini-api-key"  # Optional

4. CHẠY BUILD:
   python build_vector.py --build
   python build_vector.py --force    # Force rebuild
   python build_vector.py --clean    # Clean first
   python build_vector.py --test     # Test only

5. VALIDATE:
   python build_vector.py --validate
""")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Build vector store cho lĩnh vực xuất nhập cảnh",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--build', action='store_true', 
                       help='Build vector store')
    parser.add_argument('--force', action='store_true',
                       help='Force rebuild vector store')
    parser.add_argument('--clean', action='store_true',
                       help='Clean existing vector store')
    parser.add_argument('--validate', action='store_true',
                       help='Validate existing vector store')
    parser.add_argument('--test', action='store_true',
                       help='Test build với sample data')
    parser.add_argument('--examples', action='store_true',
                       help='Show usage examples')
    parser.add_argument('--gemini-key', type=str,
                       help='Gemini API key (optional)')
    
    args = parser.parse_args()
    
    if args.examples:
        show_example_usage()
        return
    
    if not any([args.build, args.force, args.clean, args.validate, args.test]):
        parser.print_help()
        return
    
    # Create builder
    builder = VectorBuilder(gemini_api_key=args.gemini_key)
    
    try:
        # Check prerequisites
        if not builder.check_prerequisites():
            print("\n❌ Prerequisites check failed. Please fix issues above.")
            return
        
        # Setup directories
        builder.setup_directories()
        
        # Clean if requested
        if args.clean or args.force:
            builder.clean_vector_store()
        
        # Build if requested
        if args.build or args.force or args.test:
            success = await builder.build_vector_store(force_rebuild=args.force)
            
            if success:
                print("\n✅ Vector store build completed successfully!")
                
                # Auto-validate after build
                if builder.validate_build():
                    print("✅ Validation passed")
                else:
                    print("⚠️ Validation failed")
            else:
                print("\n❌ Vector store build failed!")
        
        # Validate if requested
        elif args.validate:
            if builder.validate_build():
                print("\n✅ Vector store validation passed!")
            else:
                print("\n❌ Vector store validation failed!")
        
        # Print summary
        builder.print_build_summary()
        
    except KeyboardInterrupt:
        print("\n⏹️ Build interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        logger.exception("Unexpected error occurred")

if __name__ == "__main__":
    asyncio.run(main())