# services/rag_accuracy_test.py - TEST THÔNG TIN CHÍNH XÁC
"""
🧪 RAG ACCURACY TEST - Kiểm tra độ chính xác thông tin
🎯 Focus: Kết quả thông tin thực tế, không phải log
📋 Output: Câu hỏi → Thông tin tìm được → Độ chính xác
"""
import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent))

from app.services.unified_processor import UnifiedProcessor
from app.services.vector_rag.rag_engine import RAGEngine

class RAGAccuracyTester:
    """Test độ chính xác thông tin RAG"""
    
    def __init__(self):
        self.unified = UnifiedProcessor()
        self.rag_engine = None
        
        # Các tình huống test thực tế
        self.test_scenarios = [
            # TÌNH HUỐNG 1: Làm hộ chiếu lần đầu
            {
                "scenario": "Làm hộ chiếu lần đầu",
                "questions": [
                    "Công dân Việt Nam có quyền xuất cảnh không?",
                    "Thủ tục làm hộ chiếu cần giấy tờ gì?", 
                    "Bao lâu thì có hộ chiếu?"
                ]
            },
            
            # TÌNH HUỐNG 2: Điều kiện xuất cảnh
            {
                "scenario": "Điều kiện xuất cảnh",
                "questions": [
                    "Điều kiện để được xuất cảnh?",
                    "Hộ chiếu còn hạn bao lâu thì được đi?",
                    "Cần visa không?"
                ]
            },
            
            # TÌNH HUỐNG 3: Trường hợp bị cấm
            {
                "scenario": "Trường hợp bị hạn chế",
                "questions": [
                    "Trường hợp nào bị tạm hoãn xuất cảnh?",
                    "Bị can bị cáo có được đi nước ngoài không?",
                    "Ai có thẩm quyền quyết định tạm hoãn?"
                ]
            },
            
            # TÌNH HUỐNG 4: Hộ chiếu hết hạn
            {
                "scenario": "Hộ chiếu hết hạn",
                "questions": [
                    "Hộ chiếu hết hạn phải làm gì?",
                    "Cấp lại hộ chiếu có khác gì cấp mới?",
                    "Thời hạn hộ chiếu mới là bao lâu?"
                ]
            },
            
            # TÌNH HUỐNG 5: Trẻ em làm hộ chiếu
            {
                "scenario": "Trẻ em làm hộ chiếu", 
                "questions": [
                    "Trẻ em có được làm hộ chiếu không?",
                    "Hộ chiếu trẻ em có thời hạn khác người lớn không?",
                    "Cha mẹ cần làm gì khi con làm hộ chiếu?"
                ]
            },
            
            # TÌNH HUỐNG 6: Mất hộ chiếu
            {
                "scenario": "Mất hộ chiếu",
                "questions": [
                    "Mất hộ chiếu phải làm gì?",
                    "Báo mất hộ chiếu trong thời gian bao lâu?",
                    "Làm lại hộ chiếu sau khi mất có khó không?"
                ]
            },
            
            # TÌNH HUỐNG 7: Đa quốc tịch
            {
                "scenario": "Đa quốc tịch",
                "questions": [
                    "Người có hai quốc tịch xuất cảnh Việt Nam bằng hộ chiếu nào?",
                    "Có được giữ cả hai hộ chiếu không?",
                    "Nhập cảnh về Việt Nam dùng hộ chiếu gì?"
                ]
            }
        ]
    
    async def initialize_rag(self):
        """Khởi tạo RAG Engine"""
        try:
            print("🔧 Khởi tạo RAG Engine...")
            self.rag_engine = RAGEngine()
            result = await self.rag_engine.initialize()
            
            if result['success']:
                print("✅ RAG Engine sẵn sàng")
                return True
            else:
                print(f"❌ RAG Engine thất bại: {result['message']}")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi RAG Engine: {e}")
            return False
    
    async def test_all_scenarios(self):
        """Test tất cả tình huống"""
        print("\n" + "="*80)
        print("🧪 RAG ACCURACY TEST - Kiểm tra thông tin chính xác")
        print("="*80)
        
        if not await self.initialize_rag():
            print("❌ Không thể tiếp tục - RAG thất bại")
            return
        
        total_questions = sum(len(scenario['questions']) for scenario in self.test_scenarios)
        print(f"📋 Test {len(self.test_scenarios)} tình huống, {total_questions} câu hỏi\n")
        
        for i, scenario in enumerate(self.test_scenarios, 1):
            await self.test_scenario(scenario, i)
        
        print(f"\n✅ Hoàn thành test - Kiểm tra độ chính xác thông tin")
    
    async def test_scenario(self, scenario_data, scenario_num):
        """Test một tình huống"""
        scenario_name = scenario_data['scenario']
        questions = scenario_data['questions']
        
        print(f"\n{'='*60}")
        print(f"📋 TÌNH HUỐNG {scenario_num}: {scenario_name}")
        print(f"{'='*60}")
        
        user_id = f"test_scenario_{scenario_num}"
        
        for q_num, question in enumerate(questions, 1):
            print(f"\n🔍 Câu {q_num}: {question}")
            print("-" * 50)
            
            result = await self.process_question(question, user_id)
            
            if result['success']:
                print(f"💬 Trả lời:")
                print(f"   {result['answer'][:300]}{'...' if len(result['answer']) > 300 else ''}")
                print(f"📊 Nguồn: {result.get('source', 'không rõ')}")
                
                # Đánh giá nhanh độ chính xác
                accuracy = self.evaluate_answer_quality(question, result['answer'])
                print(f"✅ Đánh giá: {accuracy}")
            else:
                print(f"❌ Lỗi: {result.get('error', 'Không rõ')}")
        
        print(f"\n🔚 Kết thúc tình huống: {scenario_name}")
    
    async def process_question(self, question, user_id):
        """Xử lý một câu hỏi"""
        try:
            # Lấy context hội thoại
            conversation_context = self.unified.conversation.get_conversation_context(user_id)
            
            # Resolve query
            resolved_query = self.unified.conversation.resolve_vague_query(user_id, question)
            
            # Phân tích intent
            intent_analysis = self.unified.intent.analyze_intent(resolved_query, {
                'has_history': conversation_context['has_history'],
                'topic_thread': conversation_context['topic_thread'],
                'entities': conversation_context['entities']
            })
            
            # Chuẩn bị data cho RAG
            rag_data = {
                'original_query': question,
                'resolved_query': resolved_query,
                'user_id': user_id,
                'conversation_context': conversation_context,
                'intent_analysis': intent_analysis,
                'entities': conversation_context['entities'],
                'topic_thread': conversation_context['topic_thread']
            }
            
            # Query RAG Engine trực tiếp
            result = await self.rag_engine.query(
                resolved_query,
                session_id=user_id,
                unified_data=rag_data
            )
            
            if result.get('success'):
                # Cập nhật conversation
                self.unified.conversation.add_interaction(
                    user_id, question, result['answer'], "rag"
                )
                
                return {
                    'success': True,
                    'answer': result['answer'],
                    'source': 'RAG Engine',
                    'pipeline_info': result.get('pipeline_info', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('answer', 'RAG không có kết quả')
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def evaluate_answer_quality(self, question, answer):
        """Đánh giá nhanh chất lượng câu trả lời"""
        if not answer or len(answer.strip()) < 20:
            return "❌ Câu trả lời quá ngắn"
        
        # Check có thông tin pháp lý không
        if any(keyword in answer.lower() for keyword in ['điều', 'khoản', 'quy định', 'luật']):
            has_legal = "✅ Có trích dẫn pháp lý"
        else:
            has_legal = "⚠️ Không có trích dẫn pháp lý"
        
        # Check có trả lời đúng trọng tâm không
        question_lower = question.lower()
        answer_lower = answer.lower()
        
        relevance_score = 0
        if 'quyền' in question_lower and 'quyền' in answer_lower:
            relevance_score += 1
        if 'thủ tục' in question_lower and any(word in answer_lower for word in ['thủ tục', 'hồ sơ', 'giấy tờ']):
            relevance_score += 1
        if 'điều kiện' in question_lower and 'điều kiện' in answer_lower:
            relevance_score += 1
        if 'thời hạn' in question_lower and any(word in answer_lower for word in ['thời hạn', 'năm', 'ngày']):
            relevance_score += 1
        if 'tạm hoãn' in question_lower and 'tạm hoãn' in answer_lower:
            relevance_score += 1
        
        if relevance_score > 0:
            relevance = f"✅ Trả lời đúng trọng tâm ({relevance_score} điểm)"
        else:
            relevance = "⚠️ Có thể không đúng trọng tâm"
        
        # Check độ dài hợp lý
        if 50 <= len(answer) <= 500:
            length = "✅ Độ dài hợp lý"
        elif len(answer) < 50:
            length = "⚠️ Hơi ngắn"
        else:
            length = "⚠️ Hơi dài"
        
        return f"{has_legal} | {relevance} | {length}"
    
    async def test_single_question(self, question: str):
        """Test một câu hỏi đơn lẻ"""
        print(f"\n🔍 Test câu hỏi: '{question}'")
        
        if not await self.initialize_rag():
            print("❌ Không thể tiếp tục - RAG thất bại")
            return
        
        result = await self.process_question(question, "single_test")
        
        if result['success']:
            print(f"\n💬 Trả lời:")
            print(f"{result['answer']}")
            print(f"\n📊 Đánh giá: {self.evaluate_answer_quality(question, result['answer'])}")
        else:
            print(f"\n❌ Lỗi: {result.get('error', 'Không rõ')}")

async def main():
    """Main function"""
    tester = RAGAccuracyTester()
    
    if len(sys.argv) > 1:
        # Test single question
        question = ' '.join(sys.argv[1:])
        await tester.test_single_question(question)
    else:
        # Test all scenarios
        await tester.test_all_scenarios()

if __name__ == "__main__":
    asyncio.run(main())