# debug_pipeline.py - Tìm chỗ Q&A bị mất
import os
import sys
import pickle

sys.path.insert(0, 'services/vector_rag')

def debug_qa_loss():
    print("=== TÌM CHỖ Q&A BỊ MẤT ===")
    
    # STEP 1: DocumentProcessor có tạo Q&A không?
    print("\n1. DocumentProcessor output:")
    from document_processor import DocumentProcessor
    processor = DocumentProcessor()
    documents = processor.process_directory("./dataset/xuatnhapcanh/documents")
    
    qa_count = sum(1 for d in documents if d.metadata.get('content_type') == 'qa_entry')
    legal_count = sum(1 for d in documents if d.metadata.get('content_type') == 'legal_document')
    
    print(f"   📤 Output: {qa_count} Q&A + {legal_count} Legal = {len(documents)} total")
    
    if qa_count == 0:
        print("   ❌ PROBLEM: DocumentProcessor không tạo Q&A!")
        return
    
    # STEP 2: VectorBuilder có nhận đúng input không?
    print("\n2. VectorBuilder input:")
    from vector_store import VectorBuilder
    builder = VectorBuilder()
    
    # Test build process
    import asyncio
    
    print(f"   📥 Input to VectorBuilder: {len(documents)} documents")
    print(f"      - {qa_count} Q&A documents")
    print(f"      - {legal_count} Legal documents")
    
    # Simulate build
    result = asyncio.run(builder.build_from_documents(documents))
    
    if result['success']:
        stats = result['stats']
        built_qa = stats.get('qa_entries', 0)
        built_legal = stats.get('legal_documents', 0)
        built_total = stats.get('total_documents', 0)
        
        print(f"   📤 VectorBuilder output: {built_total} documents")
        print(f"      - {built_qa} Q&A documents")
        print(f"      - {built_legal} Legal documents")
        
        # PROBLEM IDENTIFIED
        if qa_count > 0 and built_qa == 0:
            print(f"\n   🚨 FOUND PROBLEM: VectorBuilder lost Q&A!")
            print(f"      Input had {qa_count} Q&A → Output has {built_qa} Q&A")
            print(f"      → Bug is in VectorBuilder.build_from_documents()")
        elif qa_count == built_qa:
            print(f"\n   ✅ VectorBuilder preserved Q&A correctly")
        else:
            print(f"\n   ⚠️ VectorBuilder partially lost Q&A: {qa_count} → {built_qa}")
            
    else:
        print(f"   ❌ VectorBuilder failed: {result.get('message')}")

if __name__ == "__main__":
    debug_qa_loss()