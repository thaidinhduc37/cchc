# unified_processor.py - Phiên bản tối ưu hóa Gen Z với Context Management
import os
import json
import pandas as pd
from datetime import datetime
from collections import deque
from utils.response_formatter import format_response
from services.flow_engine import flow_engine
from services.vector_rag.rag_engine import RAGEngine
from services.vector_rag.llm_handler import LLMHandler
from services.vector_rag.config import LLMConfig, SystemConfig

import re
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# Nếu dùng file gguf local: (ưu tiên)
llm_handler = LLMHandler(model_path="./models/gemma-2b.Q4_K_M.gguf", config=LLMConfig())

# Nếu chỉ dùng Ollama (khuyên dùng cho đa nền tảng/dev/test):
# llm_handler = LLMHandler(api_url="http://localhost:11434", model_name="gemma:2b", config=LLMConfig())

def initialize_rag_system():
    try:
        system_config = SystemConfig()
        system_config.data_path = "dataset"
        system_config.vector_store_path = "vector_stores"
        
        rag_engine = RAGEngine(
            model_path="./models/gemma-2b.Q4_K_M.gguf",
            system_config=system_config
        )
        
        # QUAN TRỌNG: Khởi tạo hệ thống với vector stores
        result = rag_engine.initialize_system(
            data_path="dataset",
            domains=["xuatnhapcanh", "cancuoc", "dangkyxe", "cutru"],
            force_rebuild=False
        )
        
        if result['success']:
            logger.info(f"✅ RAG initialized: {result['domains_created']}")
            return rag_engine, True
        else:
            logger.error(f"❌ RAG failed: {result['message']}")
            return None, False
            
    except Exception as e:
        logger.error(f"❌ RAG error: {str(e)}")
        return None, False

rag_engine, rag_initialized = initialize_rag_system()

# === KHU VỰC: Quản lý Context/Ngữ cảnh ===
class ContextManager:
    def __init__(self, max_history=6):
        self.user_contexts = {}  # {user_id: deque of conversations}
        self.max_history = max_history
    
    def add_conversation(self, user_id: str, user_input: str, bot_response: str, domain: str = None, topic: str = None):
        """Thêm cuộc trò chuyện vào context"""
        if user_id not in self.user_contexts:
            self.user_contexts[user_id] = deque(maxlen=self.max_history)
        
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "bot_response": bot_response,
            "domain": domain,
            "topic": topic  # chủ đề được trích xuất
        }
        self.user_contexts[user_id].append(conversation)
    
    def get_context(self, user_id: str) -> list:
        """Lấy lịch sử trò chuyện của user"""
        return list(self.user_contexts.get(user_id, []))
    
    def get_recent_context_string(self, user_id: str, max_conversations: int = 3) -> str:
        """Lấy context dạng string để đưa vào LLM"""
        contexts = self.get_context(user_id)
        if not contexts:
            return ""
        
        recent_contexts = contexts[-max_conversations:]
        context_str = "Lịch sử trò chuyện gần đây:\n"
        for i, conv in enumerate(recent_contexts, 1):
            context_str += f"{i}. Người dùng: {conv['user_input']}\n"
            context_str += f"   Bot: {conv['bot_response'][:200]}...\n"
            if conv.get('topic'):
                context_str += f"   Chủ đề: {conv['topic']}\n"
        return context_str
    
    def extract_topic_from_response(self, user_input: str, bot_response: str) -> str:
        """Trích xuất chủ đề chính từ câu hỏi và trả lời"""
        topic_keywords = {
            "hộ chiếu": ["hộ chiếu", "passport", "xuất nhập cảnh"],
            "căn cước": ["căn cước", "cccd", "chứng minh nhân dân"],
            "đăng ký xe": ["đăng ký xe", "biển số", "xe máy", "xe ô tô"],
            "cư trú": ["thường trú", "tạm trú", "cư trú"],
            "visa": ["visa", "thị thực"],
            "giấy tờ": ["giấy tờ", "hồ sơ", "thủ tục"]
        }
        
        combined_text = (user_input + " " + bot_response).lower()
        for topic, keywords in topic_keywords.items():
            if any(kw in combined_text for kw in keywords):
                return topic
        return "general"
    
    def clear_context(self, user_id: str):
        """Xóa context của user"""
        if user_id in self.user_contexts:
            del self.user_contexts[user_id]

# Khởi tạo context manager global
context_manager = ContextManager()

# === KHU VỰC: Xử lý câu hỏi ngắn gọn/tham chiếu ===
def expand_contextual_query(user_input: str, user_id: str) -> tuple:
    """
    Mở rộng câu hỏi ngắn gọn dựa trên context
    Returns: (expanded_query, is_contextual, inferred_domain)
    """
    user_input_lower = user_input.lower().strip()
    
    # Các pattern câu hỏi ngắn gọn thường gặp
    short_patterns = [
        "thế trẻ em thì sao", "trẻ em thì thế nào", "còn trẻ em",
        "thế người lớn", "còn người lớn", "người lớn thì sao",
        "thế về phí", "phí thế nào", "còn phí", "giá thế nào",
        "thời gian thế nào", "mất bao lâu", "còn thời gian",
        "thế hồ sơ", "còn hồ sơ", "giấy tờ thế nào",
        "ở đâu làm", "làm ở đâu", "địa điểm",
        "thế online", "làm online", "trực tuyến",
        "thế", "còn", "như thế nào", "sao", "vậy"
    ]
    
    is_short_query = (
        len(user_input.split()) <= 4 or
        any(pattern in user_input_lower for pattern in short_patterns)
    )
    
    if not is_short_query:
        return user_input, False, None
    
    # Lấy context gần nhất để hiểu câu hỏi
    recent_contexts = context_manager.get_context(user_id)
    if not recent_contexts:
        return user_input, False, None
    
    last_context = recent_contexts[-1]
    last_topic = last_context.get('topic', 'general')
    last_domain = last_context.get('domain', 'xuatnhapcanh')
    
    # Mở rộng câu hỏi dựa trên context
    expanded_query = user_input
    
    if any(x in user_input_lower for x in ["trẻ em", "trẻ con", "con nhỏ"]):
        if last_topic == "hộ chiếu":
            expanded_query = "làm hộ chiếu cho trẻ em cần gì"
        elif last_topic == "căn cước":
            expanded_query = "làm căn cước cho trẻ em"
    
    elif any(x in user_input_lower for x in ["người lớn", "người già", "bố mẹ"]):
        if last_topic == "hộ chiếu":
            expanded_query = "làm hộ chiếu cho người lớn"
        elif last_topic == "căn cước":
            expanded_query = "làm căn cước cho người lớn"
    
    elif any(x in user_input_lower for x in ["phí", "giá", "tiền", "chi phí"]):
        if last_topic == "hộ chiếu":
            expanded_query = "phí làm hộ chiếu bao nhiêu tiền"
        elif last_topic == "căn cước":
            expanded_query = "phí làm căn cước"
        elif last_topic == "đăng ký xe":
            expanded_query = "phí đăng ký xe"
    
    elif any(x in user_input_lower for x in ["thời gian", "bao lâu", "mất"]):
        if last_topic == "hộ chiếu":
            expanded_query = "làm hộ chiếu mất bao lâu"
        elif last_topic == "căn cước":
            expanded_query = "làm căn cước mất bao lâu"
    
    elif any(x in user_input_lower for x in ["hồ sơ", "giấy tờ", "cần gì"]):
        if last_topic == "hộ chiếu":
            expanded_query = "hồ sơ làm hộ chiếu cần gì"
        elif last_topic == "căn cước":
            expanded_query = "hồ sơ làm căn cước"
    
    elif any(x in user_input_lower for x in ["đâu", "ở đâu", "địa điểm"]):
        if last_topic == "hộ chiếu":
            expanded_query = "làm hộ chiếu ở đâu"
        elif last_topic == "căn cước":
            expanded_query = "làm căn cước ở đâu"
    
    elif any(x in user_input_lower for x in ["online", "trực tuyến", "mạng"]):
        if last_topic == "hộ chiếu":
            expanded_query = "đăng ký hộ chiếu online"
        elif last_topic == "căn cước":
            expanded_query = "đăng ký căn cước online"
    
    # Các câu hỏi siêu ngắn "thế", "sao", "vậy"
    elif user_input_lower in ["thế", "sao", "vậy", "như thế nào", "thế nào"]:
        expanded_query = f"thông tin thêm về {last_topic}"
    
    logger.info(f"🔄 Expanded query: '{user_input}' -> '{expanded_query}'")
    return expanded_query, True, last_domain

# === KHU VỰC: Xác định lĩnh vực & ý định ===
def detect_domain(user_input: str) -> str:
    lowered = user_input.lower()
    if any(k in lowered for k in ["hộ chiếu", "xuất nhập cảnh", "passport", "visa", "giấy thông hành", "tạm trú"]):
        return "xuatnhapcanh"
    if any(k in lowered for k in ["căn cước", "cccd", "chứng minh", "đổi thẻ"]):
        return "cancuoc"
    if any(k in lowered for k in ["đăng ký xe", "biển số", "xe máy", "xe ô tô"]):
        return "dangkyxe"
    if any(k in lowered for k in ["thường trú", "tạm trú", "cư trú"]):
        return "cutru"
    if re.search(r'điều\s+\d+', lowered, re.IGNORECASE):
        return "xuatnhapcanh"
    return "xuatnhapcanh"

def is_flow_prompt(user_input):
    user_input = user_input.lower()
    return (
        user_input.startswith("hướng dẫn") or
        user_input.startswith("quy trình") or
        user_input.startswith("thủ tục") or
        any(kw in user_input for kw in [
            "hướng dẫn thủ tục", "hướng dẫn làm", "các bước", "trình tự"
        ])
    )

def detect_flow_intent(user_input):
    flow_phrases = [
        "hướng dẫn", "quy trình", "trình tự", "các bước", "bước thực hiện", "thủ tục"
    ]
    user_input = user_input.lower().strip()
    return (
        any(user_input.startswith(kw) for kw in flow_phrases)
        or any(phrase in user_input for phrase in [
            "hướng dẫn làm", "hướng dẫn thủ tục", "hướng dẫn quy trình", "trình tự thực hiện"
        ])
    )

# === KHU VỰC: Xử lý Flow ===
def start_flow(user_id):
    flow_engine.reset(user_id)
    flow_engine.user_progress[user_id] = {"flow_id": "start", "step_index": 1}
    step = flow_engine.get_current_step(user_id).get("step", {})
    return format_response(step.get("name", "Đã vào hướng dẫn."), source="flow", buttons=["Tiếp tục", "Quay lại", "Kết thúc"])

def handle_flow_text_query(user_input, user_id):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    context = flow_engine.user_progress.get(user_id, {})
    flow_id = context.get("flow_id")
    steps = flow_engine.flows.get(flow_id, {}).get("steps", {})

    combined = [s.get("name", "") + " " + s.get("description", "") for s in steps.values()]
    vectorizer = TfidfVectorizer().fit_transform(combined + [user_input])
    sim = cosine_similarity(vectorizer[-1], vectorizer[:-1]).flatten()
    best_idx = sim.argmax()
    if sim[best_idx] >= 0.4:
        matched_step_index = list(steps.keys())[best_idx]
        flow_engine.user_progress[user_id]["step_index"] = int(matched_step_index)
        return format_response(steps[matched_step_index].get("name", ""), source="flow", buttons=["Tiếp tục", "Quay lại", "Kết thúc"])

    jump_result = flow_engine.jump_to_step_by_description(user_id, user_input)
    if jump_result:
        return format_response(jump_result.get("step", {}).get("name", ""), source="flow", buttons=["Tiếp tục", "Quay lại", "Kết thúc"])

    return format_response("🛑 Bạn đang trong hướng dẫn. Bấm 'Kết thúc' để hỏi câu khác.", source="flow")

# === KHU VỰC: Trả lời từ question.xlsx ===
def handle_question_fallback(user_input, domain):
    path = f"dataset/{domain}/question.xlsx"
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_excel(path)
        df.columns = df.columns.str.lower()
        questions = df["question"].fillna("").tolist()
        answers = df["answer"].fillna("").tolist()
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vec = TfidfVectorizer().fit_transform(questions + [user_input])
        sim = cosine_similarity(vec[-1], vec[:-1]).flatten()
        best_idx = sim.argmax()
        if sim[best_idx] >= 0.65:
            return answers[best_idx]
    except Exception as e:
        logger.error(f"Lỗi xử lý question.xlsx: {str(e)}")
        return None

# === KHU VỰC: Trả lời từ responses.json ===
def handle_response_fallback(user_input, domain):
    path = f"dataset/{domain}/responses.json"
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f).get("entries", [])
        for entry in entries:
            for kw in entry.get("keywords", []):
                if kw.lower() in user_input.lower():
                    return "\n".join(entry.get("responses", []))
    except Exception as e:
        logger.error(f"Lỗi xử lý responses.json: {str(e)}")
        return None

# === KHU VỰC: Vector RAG ===
def handle_vector_search_and_llm(user_input, domain, context_history=None):
    try:

        # Kiểm tra RAG engine có sẵn sàng không
        if not rag_engine or not rag_initialized:
            logger.warning("RAG engine not initialized")
            return None
            
        rag_result = rag_engine.query(user_input, domain=domain)
        if not rag_result or not rag_result.get('success'):
            logger.warning(f"RAG query failed: {rag_result}")
            return None
 

        context_chunks = [doc.page_content for doc in rag_result.get('source_documents', [])][:3]
        rag_context_text = "\n\n".join(context_chunks)
        question = user_input

        prompt_parts = []
        if context_history:
            prompt_parts.append(f"Lịch sử hội thoại gần đây giữa bạn và trợ lý:\n{context_history}\n")
        if rag_context_text:
            prompt_parts.append(f"Văn bản tham khảo hoặc kiến thức liên quan:\n{rag_context_text}\n")
        prompt_parts.append(f"Câu hỏi hiện tại: {question}\n")
        prompt_parts.append("Dựa trên lịch sử hội thoại và văn bản tham khảo ở trên, trả lời tự nhiên, thân thiện, đúng trọng tâm. Nếu không đủ thông tin thì trả lời lịch sự là chưa tìm thấy.")
        prompt = "\n".join(prompt_parts)

        answer = llm_handler.generate(prompt)
        return {
            "answer": answer.strip(),
            "sources": context_chunks,
            "metadata": rag_result,
            "success": True
        }
    except Exception as e:
        logger.error(f"❌ Error handle_vector_search_and_llm: {e}")
        return None


# === KHU VỰC: Fallback & Logging ===
def handle_fallback_and_log(user_input: str, domain: str) -> str:
    # Chặn câu hỏi chính trị hoặc nhạy cảm
    sensitive_keywords = [
        "vương đình huệ", "nguyễn phú trọng", "chủ tịch", "tổng bí thư",
        "chính trị", "quốc hội", "đảng", "bộ trưởng", "bầu cử", "chính quyền"
    ]
    if any(kw in user_input.lower() for kw in sensitive_keywords):
        return "❌ Tôi chỉ hỗ trợ các vấn đề thủ tục hành chính, không trả lời về nội dung chính trị."

    # Câu chào hỏi phổ biến
    greeting_patterns = [
        "chào", "hi", "hello", "xin chào", "good morning", 
        "tạm biệt", "bye", "goodbye"
    ]
    if any(x in user_input.lower() for x in greeting_patterns):
        return (
            "Xin chào! Tôi là trợ lý hỗ trợ thông tin về thủ tục hành chính.\n"
            "Tôi có thể giúp bạn tìm hiểu về:\n"
            "- Thủ tục xuất nhập cảnh, hộ chiếu\n"
            "- Căn cước công dân\n"
            "- Đăng ký xe và biển số\n"
            "- Đăng ký cư trú\n"
            "Bạn cần hỗ trợ thông tin gì ạ?"
        )

    # Log lại câu hỏi không có context để admin cập nhật vào dataset
    try:
        from services.ollama_service import log_to_review_data
        log_to_review_data(user_input, None, domain)
    except Exception:
        pass
    return "Hiện tại chưa có thông tin, tôi sẽ cập nhật và trả lời sớm nhất."

# === KHU VỰC: Entry chính xử lý toàn bộ ===
def process_user_query(user_input: str, user_id: str, domain: str = None) -> dict:
    user_input = user_input.strip()
    if not user_input:
        return format_response("❓ Vui lòng nhập câu hỏi.", source="system")

    # 1. Xử lý context và mở rộng câu hỏi ngắn gọn
    expanded_query, is_contextual, inferred_domain = expand_contextual_query(user_input, user_id)
    
    # Sử dụng domain được suy luận từ context nếu có
    if inferred_domain and not domain:
        domain = inferred_domain
    
    # Log context expansion
    if is_contextual and expanded_query != user_input:
        logger.info(f"🔄 Context expansion: '{user_input}' -> '{expanded_query}'")

    # 2. Flow handling
    if is_flow_prompt(expanded_query):
        return {
            "reply": f"📌 Bạn có muốn hướng dẫn quy trình {expanded_query} không?",
            "source": "chatbot",
            "show_flow_button": True,
            "button_label": "Hướng dẫn quy trình"
        }

    if expanded_query.lower() in ["hướng dẫn quy trình", "xem quy trình"]:
        return start_flow(user_id)

    # 3. Domain detection
    if not domain:
        domain = detect_domain(expanded_query)

    # 4. Flow check
    if flow_engine.is_in_flow(user_id):
        return handle_flow_text_query(expanded_query, user_id)

    # 5. Check Excel mẫu trước
    excel_match = handle_question_fallback(expanded_query, domain)
    if excel_match:
        response = format_response(excel_match, source="question.xlsx")
        # Lưu context sau khi có response
        topic = context_manager.extract_topic_from_response(user_input, excel_match)
        context_manager.add_conversation(user_id, user_input, excel_match, domain, topic)
        return response

    # 6. Check RAG (vector) tiếp theo
    conversation_history = context_manager.get_recent_context_string(user_id, 3)
    llm_rag_result = handle_vector_search_and_llm(
        expanded_query, domain, context_history=conversation_history
    )

    if llm_rag_result and llm_rag_result.get("success"):
        answer = llm_rag_result['answer']
        sources = llm_rag_result.get("sources", [])
        # Lưu context
        topic = context_manager.extract_topic_from_response(user_input, answer)
        context_manager.add_conversation(user_id, user_input, answer, domain, topic)
        # Trả về luôn metadata gốc nếu muốn debug nguồn!
        return format_response(answer, source="rag+llm", metadata={
            "domain": domain,
            "sources": sources[:3]
        })


    # 7. Check responses.json nếu có
    json_match = handle_response_fallback(expanded_query, domain)
    if json_match:
        response = format_response(json_match, source="response")
        # Lưu context
        topic = context_manager.extract_topic_from_response(user_input, json_match)
        context_manager.add_conversation(user_id, user_input, json_match, domain, topic)
        return response

    # 8. Fallback: chỉ trả lời ngắn gọn/lịch sự hoặc log lại
    fallback_answer = handle_fallback_and_log(expanded_query, domain)
    context_manager.add_conversation(user_id, user_input, fallback_answer, domain, "fallback")
    
    return format_response(fallback_answer, source="fallback")

# === Thêm hàm utility để quản lý context ===
def get_user_context_summary(user_id: str) -> str:
    """Lấy tóm tắt context của user để debug"""
    contexts = context_manager.get_context(user_id)
    if not contexts:
        return "Chưa có lịch sử trò chuyện"
    
    summary = f"Lịch sử {len(contexts)} cuộc trò chuyện gần nhất:\n"
    for i, conv in enumerate(contexts[-3:], 1):
        summary += f"{i}. {conv['user_input'][:50]}... ({conv.get('topic', 'N/A')})\n"
    return summary

def clear_user_context(user_id: str):
    """Xóa context của user"""
    context_manager.clear_context(user_id)
    return f"Đã xóa lịch sử trò chuyện của user {user_id}"