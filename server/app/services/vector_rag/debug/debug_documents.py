# Test Extract Content từ Văn bản Pháp luật Thực tế
"""
🧪 TEST: Kiểm tra extraction với văn bản pháp luật thực tế
- Luật 49/2019/QH14 về Xuất nhập cảnh
- Thông tư 31/2023/TT-BCA
- Nghị định 77/2020/NĐ-CP
"""
import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.vector_rag.document_processor import DocumentProcessor
from services.vector_rag.rag_config import config

@dataclass
class ContentAnalysis:
    """Phân tích nội dung văn bản"""
    file_name: str
    total_chars: int
    total_paragraphs: int
    
    # Legal structure
    articles_found: int
    chapters_found: int  
    sections_found: int
    
    # Content types
    preamble_chars: int
    articles_chars: int
    appendix_chars: int
    
    # Processing results
    chunks_created: int
    processed_chars: int
    preservation_ratio: float
    
    # Issues
    issues: List[str]

def analyze_real_legal_documents():
    """Test với văn bản pháp luật thực tế"""
    
    print("🏛️ TESTING REAL LEGAL DOCUMENTS EXTRACTION")
    print("=" * 60)
    
    processor = DocumentProcessor()
    
    # Find DOCX files
    docx_files = list(Path(config.documents_path).rglob('*.docx'))
    
    if not docx_files:
        print("❌ No DOCX files found. Please add legal documents to test.")
        return create_sample_test()
    
    print(f"📁 Found {len(docx_files)} DOCX files")
    
    results = []
    
    for file_path in docx_files:
        print(f"\n{'='*40}")
        print(f"📄 ANALYZING: {file_path.name}")
        print(f"{'='*40}")
        
        try:
            analysis = analyze_single_document(processor, str(file_path))
            results.append(analysis)
            print_analysis_results(analysis)
            
        except Exception as e:
            print(f"❌ Error analyzing {file_path.name}: {e}")
    
    # Overall summary
    if results:
        print_overall_summary(results)
    
    return results

def analyze_single_document(processor: DocumentProcessor, file_path: str) -> ContentAnalysis:
    """Phân tích chi tiết một văn bản"""
    
    file_name = os.path.basename(file_path)
    issues = []
    
    # STEP 1: Extract raw content
    print("🔍 Step 1: Extracting raw DOCX content...")
    raw_content = processor._extract_docx_content(file_path)
    
    if not raw_content:
        issues.append("Could not extract any content from DOCX")
        return ContentAnalysis(
            file_name=file_name, total_chars=0, total_paragraphs=0,
            articles_found=0, chapters_found=0, sections_found=0,
            preamble_chars=0, articles_chars=0, appendix_chars=0,
            chunks_created=0, processed_chars=0, preservation_ratio=0.0,
            issues=issues
        )
    
    # STEP 2: Analyze raw content structure
    print("📊 Step 2: Analyzing document structure...")
    content_analysis = analyze_content_structure(raw_content)
    
    # STEP 3: Test document classification
    print("🔖 Step 3: Testing document classification...")
    doc_type, confidence = processor._classify_document_with_confidence(raw_content)
    print(f"   📋 Classified as: {doc_type} (confidence: {confidence:.2f})")
    
    # STEP 4: Process through processor
    print("⚙️ Step 4: Processing through document processor...")
    processed_docs = processor.process_file(file_path)
    
    # STEP 5: Analyze what was preserved/lost
    print("📈 Step 5: Analyzing preservation...")
    preservation_analysis = analyze_preservation(raw_content, processed_docs, content_analysis)
    
    return ContentAnalysis(
        file_name=file_name,
        total_chars=len(raw_content),
        total_paragraphs=len(raw_content.split('\n\n')),
        articles_found=content_analysis['articles'],
        chapters_found=content_analysis['chapters'],
        sections_found=content_analysis['sections'],
        preamble_chars=content_analysis['preamble_chars'],
        articles_chars=content_analysis['articles_chars'],
        appendix_chars=content_analysis['appendix_chars'],
        chunks_created=len(processed_docs),
        processed_chars=sum(len(doc.content) for doc in processed_docs),
        preservation_ratio=preservation_analysis['ratio'],
        issues=preservation_analysis['issues']
    )

def analyze_content_structure(content: str) -> Dict[str, Any]:
    """Phân tích cấu trúc nội dung chi tiết"""
    
    # Find legal structures
    articles = re.findall(r'(?:^|\n)\s*(?:ĐIỀU|Điều)\s+(?:số\s+)?(\d+[a-z]?)', content, re.IGNORECASE | re.MULTILINE)
    chapters = re.findall(r'(?:^|\n)\s*(?:CHƯƠNG|Chương)\s+([IVX\d]+)', content, re.IGNORECASE | re.MULTILINE)
    sections = re.findall(r'(?:^|\n)\s*(?:MỤC|Mục)\s+(\d+)', content, re.IGNORECASE | re.MULTILINE)
    
    print(f"   📜 Articles found: {len(articles)} - {articles[:5]}{'...' if len(articles) > 5 else ''}")
    print(f"   📚 Chapters found: {len(chapters)} - {chapters}")
    print(f"   📑 Sections found: {len(sections)} - {sections}")
    
    # Estimate content distribution
    article_positions = []
    for match in re.finditer(r'(?:^|\n)\s*(?:ĐIỀU|Điều)\s+(?:số\s+)?\d+[a-z]?', content, re.IGNORECASE | re.MULTILINE):
        article_positions.append(match.start())
    
    if article_positions:
        # Preamble: before first article
        preamble_end = article_positions[0]
        preamble_chars = preamble_end
        
        # Articles: from first to last article  
        articles_start = article_positions[0]
        articles_end = article_positions[-1] + 1000  # rough estimate
        articles_chars = min(articles_end, len(content)) - articles_start
        
        # Appendix: after last article
        appendix_chars = len(content) - min(articles_end, len(content))
    else:
        preamble_chars = len(content) // 3  # rough estimate
        articles_chars = len(content) // 2
        appendix_chars = len(content) - preamble_chars - articles_chars
    
    print(f"   📄 Content distribution estimate:")
    print(f"      - Preamble: {preamble_chars:,} chars ({preamble_chars/len(content):.1%})")
    print(f"      - Articles: {articles_chars:,} chars ({articles_chars/len(content):.1%})")
    print(f"      - Appendix: {appendix_chars:,} chars ({appendix_chars/len(content):.1%})")
    
    return {
        'articles': len(articles),
        'chapters': len(chapters),
        'sections': len(sections),
        'preamble_chars': preamble_chars,
        'articles_chars': articles_chars,
        'appendix_chars': appendix_chars
    }

def analyze_preservation(raw_content: str, processed_docs: List, content_analysis: Dict) -> Dict[str, Any]:
    """Phân tích chi tiết preservation"""
    
    issues = []
    processed_chars = sum(len(doc.content) for doc in processed_docs)
    preservation_ratio = processed_chars / max(len(raw_content), 1)
    
    # Analyze by content type
    legal_chunks = [doc for doc in processed_docs if doc.metadata.get('content_type') == 'legal_document']
    preamble_chunks = [doc for doc in processed_docs if doc.metadata.get('content_type') == 'legal_preamble']
    conclusion_chunks = [doc for doc in processed_docs if doc.metadata.get('content_type') == 'legal_conclusion']
    qa_chunks = [doc for doc in processed_docs if doc.metadata.get('content_type') == 'qa_entry']
    fallback_chunks = [doc for doc in processed_docs if 'fallback' in doc.metadata.get('content_type', '')]
    
    print(f"   📦 Chunks by type:")
    print(f"      - Legal document chunks: {len(legal_chunks)}")
    print(f"      - Preamble chunks: {len(preamble_chunks)}")  
    print(f"      - Conclusion/appendix chunks: {len(conclusion_chunks)}")
    print(f"      - Q&A chunks: {len(qa_chunks)}")
    print(f"      - Fallback chunks: {len(fallback_chunks)}")
    
    # Check for potential losses
    if preservation_ratio < 0.7:
        issues.append(f"Low preservation ratio: {preservation_ratio:.1%}")
    
    if content_analysis['articles'] > 0 and len(legal_chunks) == 0:
        issues.append("Legal articles detected but no legal chunks created")
    
    if content_analysis['preamble_chars'] > 500 and len(preamble_chunks) == 0:
        issues.append("Significant preamble content but no preamble chunks")
    
    if content_analysis['appendix_chars'] > 500 and len(conclusion_chunks) == 0:
        issues.append("Significant appendix content but no conclusion chunks")
    
    # Check specific legal document issues
    if len(legal_chunks) > 0:
        # Check if all articles were captured
        articles_in_chunks = set()
        for chunk in legal_chunks:
            law_unit = chunk.metadata.get('law_unit', '')
            if law_unit and '.' in law_unit:
                article_num = law_unit.split('.')[0]
                articles_in_chunks.add(article_num)
        
        if len(articles_in_chunks) < content_analysis['articles'] * 0.8:
            issues.append(f"Only {len(articles_in_chunks)} articles captured out of {content_analysis['articles']}")
    
    print(f"   📊 Preservation ratio: {preservation_ratio:.1%}")
    if issues:
        print(f"   ⚠️ Issues found: {len(issues)}")
        for issue in issues:
            print(f"      - {issue}")
    
    return {
        'ratio': preservation_ratio,
        'issues': issues,
        'chunk_distribution': {
            'legal': len(legal_chunks),
            'preamble': len(preamble_chunks),
            'conclusion': len(conclusion_chunks),
            'qa': len(qa_chunks),
            'fallback': len(fallback_chunks)
        }
    }

def print_analysis_results(analysis: ContentAnalysis):
    """In kết quả phân tích"""
    
    print(f"\n📋 ANALYSIS RESULTS for {analysis.file_name}")
    print(f"   📏 Total content: {analysis.total_chars:,} characters")
    print(f"   📄 Paragraphs: {analysis.total_paragraphs}")
    print(f"   📜 Legal structure:")
    print(f"      - Articles: {analysis.articles_found}")
    print(f"      - Chapters: {analysis.chapters_found}")
    print(f"      - Sections: {analysis.sections_found}")
    
    print(f"   🏗️ Processing results:")
    print(f"      - Chunks created: {analysis.chunks_created}")
    print(f"      - Processed content: {analysis.processed_chars:,} characters")
    print(f"      - Preservation ratio: {analysis.preservation_ratio:.1%}")
    
    # Status assessment
    if analysis.preservation_ratio >= 0.9:
        status = "EXCELLENT ✅"
    elif analysis.preservation_ratio >= 0.8:
        status = "GOOD ✅"
    elif analysis.preservation_ratio >= 0.7:
        status = "ACCEPTABLE ⚠️"
    else:
        status = "POOR ❌"
    
    print(f"   🎯 STATUS: {status}")
    
    if analysis.issues:
        print(f"   ⚠️ Issues ({len(analysis.issues)}):")
        for issue in analysis.issues:
            print(f"      - {issue}")

def print_overall_summary(results: List[ContentAnalysis]):
    """In tổng kết"""
    
    print(f"\n{'='*60}")
    print(f"📊 OVERALL SUMMARY")
    print(f"{'='*60}")
    
    total_original = sum(r.total_chars for r in results)
    total_processed = sum(r.processed_chars for r in results)
    overall_ratio = total_processed / max(total_original, 1)
    
    print(f"Files analyzed: {len(results)}")
    print(f"Total original content: {total_original:,} characters")
    print(f"Total processed content: {total_processed:,} characters")
    print(f"Overall preservation: {overall_ratio:.1%}")
    
    # Per-file summary
    print(f"\n📋 Per-file preservation:")
    for result in results:
        status_icon = "✅" if result.preservation_ratio >= 0.8 else "⚠️" if result.preservation_ratio >= 0.7 else "❌"
        print(f"   {status_icon} {result.file_name}: {result.preservation_ratio:.1%} ({result.chunks_created} chunks)")
    
    # Common issues
    all_issues = []
    for result in results:
        all_issues.extend(result.issues)
    
    if all_issues:
        issue_counts = {}
        for issue in all_issues:
            # Group similar issues
            if "preservation ratio" in issue:
                key = "Low preservation ratio"
            elif "articles detected" in issue:
                key = "Articles not captured"
            elif "preamble" in issue:
                key = "Preamble content lost"
            elif "appendix" in issue:
                key = "Appendix content lost"
            else:
                key = issue
            
            issue_counts[key] = issue_counts.get(key, 0) + 1
        
        print(f"\n⚠️ Common issues:")
        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {issue}: {count} files affected")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if overall_ratio < 0.8:
        print("   - URGENT: Significant content loss detected")
        print("   - Check DOCX extraction for tables/complex formatting")
        print("   - Verify legal article regex patterns")
        print("   - Test with simpler documents first")
    elif overall_ratio < 0.9:
        print("   - Good preservation but room for improvement")
        print("   - Check preamble/appendix extraction")
        print("   - Verify edge cases in article patterns")
    else:
        print("   - Excellent preservation! System working well")
        print("   - Monitor for edge cases in new documents")

def create_sample_test():
    """Tạo test sample nếu không có files thực tế"""
    
    print("📝 Creating sample legal document test...")
    
    # Sample legal content
    sample_legal = """
LUẬT SỐ 49/2019/QH14
LUẬT XUẤT CẢNH, NHẬP CẢNH CỦA CÔNG DAN VIỆT NAM

CHƯƠNG I
NHỮNG QUY ĐỊNH CHUNG

Điều 1. Phạm vi điều chỉnh
Luật này quy định về xuất cảnh, nhập cảnh của công dân Việt Nam; quản lý xuất cảnh, nhập cảnh của công dân Việt Nam.

Điều 2. Đối tượng áp dụng
1. Công dân Việt Nam.
2. Cơ quan, tổ chức, cá nhân có liên quan đến hoạt động xuất cảnh, nhập cảnh của công dân Việt Nam.

Điều 3. Giải thích từ ngữ
Trong Luật này, các từ ngữ dưới đây được hiểu như sau:
1. Xuất cảnh là việc công dân Việt Nam ra khỏi lãnh thổ Việt Nam để đi nước ngoài.
2. Nhập cảnh là việc công dân Việt Nam từ nước ngoài về lãnh thổ Việt Nam.

CHƯƠNG II
XUẤT CẢNH CỦA CÔNG DÂN VIỆT NAM

Điều 15. Tạm hoãn xuất cảnh
1. Công dân Việt Nam bị tạm hoãn xuất cảnh trong các trường hợp sau đây:
a) Đang trong thời gian thi hành án phạt tù;
b) Đang bị áp dụng biện pháp xử lý hành chính đưa vào cơ sở cai nghiện bắt buộc, cơ sở giáo dục bắt buộc, cơ sở chữa bệnh bắt buộc.

2. Việc tạm hoãn xuất cảnh được thực hiện theo quy định của pháp luật về tố tụng hình sự, pháp luật về xử lý vi phạm hành chính.
"""
    
    # Test with sample
    processor = DocumentProcessor()
    
    # Simulate file processing
    print("Testing with sample legal content...")
    
    # Create temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(sample_legal)
        temp_file = f.name
    
    try:
        # Analyze structure
        content_analysis = analyze_content_structure(sample_legal)
        
        # Test classification
        doc_type, confidence = processor._classify_document_with_confidence(sample_legal)
        print(f"Sample classified as: {doc_type} (confidence: {confidence:.2f})")
        
        # Test manual processing (since we don't have DOCX)
        if doc_type == 'legal':
            print("Would process as legal document...")
            articles = re.findall(r'Điều\s+(\d+[a-z]?)', sample_legal, re.IGNORECASE)
            print(f"Articles that would be extracted: {articles}")
        
    finally:
        os.unlink(temp_file)

if __name__ == "__main__":
    analyze_real_legal_documents()