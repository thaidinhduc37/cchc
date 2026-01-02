# app/server/services/vector_rag/debug/debug_vector_store.py
"""
🔍 VECTOR STORE DATA INSPECTOR
🎯 Kiểm tra toàn bộ dữ liệu trong vector store
📋 Inspect: documents.pkl, metadata.pkl, faiss_index.bin
📊 Export detailed analysis về nội dung data
"""

import sys
import os
import pickle
import json
from pathlib import Path
from datetime import datetime
import logging

# Add parent to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

# Try import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# Try import numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from app.services.vector_rag.rag_config import config

class VectorStoreInspector:
    """Inspector toàn diện cho Vector Store data"""
    
    def __init__(self):
        # Paths
        self.vector_store_path = Path(config.vector_store_path)
        self.documents_path = Path(config.documents_path)
        
        # Files to inspect
        self.files = {
            'documents': self.vector_store_path / "documents.pkl",
            'metadata': self.vector_store_path / "metadata.pkl", 
            'faiss_index': self.vector_store_path / "faiss_index.bin"
        }
        
        # Log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = Path("app/services/vector_rag") / f"vector_store_inspection_{timestamp}.log"
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Data storage
        self.data = {}
        self.stats = {}
        self.issues = []
    
    def log(self, message, level="INFO"):
        """Log to both console and file"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {level}: {message}"
        print(log_line)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + "\n")
    
    def inspect_all(self):
        """Inspect toàn bộ vector store"""
        self.log("🔍 VECTOR STORE COMPREHENSIVE INSPECTION", "HEADER")
        self.log("=" * 80, "HEADER")
        
        # 1. Check directories and files
        self._check_directory_structure()
        
        # 2. Inspect each file
        self._inspect_documents_file()
        self._inspect_metadata_file()
        self._inspect_faiss_index()
        
        # 3. Cross-validation
        self._cross_validate_data()
        
        # 4. Content analysis
        self._analyze_content_quality()
        
        # 5. Search relevance test
        self._test_search_relevance()
        
        # 6. Generate summary report
        self._generate_summary_report()
        
        self.log(f"\n✅ Inspection completed! Full report: {self.log_file}", "SUCCESS")
    
    def _check_directory_structure(self):
        """Check directory structure and file existence"""
        self.log("\n1️⃣ DIRECTORY STRUCTURE CHECK", "SECTION")
        self.log("-" * 50)
        
        # Check base directories
        self.log(f"📁 Vector store path: {self.vector_store_path}")
        self.log(f"   Exists: {self.vector_store_path.exists()}")
        
        self.log(f"📁 Documents path: {self.documents_path}")
        self.log(f"   Exists: {self.documents_path.exists()}")
        
        # Check each file
        for file_type, file_path in self.files.items():
            self.log(f"\n📄 {file_type.upper()} FILE:")
            self.log(f"   Path: {file_path}")
            self.log(f"   Exists: {file_path.exists()}")
            
            if file_path.exists():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                self.log(f"   Size: {size_mb:.2f} MB")
                self.log(f"   Modified: {modified}")
            else:
                self.issues.append(f"Missing file: {file_path}")
                self.log(f"   ❌ FILE MISSING", "ERROR")
    
    def _inspect_documents_file(self):
        """Inspect documents.pkl file"""
        self.log("\n2️⃣ DOCUMENTS.PKL INSPECTION", "SECTION")
        self.log("-" * 50)
        
        docs_file = self.files['documents']
        
        if not docs_file.exists():
            self.log("❌ documents.pkl not found", "ERROR")
            return
        
        try:
            with open(docs_file, 'rb') as f:
                documents = pickle.load(f)
            
            self.data['documents'] = documents
            
            # Basic stats
            total_docs = len(documents)
            self.log(f"📊 Total documents: {total_docs}")
            
            if total_docs == 0:
                self.issues.append("No documents found in documents.pkl")
                self.log("❌ No documents found", "ERROR")
                return
            
            # Document length analysis
            doc_lengths = [len(doc) for doc in documents if isinstance(doc, str)]
            
            if doc_lengths:
                avg_length = sum(doc_lengths) / len(doc_lengths)
                min_length = min(doc_lengths)
                max_length = max(doc_lengths)
                
                self.log(f"📏 Document lengths:")
                self.log(f"   Average: {avg_length:.1f} chars")
                self.log(f"   Min: {min_length} chars")
                self.log(f"   Max: {max_length} chars")
                
                # Length distribution
                short_docs = sum(1 for length in doc_lengths if length < 100)
                medium_docs = sum(1 for length in doc_lengths if 100 <= length < 1000)
                long_docs = sum(1 for length in doc_lengths if length >= 1000)
                
                self.log(f"📊 Length distribution:")
                self.log(f"   Short (<100): {short_docs} ({short_docs/total_docs*100:.1f}%)")
                self.log(f"   Medium (100-1000): {medium_docs} ({medium_docs/total_docs*100:.1f}%)")
                self.log(f"   Long (>1000): {long_docs} ({long_docs/total_docs*100:.1f}%)")
            
            # Content type analysis
            legal_docs = sum(1 for doc in documents if 'điều' in doc.lower())
            qa_docs = sum(1 for doc in documents if any(keyword in doc.lower() for keyword in ['câu hỏi', 'trả lời', 'hỏi:', 'đáp:']))
            procedure_docs = sum(1 for doc in documents if any(keyword in doc.lower() for keyword in ['thủ tục', 'hồ sơ', 'quy trình']))
            
            self.log(f"📋 Content type analysis:")
            self.log(f"   Legal docs (có 'điều'): {legal_docs} ({legal_docs/total_docs*100:.1f}%)")
            self.log(f"   Q&A docs: {qa_docs} ({qa_docs/total_docs*100:.1f}%)")
            self.log(f"   Procedure docs: {procedure_docs} ({procedure_docs/total_docs*100:.1f}%)")
            
            # ALL DOCUMENTS - FULL DUMP
            self.log(f"\n📝 ALL DOCUMENTS FULL DUMP:")
            self.log("="*80)
            for i, doc in enumerate(documents):
                self.log(f"\n📄 DOCUMENT {i+1}/{total_docs}:")
                self.log(f"   Length: {len(doc)} chars")
                self.log(f"   Full content:")
                self.log(f"   {'-'*60}")
                self.log(f"   {doc}")
                self.log(f"   {'-'*60}")
                
                # Check for legal references
                legal_refs = []
                import re
                article_matches = re.findall(r'điều\s+(\d+)', doc.lower())
                if article_matches:
                    legal_refs.extend([f"Điều {art}" for art in article_matches])
                
                if legal_refs:
                    self.log(f"   Legal refs: {', '.join(legal_refs)}")
                else:
                    self.log(f"   Legal refs: None")
                
                # Add separator
                self.log(f"\n{'='*80}")
            
            self.log(f"\n✅ DUMPED ALL {total_docs} DOCUMENTS")
            
            # Store stats
            self.stats['documents'] = {
                'total': total_docs,
                'avg_length': avg_length if doc_lengths else 0,
                'legal_docs': legal_docs,
                'qa_docs': qa_docs,
                'procedure_docs': procedure_docs
            }
            
        except Exception as e:
            self.issues.append(f"Error reading documents.pkl: {e}")
            self.log(f"❌ Error reading documents.pkl: {e}", "ERROR")
    
    def _inspect_metadata_file(self):
        """Inspect metadata.pkl file"""
        self.log("\n3️⃣ METADATA.PKL INSPECTION", "SECTION")
        self.log("-" * 50)
        
        meta_file = self.files['metadata']
        
        if not meta_file.exists():
            self.log("❌ metadata.pkl not found", "ERROR")
            return
        
        try:
            with open(meta_file, 'rb') as f:
                metadata = pickle.load(f)
            
            self.data['metadata'] = metadata
            
            # Basic stats
            total_meta = len(metadata)
            self.log(f"📊 Total metadata entries: {total_meta}")
            
            if total_meta == 0:
                self.issues.append("No metadata found in metadata.pkl")
                self.log("❌ No metadata found", "ERROR")
                return
            
            # Check consistency with documents
            if 'documents' in self.data:
                docs_count = len(self.data['documents'])
                if total_meta != docs_count:
                    self.issues.append(f"Metadata count ({total_meta}) != Documents count ({docs_count})")
                    self.log(f"⚠️  Metadata count mismatch: {total_meta} vs {docs_count}", "WARNING")
                else:
                    self.log(f"✅ Metadata count matches documents count")
            
            # Analyze metadata structure
            if metadata:
                sample_meta = metadata[0]
                self.log(f"📋 Metadata structure (first entry):")
                self.log(f"   Type: {type(sample_meta)}")
                
                if isinstance(sample_meta, dict):
                    self.log(f"   Keys: {list(sample_meta.keys())}")
                    
                    # Content type analysis
                    content_types = {}
                    for meta in metadata:
                        if isinstance(meta, dict):
                            content_type = meta.get('content_type', 'unknown')
                            content_types[content_type] = content_types.get(content_type, 0) + 1
                    
                    self.log(f"📊 Content types distribution:")
                    for content_type, count in content_types.items():
                        percentage = count / total_meta * 100
                        self.log(f"   {content_type}: {count} ({percentage:.1f}%)")
                    
                    # Source analysis
                    sources = {}
                    for meta in metadata:
                        if isinstance(meta, dict):
                            source = meta.get('source', 'unknown')
                            sources[source] = sources.get(source, 0) + 1
                    
                    if len(sources) <= 10:  # Only show if reasonable number
                        self.log(f"📁 Source files distribution:")
                        for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
                            percentage = count / total_meta * 100
                            self.log(f"   {source}: {count} ({percentage:.1f}%)")
                
            # ALL METADATA - FULL DUMP
            self.log(f"\n📝 ALL METADATA FULL DUMP:")
            self.log("="*80)
            for i, meta in enumerate(metadata):
                self.log(f"\n📋 METADATA {i+1}/{total_meta}:")
                self.log(f"   {json.dumps(meta, ensure_ascii=False, indent=4)}")
                self.log(f"   {'-'*60}")
            
            self.log(f"\n✅ DUMPED ALL {total_meta} METADATA ENTRIES")
            
            # Store stats
            self.stats['metadata'] = {
                'total': total_meta,
                'content_types': content_types if 'content_types' in locals() else {},
                'sources': sources if 'sources' in locals() else {}
            }
            
        except Exception as e:
            self.issues.append(f"Error reading metadata.pkl: {e}")
            self.log(f"❌ Error reading metadata.pkl: {e}", "ERROR")
    
    def _inspect_faiss_index(self):
        """Inspect FAISS index file"""
        self.log("\n4️⃣ FAISS INDEX INSPECTION", "SECTION")
        self.log("-" * 50)
        
        if not FAISS_AVAILABLE:
            self.log("❌ FAISS not available - cannot inspect index", "ERROR")
            return
        
        index_file = self.files['faiss_index']
        
        if not index_file.exists():
            self.log("❌ faiss_index.bin not found", "ERROR")
            return
        
        try:
            # Load FAISS index
            index = faiss.read_index(str(index_file))
            self.data['faiss_index'] = index
            
            # Basic stats
            self.log(f"📊 FAISS Index stats:")
            self.log(f"   Total vectors: {index.ntotal}")
            self.log(f"   Dimension: {index.d}")
            self.log(f"   Index type: {type(index).__name__}")
            
            # Check if trained
            self.log(f"   Is trained: {index.is_trained}")
            
            # Check consistency with documents
            if 'documents' in self.data:
                docs_count = len(self.data['documents'])
                if index.ntotal != docs_count:
                    self.issues.append(f"FAISS vectors ({index.ntotal}) != Documents count ({docs_count})")
                    self.log(f"⚠️  Vector count mismatch: {index.ntotal} vs {docs_count}", "WARNING")
                else:
                    self.log(f"✅ Vector count matches documents count")
            
            # Test index functionality
            self.log(f"\n🧪 Testing FAISS index functionality:")
            
            if index.ntotal > 0 and NUMPY_AVAILABLE:
                try:
                    # Create a test query vector
                    test_vector = np.random.random((1, index.d)).astype(np.float32)
                    
                    # Test search
                    k = min(5, index.ntotal)
                    distances, indices = index.search(test_vector, k)
                    
                    self.log(f"   ✅ Search test successful")
                    self.log(f"   Retrieved {len(indices[0])} results")
                    self.log(f"   Distances: {distances[0].tolist()}")
                    self.log(f"   Indices: {indices[0].tolist()}")
                    
                except Exception as search_error:
                    self.issues.append(f"FAISS search test failed: {search_error}")
                    self.log(f"   ❌ Search test failed: {search_error}", "ERROR")
            
            # Store stats
            self.stats['faiss_index'] = {
                'total_vectors': index.ntotal,
                'dimension': index.d,
                'index_type': type(index).__name__,
                'is_trained': index.is_trained
            }
            
        except Exception as e:
            self.issues.append(f"Error reading FAISS index: {e}")
            self.log(f"❌ Error reading FAISS index: {e}", "ERROR")
    
    def _cross_validate_data(self):
        """Cross-validate data consistency"""
        self.log("\n5️⃣ CROSS-VALIDATION", "SECTION")
        self.log("-" * 50)
        
        # Check if all three components exist and are consistent
        docs_count = len(self.data.get('documents', []))
        meta_count = len(self.data.get('metadata', []))
        vector_count = self.data['faiss_index'].ntotal if 'faiss_index' in self.data else 0
        
        self.log(f"📊 Count comparison:")
        self.log(f"   Documents: {docs_count}")
        self.log(f"   Metadata: {meta_count}")
        self.log(f"   Vectors: {vector_count}")
        
        # Check consistency
        if docs_count == meta_count == vector_count and docs_count > 0:
            self.log(f"✅ All counts match perfectly!")
        else:
            issues = []
            if docs_count != meta_count:
                issues.append(f"Documents ({docs_count}) != Metadata ({meta_count})")
            if docs_count != vector_count:
                issues.append(f"Documents ({docs_count}) != Vectors ({vector_count})")
            if meta_count != vector_count:
                issues.append(f"Metadata ({meta_count}) != Vectors ({vector_count})")
            
            for issue in issues:
                self.issues.append(f"Count mismatch: {issue}")
                self.log(f"❌ {issue}", "ERROR")
        
        # Store validation results
        self.stats['validation'] = {
            'docs_count': docs_count,
            'meta_count': meta_count, 
            'vector_count': vector_count,
            'all_match': docs_count == meta_count == vector_count,
            'total_issues': len(self.issues)
        }
    
    def _analyze_content_quality(self):
        """Analyze content quality for search relevance"""
        self.log("\n6️⃣ CONTENT QUALITY ANALYSIS", "SECTION")
        self.log("-" * 50)
        
        if 'documents' not in self.data:
            self.log("❌ No documents to analyze", "ERROR")
            return
        
        documents = self.data['documents']
        
        # COMPREHENSIVE ANALYSIS
        self.log(f"\n🔍 COMPREHENSIVE CONTENT ANALYSIS:")
        self.log("="*80)
        
        if 'documents' not in self.data:
            self.log("❌ No documents to analyze", "ERROR")
            return
        
        documents = self.data['documents']
        
        # Legal content analysis
        legal_articles = []
        legal_keywords = ['điều', 'khoản', 'điểm', 'luật', 'nghị định']
        procedure_keywords = ['thủ tục', 'hồ sơ', 'quy trình', 'lệ phí']
        
        legal_score = 0
        procedure_score = 0
        qa_score = 0
        
        # DETAILED ARTICLE MAPPING
        article_mapping = {}
        
        for i, doc in enumerate(documents):
            doc_lower = doc.lower()
            
            # Find all legal articles in this document
            import re
            articles = re.findall(r'điều\s+(\d+)', doc_lower)
            for article in articles:
                if article not in article_mapping:
                    article_mapping[article] = []
                article_mapping[article].append({
                    'doc_index': i,
                    'content': doc,
                    'preview': doc[:100] + "..."
                })
            
            legal_articles.extend(articles)
            
            # Score content types
            if any(keyword in doc_lower for keyword in legal_keywords):
                legal_score += 1
            
            if any(keyword in doc_lower for keyword in procedure_keywords):
                procedure_score += 1
                
            if any(keyword in doc_lower for keyword in ['câu hỏi', 'trả lời']):
                qa_score += 1
        
        total_docs = len(documents)
        
        self.log(f"📊 Content quality metrics:")
        self.log(f"   Legal content: {legal_score}/{total_docs} ({legal_score/total_docs*100:.1f}%)")
        self.log(f"   Procedure content: {procedure_score}/{total_docs} ({procedure_score/total_docs*100:.1f}%)")
        self.log(f"   Q&A content: {qa_score}/{total_docs} ({qa_score/total_docs*100:.1f}%)")
        
        # DETAILED ARTICLE MAPPING
        unique_articles = list(set(legal_articles))
        self.log(f"\n📜 DETAILED LEGAL ARTICLES MAPPING:")
        self.log(f"   Total unique articles: {len(unique_articles)}")
        
        # Sort articles numerically
        try:
            unique_articles_sorted = sorted(unique_articles, key=int)
        except:
            unique_articles_sorted = sorted(unique_articles)
        
        for article in unique_articles_sorted:
            docs_with_article = article_mapping.get(article, [])
            self.log(f"\n   📜 ĐIỀU {article}: Found in {len(docs_with_article)} documents")
            
            for j, doc_info in enumerate(docs_with_article):
                self.log(f"      [{j+1}] Document {doc_info['doc_index']+1}:")
                self.log(f"          Preview: {doc_info['preview']}")
                self.log(f"          Full content:")
                self.log(f"          {'-'*50}")
                self.log(f"          {doc_info['content']}")
                self.log(f"          {'-'*50}")
        
        # SPECIFIC ARTICLE SEARCH
        important_articles = ['6', '15', '21', '30', '31', '36']
        self.log(f"\n🎯 IMPORTANT ARTICLES CHECK:")
        for article in important_articles:
            if article in article_mapping:
                count = len(article_mapping[article])
                self.log(f"   ✅ Điều {article}: Found in {count} documents")
            else:
                self.log(f"   ❌ Điều {article}: NOT FOUND")
        
        # Store quality stats
        self.stats['content_quality'] = {
            'legal_score': legal_score,
            'procedure_score': procedure_score,
            'qa_score': qa_score,
            'unique_articles': len(unique_articles),
            'articles_found': unique_articles_sorted,
            'article_mapping': {k: len(v) for k, v in article_mapping.items()}
        }
    
    def _test_search_relevance(self):
        """Test search relevance với sample queries"""
        self.log("\n7️⃣ SEARCH RELEVANCE TEST", "SECTION")
        self.log("-" * 50)
        
        if not all(key in self.data for key in ['documents', 'faiss_index']):
            self.log("❌ Missing data for search test", "ERROR")
            return
        
        test_queries = [
            "Điều 15 quy định gì",
            "thủ tục làm hộ chiếu",
            "trẻ em xuất cảnh",
            "lệ phí hộ chiếu",
            "được xuất cảnh không"
        ]
        
        # Simple embedding (fallback if no embedding available)
        # FULL SEARCH RELEVANCE TEST với tất cả documents
        self.log("\n🔍 FULL SEARCH RELEVANCE TEST - ALL DOCUMENTS")
        self.log("="*80)
        
        test_queries = [
            "Điều 6 quy định gì",
            "Điều 15 quy định gì", 
            "Điều 21 quy định gì",
            "Điều 30 quy định gì",
            "Điều 31 quy định gì",
            "Điều 36 quy định gì",
            "xuất cảnh bằng hộ chiếu nào",
            "thủ tục làm hộ chiếu",
            "trường hợp nào bị từ chối cấp hộ chiếu",
            "thẩm quyền thu hồi hộ chiếu",
            "người có hai quốc tịch",
            "trẻ em xuất cảnh",
            "lệ phí hộ chiếu",
            "được xuất cảnh không",
            "bị khởi tố có được xuất cảnh không",
            "ân xá có được xuất cảnh không"
        ]
        
        if 'documents' not in self.data:
            self.log("❌ No documents to analyze", "ERROR")
            return
        
        documents = self.data['documents']
        
        for query in test_queries:
            self.log(f"\n🔍 TESTING QUERY: '{query}'")
            self.log("-"*60)
            
            # Simple keyword matching for relevance check
            query_lower = query.lower()
            relevant_docs = []
            
            for i, doc in enumerate(documents):
                doc_lower = doc.lower()
                
                # Enhanced relevance scoring
                score = 0
                query_words = query_lower.split()
                
                # Exact phrase matching (higher score)
                if query_lower in doc_lower:
                    score += 10
                
                # Individual word matching
                for word in query_words:
                    if len(word) > 2:  # Skip short words
                        count = doc_lower.count(word)
                        score += count
                
                # Legal article exact matching
                import re
                if "điều" in query_lower:
                    article_match = re.search(r'điều\s+(\d+)', query_lower)
                    if article_match:
                        target_article = article_match.group(1)
                        if f"điều {target_article}" in doc_lower:
                            score += 20  # High boost for exact article match
                
                if score > 0:
                    relevant_docs.append((i, score, doc))
            
            # Sort by relevance
            relevant_docs.sort(key=lambda x: x[1], reverse=True)
            
            self.log(f"   📊 Found {len(relevant_docs)} potentially relevant docs")
            
            # Show ALL relevant documents for thorough analysis
            if relevant_docs:
                self.log(f"   📋 ALL RELEVANT DOCUMENTS:")
                for j, (doc_idx, score, doc_content) in enumerate(relevant_docs):
                    self.log(f"\n   [{j+1}] Document {doc_idx+1}, Relevance Score: {score}")
                    self.log(f"       Full content:")
                    self.log(f"       {'-'*50}")
                    self.log(f"       {doc_content}")
                    self.log(f"       {'-'*50}")
            else:
                self.log(f"   ❌ NO RELEVANT DOCUMENTS FOUND!")
            
            self.log(f"\n{'='*80}")
    
    def _generate_summary_report(self):
        """Generate final summary report"""
        self.log("\n8️⃣ SUMMARY REPORT", "SECTION")
        self.log("=" * 50)
        
        # Overall status
        if not self.issues:
            self.log("🎉 VECTOR STORE STATUS: HEALTHY", "SUCCESS")
        else:
            self.log(f"⚠️  VECTOR STORE STATUS: {len(self.issues)} ISSUES FOUND", "WARNING")
        
        # Quick stats
        self.log(f"\n📊 QUICK STATS:")
        if 'documents' in self.stats:
            self.log(f"   📄 Documents: {self.stats['documents']['total']}")
            self.log(f"   📋 Legal docs: {self.stats['documents']['legal_docs']}")
            self.log(f"   ❓ Q&A docs: {self.stats['documents']['qa_docs']}")
        
        if 'faiss_index' in self.stats:
            self.log(f"   🧮 Vectors: {self.stats['faiss_index']['total_vectors']}")
            self.log(f"   📐 Dimension: {self.stats['faiss_index']['dimension']}")
        
        # Issues summary
        if self.issues:
            self.log(f"\n❌ ISSUES FOUND ({len(self.issues)}):")
            for i, issue in enumerate(self.issues, 1):
                self.log(f"   {i}. {issue}")
        
        # Recommendations
        self.log(f"\n💡 RECOMMENDATIONS:")
        
        if not self.issues:
            self.log("   ✅ Vector store is in good condition")
            self.log("   ✅ All components are consistent")
            self.log("   ✅ Ready for RAG operations")
        else:
            if any('Missing file' in issue for issue in self.issues):
                self.log("   🔧 Rebuild vector store - missing files detected")
            
            if any('mismatch' in issue.lower() for issue in self.issues):
                self.log("   🔧 Re-index data - count mismatches detected")
            
            if 'documents' in self.stats and self.stats['documents']['total'] < 100:
                self.log("   📚 Add more documents - current dataset is small")
        
        # Export detailed JSON report
        json_report = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy' if not self.issues else 'issues_found',
            'stats': self.stats,
            'issues': self.issues,
            'files_checked': {k: str(v) for k, v in self.files.items()},
            'availability': {
                'faiss': FAISS_AVAILABLE,
                'numpy': NUMPY_AVAILABLE
            }
        }
        
        json_file = self.log_file.with_suffix('.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_report, f, ensure_ascii=False, indent=2)
        
        self.log(f"\n📄 Detailed JSON report: {json_file}")
        
        # Final status
        self.log(f"\n{'='*50}")
        if not self.issues:
            self.log("🎯 VECTOR STORE IS READY FOR RAG OPERATIONS", "SUCCESS")
        else:
            self.log("🚨 VECTOR STORE NEEDS ATTENTION BEFORE USE", "WARNING")

def main():
    """Main inspection function"""
    print("🔍 Starting Vector Store Data Inspection...")
    
    inspector = VectorStoreInspector()
    inspector.inspect_all()
    
    print(f"\n✅ Inspection completed!")
    print(f"📄 Log file: {inspector.log_file}")
    print(f"📊 JSON report: {inspector.log_file.with_suffix('.json')}")

if __name__ == "__main__":
    main()