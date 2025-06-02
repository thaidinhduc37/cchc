#!/usr/bin/env python3
"""
Script query hệ thống RAG đã build
Chạy: python query_rag.py --vector_db ./vector_db --query "Thủ tục thành lập doanh nghiệp?"
"""

import argparse
import sys
import time
import json
from pathlib import Path
import logging

# Import từ build_vectors.py và rag_system.py
from build_vectors import load_vector_database
from rag_system import GemmaLLM, DocumentChunk

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RAGQuerySystem:
    """Hệ thống query RAG từ vector database đã build"""
    
    def __init__(self, vector_db_path: str, llm_model: str = "gemma:2b"):
        logger.info("🚀 Khởi tạo RAG Query System...")
        
        # Load vector database
        self.vector_store = load_vector_database(vector_db_path)
        
        # Khởi tạo LLM
        self.llm = GemmaLLM(llm_model)
        
        logger.info("✅ RAG Query System sẵn sàng!")
    
    def search_documents(self, query: str, top_k: int = 5) -> list[DocumentChunk]:
        """Tìm kiếm documents liên quan"""
        logger.info(f"🔍 Tìm kiếm: '{query}' (top {top_k})")
        
        start_time = time.time()
        results = self.vector_store.similarity_search(query, k=top_k)
        search_time = time.time() - start_time
        
        logger.info(f"⚡ Tìm thấy {len(results)} kết quả trong {search_time:.3f}s")
        
        return results
    
    def create_context_prompt(self, query: str, docs: list[DocumentChunk]) -> str:
        """Tạo prompt với context từ documents"""
        context_parts = []
        
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get('filename', 'Unknown')
            context_parts.append(f"[Tài liệu {i} - {source}]\n{doc.content}")
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""Dựa trên các tài liệu pháp lý sau, hãy trả lời câu hỏi một cách chính xác và chi tiết:

NGỮ CẢNH:
{context}

CÂU HỎI: {query}

HƯỚNG DẪN:
- Trả lời dựa trên thông tin trong tài liệu được cung cấp
- Trích dẫn cụ thể điều, khoản, điểm liên quan
- Nếu không có thông tin đủ, hãy nói rõ
- Trả lời bằng tiếng Việt, rõ ràng và súc tích
- Cấu trúc câu trả lời logic và dễ hiểu

TRẢ LỜI:"""

        return prompt
    
    def query(self, question: str, top_k: int = 5, verbose: bool = False) -> dict:
        """Query hệ thống RAG"""
        logger.info(f"❓ Câu hỏi: {question}")
        
        start_time = time.time()
        
        try:
            # 1. Tìm kiếm documents
            relevant_docs = self.search_documents(question, top_k)
            
            if not relevant_docs:
                return {
                    'question': question,
                    'answer': "Xin lỗi, tôi không tìm thấy thông tin liên quan trong cơ sở dữ liệu.",
                    'sources': [],
                    'search_time': 0,
                    'generation_time': 0,
                    'total_time': time.time() - start_time
                }
            
            search_time = time.time() - start_time
            
            # 2. Tạo prompt
            prompt = self.create_context_prompt(question, relevant_docs)
            
            if verbose:
                logger.info("📝 Prompt:")
                print("-" * 50)
                print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
                print("-" * 50)
            
            # 3. Generate answer
            gen_start = time.time()
            answer = self.llm.generate(prompt, max_tokens=800)
            generation_time = time.time() - gen_start
            
            # 4. Chuẩn bị sources
            sources = []
            for doc in relevant_docs:
                sources.append({
                    'filename': doc.metadata.get('filename', 'Unknown'),
                    'file_type': doc.metadata.get('file_type', 'unknown'),
                    'content_preview': doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
                })
            
            total_time = time.time() - start_time
            
            result = {
                'question': question,
                'answer': answer,
                'sources': sources,
                'search_time': search_time,
                'generation_time': generation_time,
                'total_time': total_time,
                'num_sources': len(relevant_docs)
            }
            
            logger.info(f"✅ Hoàn thành trong {total_time:.3f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Lỗi khi xử lý câu hỏi: {e}")
            return {
                'question': question,
                'answer': f"Có lỗi xảy ra: {str(e)}",
                'sources': [],
                'search_time': 0,
                'generation_time': 0,
                'total_time': time.time() - start_time
            }
    
    def interactive_mode(self):
        """Chế độ tương tác"""
        print("\n🤖 RAG Pháp lý - Chế độ tương tác")
        print("=" * 50)
        print("Nhập câu hỏi hoặc 'quit' để thoát")
        print("-" * 50)
        
        while True:
            try:
                question = input("\n❓ Câu hỏi: ").strip()
                
                if question.lower() in ['quit', 'exit', 'q']:
                    print("👋 Tạm biệt!")
                    break
                
                if not question:
                    continue
                
                print("\n🔄 Đang xử lý...")
                result = self.query(question)
                
                print(f"\n✅ Trả lời:")
                print("-" * 30)
                print(result['answer'])
                
                print(f"\n📊 Thống kê:")
                print(f"  • Thời gian tìm kiếm: {result['search_time']:.3f}s")
                print(f"  • Thời gian tạo câu trả lời: {result['generation_time']:.3f}s")
                print(f"  • Tổng thời gian: {result['total_time']:.3f}s")
                print(f"  • Số nguồn tham khảo: {result['num_sources']}")
                
                if result['sources']:
                    print(f"\n📚 Nguồn tham khảo:")
                    for i, source in enumerate(result['sources'][:3], 1):
                        print(f"  {i}. {source['filename']} ({source['file_type']})")
                
            except KeyboardInterrupt:
                print("\n👋 Tạm biệt!")
                break
            except Exception as e:
                print(f"❌ Lỗi: {e}")

def print_result(result: dict, show_sources: bool = True, show_stats: bool = True):
    """In kết quả query"""
    print(f"\n❓ Câu hỏi: {result['question']}")
    print("=" * 60)
    
    print(f"✅ Trả lời:")
    print("-" * 30)
    print(result['answer'])
    
    if show_stats:
        print(f"\n📊 Thống kê:")
        print(f"  • Thời gian tìm kiếm: {result['search_time']:.3f}s")
        print(f"  • Thời gian tạo câu trả lời: {result['generation_time']:.3f}s")
        print(f"  • Tổng thời gian: {result['total_time']:.3f}s")
        print(f"  • Số nguồn tham khảo: {result['num_sources']}")
    
    if show_sources and result['sources']:
        print(f"\n📚 Nguồn tham khảo:")
        for i, source in enumerate(result['sources'], 1):
            print(f"  {i}. {source['filename']} ({source['file_type']})")
            if len(source['content_preview']) < 150:
                print(f"     📄 {source['content_preview']}")

def batch_query_from_file(query_system: RAGQuerySystem, questions_file: str, output_file: str = None):
    """Chạy batch queries từ file"""
    logger.info(f"📁 Đọc câu hỏi từ: {questions_file}")
    
    with open(questions_file, 'r', encoding='utf-8') as f:
        questions = [line.strip() for line in f if line.strip()]
    
    logger.info(f"📋 Sẽ xử lý {len(questions)} câu hỏi")
    
    results = []
    
    for i, question in enumerate(questions, 1):
        logger.info(f"🔄 Xử lý câu hỏi {i}/{len(questions)}")
        result = query_system.query(question)
        results.append(result)
        
        print_result(result, show_sources=False, show_stats=False)
        print("-" * 60)
    
    # Lưu kết quả nếu có output file
    if output_file:
        logger.info(f"💾 Lưu kết quả vào: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Thống kê tổng
    total_time = sum(r['total_time'] for r in results)
    avg_time = total_time / len(results)
    
    print(f"\n📊 THỐNG KÊ TỔNG:")
    print(f"  • Tổng câu hỏi: {len(questions)}")
    print(f"  • Tổng thời gian: {total_time:.2f}s")
    print(f"  • Thời gian trung bình/câu hỏi: {avg_time:.3f}s")

def main():
    """Hàm main"""
    parser = argparse.ArgumentParser(description="Query RAG system với vector database")
    
    parser.add_argument(
        "--vector_db", 
        type=str, 
        required=True,
        help="Đường dẫn đến vector database"
    )
    
    parser.add_argument(
        "--query", 
        type=str, 
        help="Câu hỏi cần trả lời"
    )
    
    parser.add_argument(
        "--questions_file", 
        type=str, 
        help="File chứa danh sách câu hỏi (mỗi dòng 1 câu hỏi)"
    )
    
    parser.add_argument(
        "--output_file", 
        type=str, 
        help="File lưu kết quả (JSON format)"
    )
    
    parser.add_argument(
        "--interactive", 
        action="store_true",
        help="Chế độ tương tác"
    )
    
    parser.add_argument(
        "--top_k", 
        type=int, 
        default=5,
        help="Số lượng documents liên quan (default: 5)"
    )
    
    parser.add_argument(
        "--llm_model", 
        type=str, 
        default="gemma:2b",
        help="Model LLM (default: gemma:2b)"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Hiển thị thông tin chi tiết"
    )
    
    args = parser.parse_args()
    
    try:
        # Khởi tạo query system
        query_system = RAGQuerySystem(args.vector_db, args.llm_model)
        
        if args.interactive:
            # Chế độ tương tác
            query_system.interactive_mode()
            
        elif args.questions_file:
            # Batch query từ file
            batch_query_from_file(query_system, args.questions_file, args.output_file)
            
        elif args.query:
            # Single query
            result = query_system.query(args.query, args.top_k, args.verbose)
            print_result(result)
            
            # Lưu kết quả nếu có output file
            if args.output_file:
                with open(args.output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                logger.info(f"💾 Đã lưu kết quả vào: {args.output_file}")
        else:
            print("❌ Vui lòng cung cấp --query, --questions_file, hoặc --interactive")
            parser.print_help()
    
    except KeyboardInterrupt:
        logger.info("\n⏹️ Quá trình bị ngắt")
    except Exception as e:
        logger.error(f"❌ Lỗi: {e}")
        sys.exit(1)

