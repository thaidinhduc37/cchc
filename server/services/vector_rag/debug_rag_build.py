# services/vector_rag/debug_rag_build.py
# Debug test script để kiểm tra extract system chi tiết
import os
import sys
import json
import pickle
from pathlib import Path
import time
from datetime import datetime

# Fix import path - từ server/ directory
sys.path.append(str(Path(__file__).parent.parent.parent))

def print_section(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print('='*60)

def print_subsection(title):
    """Print subsection header"""
    print(f"\n📋 {title}")
    print('-'*40)

def debug_document_processor():
    """Debug 1: Test DocumentProcessor extract capabilities"""
    print_section("DOCUMENT PROCESSOR DEBUG")
    
    try:
        from services.vector_rag.document_processor import DocumentProcessor
        from services.vector_rag.rag_config import config
        print("✅ DocumentProcessor imported successfully")
        
        processor = DocumentProcessor()
        documents_path = config.documents_path
        print(f"📁 Documents path: {documents_path}")
        
        if not os.path.exists(documents_path):
            print(f"❌ Documents path not found: {documents_path}")
            return {}
        
        print_subsection("Testing Individual Files")
        
        docx_files = list(Path(documents_path).glob('*.docx'))
        print(f"📄 Found {len(docx_files)} DOCX files:")
        
        file_results = {}
        
        for i, file_path in enumerate(docx_files):
            print(f"\n🔍 File {i+1}: {file_path.name}")
            print(f"   📏 Size: {os.path.getsize(file_path):,} bytes")
            
            try:
                start_time = time.time()
                documents = processor.process_file(str(file_path))
                process_time = time.time() - start_time
                
                print(f"   ⏱️  Processing time: {process_time:.3f}s")
                print(f"   📦 Chunks created: {len(documents)}")
                
                if documents:
                    content_types = {}
                    law_units = []
                    qa_questions = []
                    authorities = set()
                    doc_types = set()
                    
                    for doc in documents:
                        if hasattr(doc, 'metadata'):
                            content_type = doc.metadata.get('content_type', 'unknown')
                            content_types[content_type] = content_types.get(content_type, 0) + 1
                            
                            if content_type == 'legal_document':
                                law_unit = doc.metadata.get('law_unit')
                                if law_unit:
                                    law_units.append(law_unit)
                                authority = doc.metadata.get('authority_level', 'unknown')
                                authorities.add(authority)
                                doc_type = doc.metadata.get('doc_type', 'unknown')
                                doc_types.add(doc_type)
                            
                            elif content_type == 'qa_entry':
                                question = doc.metadata.get('question', '')
                                if question:
                                    qa_questions.append(question[:80] + "..." if len(question) > 80 else question)
                    
                    print(f"   📊 Content Analysis:")
                    print(f"      📋 Content types: {dict(content_types)}")
                    
                    if law_units:
                        unique_articles = set()
                        for law_unit in law_units:
                            if law_unit:
                                article = law_unit.split('.')[0]
                                unique_articles.add(article)
                        dieu_count = len(unique_articles)
                        khoan_count = len([lu for lu in law_units if lu.count('.') == 1])
                        diem_count = len([lu for lu in law_units if lu.count('.') == 2])
                        
                        print(f"      ⚖️  Legal Structure:")
                        print(f"         - Điều: {dieu_count}")
                        print(f"         - Khoản: {khoan_count}")
                        print(f"         - Điểm: {diem_count}")
                        print(f"         - Sample law units: {law_units[:5]}")
                        print(f"         - Authorities: {list(authorities)}")
                        print(f"         - Doc types: {list(doc_types)}")
                    
                    if qa_questions:
                        print(f"      ❓ Q&A Analysis:")
                        print(f"         - Total Q&A: {len(qa_questions)}")
                        print(f"         - Sample questions:")
                        for j, q in enumerate(qa_questions[:3], 1):
                            print(f"           {j}. {q}")
                    
                    if hasattr(processor, 'extract_simple_references'):
                        print(f"      🔗 Testing Cross-References:")
                        sample_content = documents[0].content if documents else ""
                        refs = processor.extract_simple_references(sample_content)
                        total_refs = sum(len(ref_list) for ref_list in refs.values())
                        print(f"         - Total refs found: {total_refs}")
                        if total_refs > 0:
                            print(f"         - Breakdown: {dict(refs)}")
                    
                    if documents:
                        sample_doc = documents[0]
                        content_preview = sample_doc.content[:200] + "..." if len(sample_doc.content) > 200 else sample_doc.content
                        print(f"      📄 Sample content: {content_preview}")
                        print(f"      🏷️  Sample metadata keys: {list(sample_doc.metadata.keys())}")
                    
                    file_results[file_path.name] = {
                        'chunks': len(documents),
                        'content_types': dict(content_types),
                        'legal_structure': {
                            'dieu': dieu_count if law_units else 0,
                            'khoan': khoan_count if law_units else 0,
                            'diem': diem_count if law_units else 0,
                            'total_law_units': len(law_units)
                        },
                        'qa_count': len(qa_questions),
                        'authorities': list(authorities),
                        'doc_types': list(doc_types),
                        'processing_time': process_time
                    }
                else:
                    print(f"   ❌ No documents created from this file")
                    file_results[file_path.name] = {'chunks': 0, 'error': 'No documents created'}
                    
            except Exception as e:
                print(f"   ❌ Processing failed: {e}")
                file_results[file_path.name] = {'chunks': 0, 'error': str(e)}
        
        print_subsection("Summary Across All Files")
        total_chunks = sum(r.get('chunks', 0) for r in file_results.values())
        total_legal = sum(r.get('legal_structure', {}).get('total_law_units', 0) for r in file_results.values())
        total_qa = sum(r.get('qa_count', 0) for r in file_results.values())
        
        print(f"📊 TOTAL EXTRACTION RESULTS:")
        print(f"   📦 Total chunks: {total_chunks}")
        print(f"   ⚖️  Total law units: {total_legal}")
        print(f"   ❓ Total Q&A: {total_qa}")
        print(f"   📁 Files processed: {len([r for r in file_results.values() if r.get('chunks', 0) > 0])}/{len(file_results)}")
        
        return file_results
        
    except Exception as e:
        print(f"❌ Document processor debug failed: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return {}

def debug_vector_store_files():
    """Debug 2: Check vector store files and analyze full .pkl content"""
    print_section("VECTOR STORE FILES DEBUG")
    
    try:
        from services.vector_rag.rag_config import config
        
        vector_store_path = config.vector_store_path
        print(f"📁 Vector store path: {vector_store_path}")
        
        if not os.path.exists(vector_store_path):
            print(f"❌ Vector store path not found")
            return {}
        
        core_files = {
            "documents.pkl": "Processed documents",
            "metadata.pkl": "Document metadata",
            "faiss_index.bin": "FAISS search index"
        }
        
        log_files = {
            "build_detailed.log": "Detailed build log",
            "build_summary.json": "Build summary JSON"
        }
        
        file_status = {}
        
        print_subsection("Core Vector Store Files")
        for filename, description in core_files.items():
            filepath = os.path.join(vector_store_path, filename)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                size_mb = size / (1024 * 1024)
                mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                print(f"   ✅ {filename}: {size_mb:.2f}MB (modified: {mod_time.strftime('%Y-%m-%d %H:%M')})")
                file_status[filename] = {'exists': True, 'size': size, 'size_mb': size_mb}
                
                if filename.endswith('.pkl'):
                    try:
                        with open(filepath, 'rb') as f:
                            data = pickle.load(f)
                        
                        print(f"      📊 Analyzing {filename} content:")
                        if filename == "documents.pkl":
                            file_status[filename]['document_count'] = len(data)
                            print(f"         - Total documents: {len(data)}")
                            
                            # Analyze document content
                            content_lengths = [len(doc.content) if hasattr(doc, 'content') else len(str(doc)) for doc in data]
                            avg_length = sum(content_lengths) / len(content_lengths) if content_lengths else 0
                            print(f"         - Average content length: {avg_length:.1f} characters")
                            print(f"         - Sample content (first doc):")
                            sample_doc = data[0] if data else None
                            if sample_doc:
                                content_preview = sample_doc.content[:150] + "..." if hasattr(sample_doc, 'content') and len(sample_doc.content) > 150 else sample_doc.content if hasattr(sample_doc, 'content') else str(sample_doc)[:150]
                                print(f"           {content_preview}")
                        
                        elif filename == "metadata.pkl":
                            file_status[filename]['metadata_count'] = len(data)
                            print(f"         - Total metadata entries: {len(data)}")
                            
                            # Analyze metadata structure
                            content_types = {}
                            authorities = {}
                            domains = {}
                            law_units = []
                            for meta in data:
                                ct = meta.get('content_type', 'unknown')
                                content_types[ct] = content_types.get(ct, 0) + 1
                                
                                auth = meta.get('authority_level', 'unknown')
                                authorities[auth] = authorities.get(auth, 0) + 1
                                
                                domain = meta.get('primary_domain', 'unknown')
                                domains[domain] = domains.get(domain, 0) + 1
                                
                                if meta.get('law_unit'):
                                    law_units.append(meta['law_unit'])
                            
                            print(f"         - Content types: {dict(content_types)}")
                            print(f"         - Authorities: {dict(authorities)}")
                            print(f"         - Domains: {dict(domains)}")
                            if law_units:
                                print(f"         - Sample law units: {law_units[:5]}")
                            
                            # Validate metadata keys
                            required_keys = ['content_type', 'source', 'processed_at']
                            missing_keys = []
                            for meta in data:
                                missing = [key for key in required_keys if key not in meta]
                                if missing:
                                    missing_keys.append(f"Metadata entry missing: {missing}")
                            if missing_keys:
                                print(f"         - ⚠️  Missing keys in {len(missing_keys)} entries")
                                file_status[filename]['missing_keys'] = missing_keys[:5]
                            else:
                                print(f"         - ✅ All required metadata keys present")
                            
                            file_status[filename]['content_types'] = dict(content_types)
                            file_status[filename]['authorities'] = dict(authorities)
                            file_status[filename]['domains'] = dict(domains)
                            file_status[filename]['law_unit_count'] = len(law_units)
                    except Exception as e:
                        print(f"      ❌ Failed to read {filename}: {e}")
                        file_status[filename]['error'] = str(e)
                        
            else:
                print(f"   ❌ {filename}: Missing")
                file_status[filename] = {'exists': False}
        
        print_subsection("Build Log Files")
        for filename, description in log_files.items():
            filepath = os.path.join(vector_store_path, filename)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                print(f"   ✅ {filename}: {size:,} bytes")
                
                if filename.endswith('.json'):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            log_data = json.load(f)
                        
                        build_session = log_data.get('build_session', {})
                        print(f"      🕐 Build time: {build_session.get('start_time', 'Unknown')}")
                        print(f"      ✅ Success: {build_session.get('success', False)}")
                        
                        legal_extraction = log_data.get('legal_extraction', {})
                        qa_extraction = log_data.get('qa_extraction', {})
                        
                        print(f"      📊 Extraction Summary:")
                        print(f"         - Legal docs: {legal_extraction.get('documents_processed', 0)}")
                        print(f"         - Articles: {legal_extraction.get('total_articles', 0)}")
                        print(f"         - Q&A docs: {qa_extraction.get('documents_processed', 0)}")
                        print(f"         - Q&A pairs: {qa_extraction.get('total_qa_pairs', 0)}")
                        
                        file_status[filename] = {
                            'exists': True,
                            'build_success': build_session.get('success', False),
                            'legal_extraction': legal_extraction,
                            'qa_extraction': qa_extraction
                        }
                    except Exception as e:
                        print(f"      ❌ Failed to parse JSON: {e}")
                        file_status[filename] = {'exists': True, 'error': str(e)}
            else:
                print(f"   ❌ {filename}: Missing")
                file_status[filename] = {'exists': False}
        
        return file_status
        
    except Exception as e:
        print(f"❌ Vector store debug failed: {e}")
        return {}

def debug_extraction_quality():
    """Debug 4: Check extraction quality with full .pkl content analysis"""
    print_section("EXTRACTION QUALITY DEBUG")
    
    try:
        from services.vector_rag.rag_config import config
        
        vector_store_path = config.vector_store_path
        docs_file = os.path.join(vector_store_path, "documents.pkl")
        meta_file = os.path.join(vector_store_path, "metadata.pkl")
        
        if not (os.path.exists(docs_file) and os.path.exists(meta_file)):
            print("❌ No built vector store found. Run build first.")
            return {}
        
        print_subsection("Loading Built Data")
        
        try:
            with open(docs_file, 'rb') as f:
                documents = pickle.load(f)
            with open(meta_file, 'rb') as f:
                metadata = pickle.load(f)
        except Exception as e:
            print(f"❌ Failed to load .pkl files: {e}")
            return {}
        
        print(f"📊 Loaded {len(documents)} documents with {len(metadata)} metadata entries")
        
        if len(documents) != len(metadata):
            print(f"⚠️  WARNING: Document/metadata count mismatch!")
        
        print_subsection("Content Quality Analysis")
        
        content_types = {}
        legal_stats = {'total_law_units': 0, 'dieu': 0, 'khoan': 0, 'diem': 0}
        qa_stats = {'total_pairs': 0, 'has_questions': 0, 'has_answers': 0}
        authority_dist = {}
        domain_dist = {}
        issues = []
        
        for i, (doc, meta) in enumerate(zip(documents, metadata)):
            content_type = meta.get('content_type', 'unknown')
            content_types[content_type] = content_types.get(content_type, 0) + 1
            
            # Validate document structure
            doc_content = doc.content if hasattr(doc, 'content') else str(doc)
            if not doc_content.strip():
                issues.append(f"Document {i} has empty content")
            
            # Legal document analysis
            if content_type == 'legal_document':
                law_unit = meta.get('law_unit', '')
                if law_unit:
                    legal_stats['total_law_units'] += 1
                    if '.' not in law_unit:
                        legal_stats['dieu'] += 1
                    elif law_unit.count('.') == 1:
                        legal_stats['khoan'] += 1
                    elif law_unit.count('.') == 2:
                        legal_stats['diem'] += 1
                else:
                    issues.append(f"Legal document {i} missing law_unit")
                
                authority = meta.get('authority_level', 'unknown')
                authority_dist[authority] = authority_dist.get(authority, 0) + 1
                
                # Check for missing required metadata
                required_keys = ['doc_id', 'authority_level', 'primary_domain']
                missing_keys = [key for key in required_keys if not meta.get(key)]
                if missing_keys:
                    issues.append(f"Legal document {i} missing metadata keys: {missing_keys}")
            
            # Q&A analysis
            elif content_type == 'qa_entry':
                qa_stats['total_pairs'] += 1
                if meta.get('question'):
                    qa_stats['has_questions'] += 1
                else:
                    issues.append(f"Q&A document {i} missing question")
                if meta.get('answer_preview'):
                    qa_stats['has_answers'] += 1
                else:
                    issues.append(f"Q&A document {i} missing answer")
            
            # Domain analysis
            domain = meta.get('primary_domain', 'unknown')
            domain_dist[domain] = domain_dist.get(domain, 0) + 1
            
            # Content length validation
            if len(doc_content) < 50:
                issues.append(f"Document {i} content too short: {len(doc_content)} characters")
        
        print(f"📋 Content Type Distribution:")
        for ct, count in content_types.items():
            percentage = (count / len(metadata)) * 100 if len(metadata) > 0 else 0
            print(f"   - {ct}: {count} ({percentage:.1f}%)")
        
        print(f"⚖️  Legal Document Quality:")
        print(f"   - Total law units: {legal_stats['total_law_units']}")
        print(f"   - Điều level: {legal_stats['dieu']}")
        print(f"   - Khoản level: {legal_stats['khoan']}")
        print(f"   - Điểm level: {legal_stats['diem']}")
        print(f"   - Authority distribution: {dict(authority_dist)}")
        
        print(f"❓ Q&A Quality:")
        print(f"   - Total Q&A pairs: {qa_stats['total_pairs']}")
        print(f"   - Has questions: {qa_stats['has_questions']}")
        print(f"   - Has answers: {qa_stats['has_answers']}")
        
        print(f"🌐 Domain Distribution:")
        print(f"   - Domains: {dict(domain_dist)}")
        
        if issues:
            print(f"⚠️  Issues Found ({len(issues)}):")
            for issue in issues[:5]:  # Show up to 5 issues
                print(f"      - {issue}")
            if len(issues) > 5:
                print(f"      - ...and {len(issues)-5} more issues")
        
        print_subsection("Content Samples")
        legal_docs = [(i, meta) for i, meta in enumerate(metadata) if meta.get('content_type') == 'legal_document']
        if legal_docs:
            idx, meta = legal_docs[0]
            content = documents[idx].content if idx < len(documents) and hasattr(documents[idx], 'content') else str(documents[idx])
            print(f"📜 Legal Document Sample:")
            print(f"   Law unit: {meta.get('law_unit', 'N/A')}")
            print(f"   Authority: {meta.get('authority_level', 'N/A')}")
            print(f"   Content preview: {content[:150]}..." if len(content) > 150 else content)
        
        qa_docs = [(i, meta) for i, meta in enumerate(metadata) if meta.get('content_type') == 'qa_entry']
        if qa_docs:
            idx, meta = qa_docs[0]
            content = documents[idx].content if idx < len(documents) and hasattr(documents[idx], 'content') else str(documents[idx])
            print(f"❓ Q&A Sample:")
            print(f"   Question: {meta.get('question', 'N/A')[:100]}...")
            print(f"   Answer preview: {meta.get('answer_preview', 'N/A')[:100]}...")
            print(f"   Content preview: {content[:150]}..." if len(content) > 150 else content)
        
        return {
            'total_documents': len(documents),
            'total_metadata': len(metadata),
            'content_types': dict(content_types),
            'legal_stats': legal_stats,
            'qa_stats': qa_stats,
            'authority_distribution': dict(authority_dist),
            'domain_distribution': dict(domain_dist),
            'data_consistent': len(documents) == len(metadata),
            'issues': issues
        }
        
    except Exception as e:
        print(f"❌ Extraction quality debug failed: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return {}

def generate_debug_summary(all_results):
    """Generate comprehensive debug summary"""
    print_section("🎯 COMPREHENSIVE DEBUG SUMMARY")
    
    doc_results = all_results.get('document_processing', {})
    if doc_results:
        print_subsection("📄 Document Processing Status")
        total_files = len(doc_results)
        successful_files = len([r for r in doc_results.values() if r.get('chunks', 0) > 0])
        total_chunks = sum(r.get('chunks', 0) for r in doc_results.values())
        total_legal_units = sum(r.get('legal_structure', {}).get('total_law_units', 0) for r in doc_results.values())
        total_qa = sum(r.get('qa_count', 0) for r in doc_results.values())
        
        print(f"   📊 Files: {successful_files}/{total_files} processed successfully")
        print(f"   📦 Total chunks: {total_chunks}")
        print(f"   ⚖️  Legal units extracted: {total_legal_units}")
        print(f"   ❓ Q&A pairs extracted: {total_qa}")
        
        if total_chunks == 0:
            print(f"   🚨 CRITICAL: No content extracted from any files!")
        elif total_legal_units == 0 and total_qa == 0:
            print(f"   ⚠️  WARNING: No structured content (legal/Q&A) extracted!")
        else:
            print(f"   ✅ Content extraction successful")
    
    vector_results = all_results.get('vector_store', {})
    if vector_results:
        print_subsection("💾 Vector Store Status")
        core_files = ['documents.pkl', 'metadata.pkl', 'faiss_index.bin']
        files_exist = [vector_results.get(f, {}).get('exists', False) for f in core_files]
        
        print(f"   📁 Core files: {sum(files_exist)}/{len(core_files)} exist")
        
        if all(files_exist):
            docs_count = vector_results.get('documents.pkl', {}).get('document_count', 0)
            meta_count = vector_results.get('metadata.pkl', {}).get('metadata_count', 0)
            print(f"   📊 Documents: {docs_count}, Metadata: {meta_count}")
            
            if docs_count != meta_count:
                print(f"   🚨 CRITICAL: Document/metadata count mismatch!")
            else:
                print(f"   ✅ Vector store data consistent")
                
            # Additional .pkl analysis
            if 'metadata.pkl' in vector_results and vector_results['metadata.pkl'].get('exists'):
                print(f"   📋 Metadata Analysis:")
                print(f"      - Content types: {vector_results['metadata.pkl'].get('content_types', {})}")
                print(f"      - Authorities: {vector_results['metadata.pkl'].get('authorities', {})}")
                print(f"      - Domains: {vector_results['metadata.pkl'].get('domains', {})}")
                if vector_results['metadata.pkl'].get('missing_keys'):
                    print(f"      - ⚠️  Missing metadata keys in {len(vector_results['metadata.pkl']['missing_keys'])} entries")
        else:
            print(f"   ❌ Incomplete vector store - missing core files")
    
    build_results = all_results.get('build_process', {})
    if build_results:
        print_subsection("🔨 Build System Status")
        config_valid = build_results.get('config_valid', False)
        builder_ready = build_results.get('builder_ready', False)
        
        print(f"   ⚙️  Configuration: {'✅ Valid' if config_valid else '❌ Invalid'}")
        print(f"   🏗️  Builder: {'✅ Ready' if builder_ready else '❌ Not Ready'}")
        
        paths_status = build_results.get('paths_status', {})
        for path_name, status in paths_status.items():
            exists = status.get('exists', False)
            files = status.get('files', 0)
            print(f"   📁 {path_name}: {'✅' if exists else '❌'} ({files} files)")
    
    quality_results = all_results.get('extraction_quality', {})
    if quality_results:
        print_subsection("🔍 Extraction Quality Assessment")
        total_docs = quality_results.get('total_documents', 0)
        data_consistent = quality_results.get('data_consistent', False)
        
        print(f"   📊 Total processed: {total_docs} documents")
        print(f"   🔄 Data consistency: {'✅ OK' if data_consistent else '❌ MISMATCH'}")
        
        content_types = quality_results.get('content_types', {})
        legal_stats = quality_results.get('legal_stats', {})
        qa_stats = quality_results.get('qa_stats', {})
        
        print(f"   📋 Content breakdown:")
        for ct, count in content_types.items():
            percentage = (count / total_docs) * 100 if total_docs > 0 else 0
            print(f"      - {ct}: {count} ({percentage:.1f}%)")
        
        if legal_stats.get('total_law_units', 0) > 0:
            print(f"   ⚖️  Legal structure: {legal_stats['dieu']} Điều, {legal_stats['khoan']} Khoản, {legal_stats['diem']} Điểm")
        
        if qa_stats.get('total_pairs', 0) > 0:
            print(f"   ❓ Q&A quality: {qa_stats['has_questions']}/{qa_stats['total_pairs']} have questions")
        
        if quality_results.get('issues'):
            print(f"   ⚠️  Issues found: {len(quality_results['issues'])}")
            for issue in quality_results['issues'][:5]:
                print(f"      - {issue}")
            if len(quality_results['issues']) > 5:
                print(f"      - ...and {len(quality_results['issues'])-5} more issues")
    
    print_subsection("🎯 Overall System Assessment")
    issues = []
    recommendations = []
    
    if doc_results and sum(r.get('chunks', 0) for r in doc_results.values()) == 0:
        issues.append("No content extracted from documents")
        recommendations.append("Check document processor and file formats")
    
    if vector_results:
        core_files = ['documents.pkl', 'metadata.pkl', 'faiss_index.bin']
        missing_files = [f for f in core_files if not vector_results.get(f, {}).get('exists', False)]
        if missing_files:
            issues.append(f"Missing vector store files: {missing_files}")
            recommendations.append("Run build command to create vector database")
    
    if quality_results and not quality_results.get('data_consistent', True):
        issues.append("Data consistency problems in vector store")
        recommendations.append("Rebuild vector database to fix consistency")
    
    if quality_results.get('issues'):
        issues.extend(quality_results['issues'][:3])  # Include top 3 issues from quality check
    
    if not issues:
        issues.append("System appears healthy")
        recommendations.append("Ready for production use")
    
    print(f"   🚨 Issues found: {len([i for i in issues if not i.startswith('System appears')])}")
    for issue in issues:
        icon = "✅" if issue.startswith("System appears") else "❌"
        print(f"      {icon} {issue}")
    
    print(f"   💡 Recommendations:")
    for rec in recommendations:
        print(f"      💡 {rec}")

def main():
    """Main debug execution"""
    print(f"🔍 RAG SYSTEM EXTRACT DEBUG")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Working directory: {os.getcwd()}")
    
    all_results = {}
    
    try:
        all_results['document_processing'] = debug_document_processor()
        all_results['vector_store'] = debug_vector_store_files()
        all_results['build_process'] = debug_build_process()
        all_results['extraction_quality'] = debug_extraction_quality()
        
        generate_debug_summary(all_results)
        
    except Exception as e:
        print(f"❌ Debug execution failed: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
    
    print(f"\n🏁 Debug completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()