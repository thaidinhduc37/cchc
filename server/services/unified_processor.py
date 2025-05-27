# unified_processor.py - Bản sửa hoàn chỉnh sau khi rà lại lỗi dòng 117–118

import os
import json
import pandas as pd
from datetime import datetime

from utils.response_formatter import format_response
from services.ollama_service import OllamaService
from services.rag_system import DocumentRAGSystem

user_contexts = {}

def detect_domain(user_input: str) -> str:
    lowered = user_input.lower()
    if any(k in lowered for k in ["căn cước", "cccd", "chứng minh", "đổi thẻ"]):
        return "cancuoc"
    if any(k in lowered for k in ["hộ chiếu", "xuất nhập cảnh", "passport"]):
        return "xuatnhapcanh"
    if any(k in lowered for k in ["đăng ký xe", "biển số", "xe máy", "xe ô tô"]):
        return "dangkyxe"
    if any(k in lowered for k in ["thường trú", "tạm trú", "cư trú"]):
        return "cutru"
    return "xuatnhapcanh"

def detect_flow_intent(user_input: str) -> dict:
    lowered = user_input.lower().strip()
    guide_keywords = ["hướng dẫn", "làm hộ chiếu", "thủ tục", "cấp hộ chiếu", "xin hộ chiếu", "start", "quy trình"]
    procedure_types = {
        "lần đầu": ["lần đầu", "mới làm"],
        "cấp lại": ["cấp lại", "đổi mới"],
        "bị mất": ["mất", "thất lạc"],
        "hư hỏng": ["rách", "hư", "hỏng"]
    }

    intent_result = {"has_guide_intent": False, "procedure_type": None, "age_group": None, "confidence": 0.0}

    if any(keyword in lowered for keyword in guide_keywords):
        intent_result["has_guide_intent"] = True
        intent_result["confidence"] += 0.5

    for proc_type, keywords in procedure_types.items():
        if any(keyword in lowered for keyword in keywords):
            intent_result["procedure_type"] = proc_type
            intent_result["confidence"] += 0.3
            break

    if any(age in lowered for age in ["dưới 14"]):
        intent_result["age_group"] = "under_14"
        intent_result["confidence"] += 0.2
    elif any(age in lowered for age in ["trên 14", "từ 14"]):
        intent_result["age_group"] = "over_14"
        intent_result["confidence"] += 0.2

    return intent_result

def enhance_response_with_suggestions(text: str, input_text: str) -> str:
    # Tạm thời không chèn thêm gợi ý điều hướng trong phản hồi nữa vì frontend sẽ xử lý
    return text

def get_enhanced_context(user_id: str, user_input: str) -> str:
    if user_id in user_contexts:
        ctx = user_contexts[user_id]
        return f"Trước đó: {ctx.get('last_question', '')} | Trả lời: {ctx.get('last_answer', '')[:200]} | Hiện tại: {user_input}"
    return user_input

def save_qa_to_excel(domain, question, answer):
    try:
        os.makedirs(f"review_data/{domain}", exist_ok=True)
        path = f"review_data/{domain}/question.xlsx"
        if not os.path.exists(path):
            df = pd.DataFrame(columns=["question", "answer", "timestamp", "source"])
        else:
            df = pd.read_excel(path)

        df.loc[len(df)] = [question, answer, datetime.now().isoformat(), "ollama"]
        df.to_excel(path, index=False)
    except Exception as e:
        print(f"⚠️ Lỗi ghi log Q&A: {e}")

def get_user_context(user_id: str) -> dict:
    return user_contexts.get(user_id, {})

def clear_user_context(user_id: str) -> bool:
    if user_id in user_contexts:
        del user_contexts[user_id]
        return True
    return False

def get_conversation_stats() -> dict:
    total = len(user_contexts)
    domains = {}
    for ctx in user_contexts.values():
        d = ctx.get("domain", "unknown")
        domains[d] = domains.get(d, 0) + 1
    return {"total_users": total, "by_domain": domains, "timestamp": datetime.now().isoformat()}

def load_response_data(domain):
    path = f"dataset/{domain}/responses.json"
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("entries", [])
    except Exception as e:
        print(f"⚠️ Lỗi load responses.json: {e}")
        return []

def find_response_from_json(user_input: str, response_entries: list):
    lowered = user_input.lower()
    for entry in response_entries:
        for keyword in entry.get("keywords", []):
            if keyword.lower() in lowered:
                return "\n".join(entry.get("responses", []))
    return None

def find_similar_question(user_input: str, domain: str, threshold: float = 0.65):
    path = f"dataset/{domain}/question.xlsx"
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_excel(path)
        df.columns = df.columns.str.strip().str.lower()
        questions = df["question"].fillna("").tolist()
        answers = df["answer"].fillna("").tolist()
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vectorizer = TfidfVectorizer(ngram_range=(1, 2)).fit(questions + [user_input])
        vecs = vectorizer.transform(questions + [user_input])
        similarities = cosine_similarity(vecs[-1], vecs[:-1]).flatten()
        best_idx = similarities.argmax()
        best_score = similarities[best_idx]
        if best_score >= threshold:
            return answers[best_idx]
    except Exception as e:
        print(f"⚠️ Lỗi tìm câu hỏi gần giống: {e}")
    return None

def process_user_query(user_input, user_id, domain=None):
    user_input = user_input.strip()
    if not user_input:
        return format_response("❓ Vui lòng nhập câu hỏi của bạn.", source="system")

    lowered = user_input.lower()
    if not domain:
        domain = detect_domain(lowered)

    flow_intent = detect_flow_intent(user_input)
    enhanced_input = get_enhanced_context(user_id, user_input)

    response_entries = load_response_data(domain)
    matched_response = find_response_from_json(enhanced_input, response_entries)

    if matched_response:
        enhanced_response = enhance_response_with_suggestions(matched_response, user_input)
        user_contexts[user_id] = {
            "last_question": user_input,
            "last_answer": enhanced_response,
            "domain": domain,
            "timestamp": datetime.now().isoformat()
        }
        return format_response(enhanced_response, source="response")

    matched_similar = find_similar_question(enhanced_input, domain, threshold=0.6)
    if matched_similar:
        enhanced_response = enhance_response_with_suggestions(matched_similar, user_input)
        user_contexts[user_id] = {
            "last_question": user_input,
            "last_answer": enhanced_response,
            "domain": domain,
            "timestamp": datetime.now().isoformat()
        }
        return format_response(enhanced_response, source="question.xlsx")

    try:
        rag = DocumentRAGSystem(vector_store_path=f"vector_store/{domain}")
        results = rag.vector_store.search(enhanced_input, k=3, score_threshold=0.5)
        for res in results:
            chunk = res["chunk_text"].lower()
            banned_keywords = ["vương đình huệ", "nguyễn phú trọng", "quốc hội", "chủ tịch", "tổng bí thư"]
            if not any(b in chunk for b in banned_keywords):
                enhanced = enhance_response_with_suggestions(res["chunk_text"], user_input)
                user_contexts[user_id] = {
                    "last_question": user_input,
                    "last_answer": enhanced,
                    "domain": domain,
                    "timestamp": datetime.now().isoformat()
                }
                return format_response(enhanced, source="vector")
    except Exception as e:
        print(f"⚠️ Lỗi RAG: {e}")

    try:
        ollama = OllamaService()
        instruction = f"""Bạn là chatbot hỗ trợ Dịch vụ công Việt Nam, chuyên về lĩnh vực {domain}.
Quy tắc:
- Trả lời chính xác, không bịa đặt
- Không đề cập thông tin chính trị hay tên lãnh đạo
- Trả lời ngắn gọn, dễ hiểu, thân thiện
- Nếu không chắc chắn, gợi ý liên hệ cơ quan chức năng
- Có thể gợi ý hướng dẫn nếu phù hợp
Context: {enhanced_input}"""
        raw = ollama.ask(user_input, instruction=instruction)
        banned_keywords = ["vương đình huệ", "nguyễn phú trọng", "chủ tịch", "quốc hội", "tổng bí thư"]
        if any(b in raw.lower() for b in banned_keywords):
            os.makedirs("logs", exist_ok=True)
            with open("logs/flagged_answers.txt", "a", encoding="utf-8") as f:
                f.write(f"[BLOCKED - {datetime.now().isoformat()}] {user_input} → {raw}\n")
            raw = "❌ Tôi chỉ hỗ trợ các vấn đề về Dịch vụ công. Vui lòng hỏi về thủ tục hành chính."
        final = enhance_response_with_suggestions(raw, user_input)
        if "không thể hỗ trợ" not in final.lower():
            save_qa_to_excel(domain, user_input, final)
        user_contexts[user_id] = {
            "last_question": user_input,
            "last_answer": final,
            "domain": domain,
            "timestamp": datetime.now().isoformat(),
            "source": "ollama"
        }
        return format_response(final, source="ollama")
    except Exception as e:
        print(f"⚠️ Lỗi Ollama: {e}")
        return format_response("⚠️ Hệ thống gặp lỗi. Vui lòng thử lại sau.", source="error")
