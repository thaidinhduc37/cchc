# Enhanced test script để kiểm tra toàn diện hệ thống build vector
import os
import subprocess
import sys
import json
import pickle
from pathlib import Path
import time
from datetime import datetime

def print_section(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print('='*60)

def print_subsection(title):
    """Print subsection header"""
    print(f"\n📋 {title}")
    print('-'*40)

def check_file_exists(filepath, description=""):
    """Check if file exists and return info"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        size_mb = size / (1024 * 1024)
        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        print(f"   ✅ {filepath} ({size_mb:.2f}MB, modified: {mod_time.strftime('%Y-%m-%d %H:%M')})")
        return True, size
    else:
        print(f"   ❌ {filepath} - Missing")
        return False, 0

def test_system_files():
    """Test 1: Kiểm tra các file hệ thống"""
    print_section("SYSTEM FILES CHECK")
    
    required_files = {
        "Build Script": "services/vector_rag/build_vector.py",
        "Document Processor": "services/vector_rag/document_processor.py", 
        "Embeddings": "services/vector_rag/embeddings.py",
        "RAG Config": "services/vector_rag/rag_config.py",
        "Vector Store": "services/vector_rag/vector_store.py"
    }
    
    all_exist = True
    for desc, filepath in required_files.items():
        exists, _ = check_file_exists(filepath, desc)
        if not exists:
            all_exist = False
    
    return all_exist

def test_dataset_structure():
    """Test 2: Kiểm tra cấu trúc dataset"""
    print_section("DATASET STRUCTURE CHECK")
    
    # Use same paths as config
    base_paths = [
        "./dataset/xuatnhapcanh/documents",
        "./dataset/xuatnhapcanh/vector_store"
    ]
    
    dataset_info = {}
    
    for path in base_paths:
        print_subsection(f"Checking {path}")
        if os.path.exists(path):
            files = os.listdir(path)
            
            # Phân loại files
            docx_files = [f for f in files if f.endswith('.docx')]
            json_files = [f for f in files if f.endswith('.json')]
            pkl_files = [f for f in files if f.endswith('.pkl')]
            bin_files = [f for f in files if f.endswith('.bin')]
            other_files = [f for f in files if not any(f.endswith(ext) for ext in ['.docx', '.json', '.pkl', '.bin'])]
            
            print(f"   📁 Total files: {len(files)}")
            if docx_files:
                print(f"   📄 DOCX files: {len(docx_files)}")
                for f in docx_files[:5]:  # Show first 5
                    print(f"      - {f}")
                if len(docx_files) > 5:
                    print(f"      ... and {len(docx_files) - 5} more")
            
            if json_files:
                print(f"   📋 JSON files: {len(json_files)}")
                for f in json_files[:3]:
                    print(f"      - {f}")
            
            if pkl_files:
                print(f"   💾 PKL files: {len(pkl_files)}")
                for f in pkl_files:
                    print(f"      - {f}")
            
            if bin_files:
                print(f"   🧮 BIN files: {len(bin_files)}")
                for f in bin_files:
                    print(f"      - {f}")
            
            if other_files:
                print(f"   📄 Other files: {len(other_files)}")
            
            dataset_info[path] = {
                'total': len(files),
                'docx': len(docx_files),
                'json': len(json_files),
                'pkl': len(pkl_files),
                'bin': len(bin_files),
                'docx_files': docx_files,
                'json_files': json_files
            }
        else:
            print(f"   ❌ Path not found: {path}")
            dataset_info[path] = {'total': 0, 'docx': 0, 'json': 0, 'pkl': 0, 'bin': 0}
    
    return dataset_info

def test_document_content_analysis():
    """Test 3: Phân tích nội dung documents để kiểm tra extract được gì"""
    print_section("DOCUMENT CONTENT ANALYSIS")
    
    # Use same path as config
    documents_path = "./dataset/xuatnhapcanh/documents"
    if not os.path.exists(documents_path):
        print("❌ Documents path not found")
        return {}
    
    # Fix import path
    try:
        # Add current directory to path instead of services/vector_rag
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        from document_processor import DocumentProcessor
        print("✅ DocumentProcessor imported successfully")
        
        processor = DocumentProcessor()
        
        # Test process directory
        print_subsection("Processing Documents")
        documents = processor.process_directory(documents_path)
        
        print(f"📊 Total documents processed: {len(documents)}")
        
        # Phân tích theo content type
        content_analysis = {
            'qa_entry': [],
            'legal_document': [],
            'unknown': []
        }
        
        law_units_found = []
        
        for i, doc in enumerate(documents):
            if hasattr(doc, 'metadata'):
                content_type = doc.metadata.get('content_type', 'unknown')
                content_analysis[content_type].append(i)
                
                # Thu thập law_unit info
                if content_type == 'legal_document':
                    law_unit = doc.metadata.get('law_unit')
                    if law_unit:
                        law_units_found.append(law_unit)
        
        # In thống kê
        print_subsection("Content Type Breakdown")
        for content_type, doc_indices in content_analysis.items():
            print(f"   📋 {content_type}: {len(doc_indices)} documents")
            
            # Show sample content for each type
            if doc_indices and len(doc_indices) > 0:
                sample_idx = doc_indices[0]
                if sample_idx < len(documents):
                    sample_doc = documents[sample_idx]
                    content_preview = sample_doc.content[:200] + "..." if len(sample_doc.content) > 200 else sample_doc.content
                    print(f"      📄 Sample content: {content_preview}")
                    if hasattr(sample_doc, 'metadata'):
                        print(f"      🏷️  Sample metadata: {sample_doc.metadata}")
        
        # Phân tích law_units (Điều/Khoản/Điểm)
        if law_units_found:
            print_subsection("Legal Structure Analysis")
            print(f"   📜 Law units found: {len(law_units_found)}")
            
            # Phân loại law_units
            dieu_count = len([lu for lu in law_units_found if '.' not in lu])  # Chỉ số Điều
            khoan_count = len([lu for lu in law_units_found if lu.count('.') == 1])  # Điều.Khoản
            diem_count = len([lu for lu in law_units_found if lu.count('.') == 2])  # Điều.Khoản.Điểm
            
            print(f"      ⚖️  Điều level: {dieu_count}")
            print(f"      📝 Khoản level: {khoan_count}")
            print(f"      📍 Điểm level: {diem_count}")
            
            # Show some examples
            print(f"      📋 Examples: {law_units_found[:10]}")
        
        # Q&A Analysis
        qa_docs = [documents[i] for i in content_analysis['qa_entry']]
        if qa_docs:
            print_subsection("Q&A Analysis")
            print(f"   ❓ Total Q&A entries: {len(qa_docs)}")
            
            # Check format
            docx_qa_format = 0
            for qa_doc in qa_docs[:5]:  # Check first 5
                if 'CÂU HỎI:' in qa_doc.content and 'TRẢ LỜI:' in qa_doc.content:
                    docx_qa_format += 1
            
            print(f"   📄 DOCX Q&A format (CÂU HỎI/TRẢ LỜI): {docx_qa_format}/{min(5, len(qa_docs))} checked")
        
        analysis_result = {
            'total_processed': len(documents),
            'content_types': {k: len(v) for k, v in content_analysis.items()},
            'law_units_found': len(law_units_found),
            'law_structure': {
                'dieu': dieu_count if law_units_found else 0,
                'khoan': khoan_count if law_units_found else 0,
                'diem': diem_count if law_units_found else 0
            } if law_units_found else {},
            'qa_format_check': {
                'total_qa': len(qa_docs),
                'docx_format': docx_qa_format if qa_docs else 0
            }
        }
        
        return analysis_result
        
    except Exception as e:
        print(f"❌ Document analysis failed: {e}")
        import traceback
        print(f"   📋 Traceback: {traceback.format_exc()}")
        return {}

def test_vector_store_status():
    """Test 4: Kiểm tra trạng thái vector store"""
    print_section("VECTOR STORE STATUS")
    
    # Use same path as config
    vector_store_path = "./dataset/xuatnhapcanh/vector_store"
    
    if not os.path.exists(vector_store_path):
        print("❌ Vector store path not found")
        return {}
    
    # Check vector store files
    vector_files = {
        "Documents": "documents.pkl",
        "Metadata": "metadata.pkl", 
        "FAISS Index": "faiss_index.bin",
        "Build Log": "build_log.json",
        "Embeddings Cache": "embeddings_cache_enhanced.pkl"
    }
    
    store_status = {}
    
    for desc, filename in vector_files.items():
        filepath = os.path.join(vector_store_path, filename)
        exists, size = check_file_exists(filepath, desc)
        store_status[filename] = {'exists': exists, 'size': size}
    
    # Analyze vector store content if possible
    if store_status['documents.pkl']['exists']:
        try:
            docs_file = os.path.join(vector_store_path, "documents.pkl")
            meta_file = os.path.join(vector_store_path, "metadata.pkl")
            
            print_subsection("Vector Store Content Analysis")
            
            with open(docs_file, 'rb') as f:
                documents = pickle.load(f)
            print(f"   📄 Documents in store: {len(documents)}")
            
            if store_status['metadata.pkl']['exists']:
                with open(meta_file, 'rb') as f:
                    metadata = pickle.load(f)
                print(f"   🏷️  Metadata entries: {len(metadata)}")
                
                # Analyze metadata
                content_types = {}
                for meta in metadata:
                    content_type = meta.get('content_type', 'unknown')
                    content_types[content_type] = content_types.get(content_type, 0) + 1
                
                print(f"   📊 Content type distribution:")
                for ct, count in content_types.items():
                    print(f"      - {ct}: {count}")
                
                store_status['content_analysis'] = {
                    'total_docs': len(documents),
                    'total_metadata': len(metadata),
                    'content_types': content_types,
                    'consistent': len(documents) == len(metadata)
                }
            
        except Exception as e:
            print(f"   ❌ Failed to analyze vector store content: {e}")
    
    # Check build log if exists
    if store_status['build_log.json']['exists']:
        try:
            log_file = os.path.join(vector_store_path, "build_log.json")
            with open(log_file, 'r', encoding='utf-8') as f:
                build_log = json.load(f)
            
            print_subsection("Last Build Info")
            build_session = build_log.get('build_session', {})
            print(f"   ⏱️  Build time: {build_session.get('start_time', 'Unknown')}")
            print(f"   ✅ Success: {build_session.get('success', False)}")
            print(f"   🎯 Approach: {build_session.get('approach', 'Unknown')}")
            print(f"   ⏱️  Duration: {build_session.get('duration_seconds', 0):.1f}s")
            
            build_stats = build_log.get('build_stats', {})
            if build_stats:
                print(f"   📊 Build stats:")
                for key, value in build_stats.items():
                    print(f"      - {key}: {value}")
                    
            store_status['last_build'] = build_session
            
        except Exception as e:
            print(f"   ❌ Failed to read build log: {e}")
    
    return store_status

def test_build_command():
    """Test 5: Test build command execution"""
    print_section("BUILD COMMAND TEST")
    
    commands_to_test = [
        {
            'name': 'Stats Check',
            'cmd': [sys.executable, "services/vector_rag/build_vector.py", "--domain", "xuatnhapcanh", "--stats"],
            'timeout': 30
        },
        {
            'name': 'Quick Test',
            'cmd': [sys.executable, "services/vector_rag/build_vector.py", "--domain", "xuatnhapcanh", "--quick-test", "Trẻ em làm hộ chiếu"],
            'timeout': 45
        }
    ]
    
    test_results = {}
    
    for test in commands_to_test:
        print_subsection(f"Testing: {test['name']}")
        try:
            print(f"   🚀 Running: {' '.join(test['cmd'])}")
            
            result = subprocess.run(
                test['cmd'], 
                capture_output=True, 
                text=True, 
                timeout=test['timeout'],
                cwd="."
            )
            
            print(f"   📊 Return code: {result.returncode}")
            
            if result.stdout:
                print(f"   📤 STDOUT:")
                for line in result.stdout.split('\n')[:20]:  # First 20 lines
                    if line.strip():
                        print(f"      {line}")
                if len(result.stdout.split('\n')) > 20:
                    print(f"      ... (truncated)")
                    
            if result.stderr:
                print(f"   📥 STDERR:")
                for line in result.stderr.split('\n')[:10]:  # First 10 lines
                    if line.strip():
                        print(f"      {line}")
            
            test_results[test['name']] = {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout_lines': len(result.stdout.split('\n')),
                'stderr_lines': len(result.stderr.split('\n'))
            }
            
        except subprocess.TimeoutExpired:
            print(f"   ⏰ Command timed out after {test['timeout']}s")
            test_results[test['name']] = {'success': False, 'error': 'timeout'}
        except Exception as e:
            print(f"   ❌ Command failed: {e}")
            test_results[test['name']] = {'success': False, 'error': str(e)}
    
    return test_results

def test_search_functionality():
    """Test 6: Test search functionality if vector store is ready"""
    print_section("SEARCH FUNCTIONALITY TEST")
    
    try:
        # Fix import path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        from vector_store import VectorStore
        
        print("✅ VectorStore imported successfully")
        
        # Test queries for both Q&A and legal content
        test_queries = [
            "Trẻ em dưới 14 tuổi làm hộ chiếu cần gì?",
            "Điều kiện cấp hộ chiếu phổ thông",
            "Lệ phí xuất cảnh",
            "Thủ tục làm visa",
            "Con tôi 5 tuổi có được đi nước ngoài không?"
        ]
        
        print_subsection("Initializing Vector Store")
        vector_store = VectorStore()
        
        # Try to initialize
        print("🔄 Attempting to initialize...")
        # Note: This is async, so we'd need to run it properly
        print("   ℹ️  (Async initialization - would need proper async context)")
        
        print_subsection("Test Queries (Simulation)")
        for i, query in enumerate(test_queries):
            print(f"   {i+1}. Query: '{query}'")
            print(f"      Expected: Mix of Q&A and legal results")
            print(f"      Priority: Q&A entries should rank higher")
        
        return {'simulation': True, 'queries_prepared': len(test_queries)}
        
    except Exception as e:
        print(f"❌ Search functionality test failed: {e}")
        return {'error': str(e)}

def generate_summary_report(all_results):
    """Generate final summary report"""
    print_section("COMPREHENSIVE SUMMARY REPORT")
    
    # System health
    system_health = all_results.get('system_files', False)
    print_subsection("System Health")
    print(f"   🏥 System Files: {'✅ OK' if system_health else '❌ MISSING FILES'}")
    
    # Dataset status
    dataset_info = all_results.get('dataset', {})
    docs_path = "./dataset/xuatnhapcanh/documents"
    vector_path = "./dataset/xuatnhapcanh/vector_store"
    
    docs_info = dataset_info.get(docs_path, {})
    vector_info = dataset_info.get(vector_path, {})
    
    print_subsection("Dataset Status")
    print(f"   📄 DOCX Documents: {docs_info.get('docx', 0)}")
    print(f"   📋 JSON Documents: {docs_info.get('json', 0)}")
    print(f"   💾 Vector Store Files: {vector_info.get('total', 0)}")
    
    # Content analysis
    content_analysis = all_results.get('content_analysis', {})
    if content_analysis:
        print_subsection("Content Extraction Results")
        print(f"   📊 Total Documents Processed: {content_analysis.get('total_processed', 0)}")
        
        content_types = content_analysis.get('content_types', {})
        print(f"   ❓ Q&A Entries: {content_types.get('qa_entry', 0)}")
        print(f"   ⚖️  Legal Documents: {content_types.get('legal_document', 0)}")
        print(f"   ❔ Unknown Type: {content_types.get('unknown', 0)}")
        
        law_structure = content_analysis.get('law_structure', {})
        if law_structure:
            print(f"   📜 Legal Structure Extracted:")
            print(f"      - Điều level: {law_structure.get('dieu', 0)}")
            print(f"      - Khoản level: {law_structure.get('khoan', 0)}")
            print(f"      - Điểm level: {law_structure.get('diem', 0)}")
        
        qa_format = content_analysis.get('qa_format_check', {})
        if qa_format.get('total_qa', 0) > 0:
            print(f"   📄 Q&A Format Check:")
            print(f"      - Total Q&A: {qa_format.get('total_qa', 0)}")
            print(f"      - DOCX Format: {qa_format.get('docx_format', 0)}")
    
    # Vector store status
    vector_status = all_results.get('vector_store', {})
    if vector_status:
        print_subsection("Vector Store Status")
        
        content_analysis_vs = vector_status.get('content_analysis', {})
        if content_analysis_vs:
            print(f"   🧮 Vectors Created: {content_analysis_vs.get('total_docs', 0)}")
            print(f"   🔗 Consistency: {'✅ OK' if content_analysis_vs.get('consistent', False) else '❌ MISMATCH'}")
            
            vs_content_types = content_analysis_vs.get('content_types', {})
            for ct, count in vs_content_types.items():
                print(f"   📋 {ct}: {count} vectors")
    
    # Build command tests
    build_tests = all_results.get('build_tests', {})
    if build_tests:
        print_subsection("Build System Status")
        for test_name, result in build_tests.items():
            status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
            print(f"   🧪 {test_name}: {status}")
    
    # Overall assessment
    print_subsection("Overall Assessment")
    
    issues = []
    recommendations = []
    
    if not system_health:
        issues.append("Missing system files")
        recommendations.append("Check file paths and ensure all components are present")
    
    if docs_info.get('docx', 0) == 0:
        issues.append("No DOCX files found")
        recommendations.append("Add DOCX documents to process")
    
    if content_analysis.get('total_processed', 0) == 0:
        issues.append("No documents processed")
        recommendations.append("Run document processing to extract content")
    
    if vector_info.get('total', 0) == 0:
        issues.append("No vector store files")
        recommendations.append("Run build command to create vector database")
    
    if not issues:
        issues.append("System appears healthy")
        recommendations.append("System ready for Q&A processing")
    
    print(f"   🚨 Issues Found: {len([i for i in issues if not i.startswith('System appears')])}")
    for issue in issues:
        status_icon = "✅" if issue.startswith("System appears") else "❌"
        print(f"      {status_icon} {issue}")
    
    print(f"   💡 Recommendations:")
    for rec in recommendations:
        print(f"      💡 {rec}")
    
    # Capability assessment
    print_subsection("System Capabilities")
    
    capabilities = {
        'DOCX Processing': docs_info.get('docx', 0) > 0,
        'Legal Structure Extraction': content_analysis.get('law_structure', {}).get('dieu', 0) > 0,
        'Q&A Processing': content_analysis.get('content_types', {}).get('qa_entry', 0) > 0,
        'Vector Storage': vector_info.get('total', 0) > 0,
        'Build System': any(build_tests.get(test, {}).get('success', False) for test in build_tests)
    }
    
    for capability, status in capabilities.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {capability}")

def main():
    """Main test execution"""
    print(f"🚀 ENHANCED RAG SYSTEM COMPREHENSIVE TEST")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Focus: Vector Build System + Content Extraction")
    
    all_results = {}
    
    # Execute all tests
    try:
        all_results['system_files'] = test_system_files()
        all_results['dataset'] = test_dataset_structure()
        all_results['content_analysis'] = test_document_content_analysis()
        all_results['vector_store'] = test_vector_store_status()
        all_results['build_tests'] = test_build_command()
        all_results['search_test'] = test_search_functionality()
        
        # Generate comprehensive report
        generate_summary_report(all_results)
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
    
    print(f"\n🏁 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()