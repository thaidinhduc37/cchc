import os
import json
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from services.vector_db import VectorDatabase
from services.ollama_service import OllamaService
from utils.response_formatter import format_response
from services.flow_engine import FlowEngine

flow_engine = FlowEngine()

def load_response_data(domain):
    path = f"dataset/{domain}/responses.json"
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("entries", [])
    except:
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
        df.columns = df.columns.str.strip().str.lower()  # normalize
        questions = df["question"].fillna("").tolist()
        answers = df["answer"].fillna("").tolist()

        vectorizer = TfidfVectorizer().fit(questions + [user_input])
        vecs = vectorizer.transform(questions + [user_input])
        similarities = cosine_similarity(vecs[-1], vecs[:-1]).flatten()

        best_idx = similarities.argmax()
        best_score = similarities[best_idx]

        if best_score >= threshold:
            return answers[best_idx]

    except Exception as e:
        print("⚠️ Lỗi tìm câu hỏi gần giống:", e)

    return None

def detect_flow_key_from_input(user_input: str):
    lowered = user_input.lower()
    if "dưới 14" in lowered:
        return "cap_con_duoi_14"
    elif "mất" in lowered:
        return "cap_doi_mat_the"
    elif "đổi" in lowered:
        return "cap_doi_tu_14_co_vneid"
    elif "lần đầu" in lowered:
        return "cap_lan_dau_khong_vneid"
    return None

def save_qa_to_excel(domain, question, answer):
    os.makedirs(f"dataset/{domain}", exist_ok=True)
    path = f"dataset/{domain}/question.xlsx"
    if not os.path.exists(path):
        df = pd.DataFrame(columns=["question", "answer"])
    else:
        df = pd.read_excel(path)

    df.loc[len(df)] = [question, answer]
    df.to_excel(path, index=False)

def process_user_query(user_input, user_id, domain="xuatnhapcanh"):
    lowered = user_input.strip().lower()
    response_entries = load_response_data(domain)

    # 1. Nếu đang trong flow → điều hướng tiếp
    if user_id in flow_engine.user_flows:
        if any(k in lowered for k in ["xong", "kết thúc", "thoát"]):
            return format_response("✅ Đã kết thúc hướng dẫn.", source="flow")
        if any(k in lowered for k in ["tiếp", "tiếp theo", "bước tiếp"]):
            step = flow_engine.next_step(user_id)
            return format_response(step.get("text", ""), source="flow")
        if any(k in lowered for k in ["quay lại", "bước trước"]):
            step = flow_engine.previous_step(user_id)
            return format_response(step.get("text", ""), source="flow")
        step = flow_engine.get_step(user_id)
        return format_response(step.get("text", ""), source="flow")

    # 2. Chỉ kích hoạt flow nếu có ý định rõ ràng từ người dùng
    if any(k in lowered for k in ["hướng dẫn", "bắt đầu", "mở hướng dẫn", "làm từng bước"]):
        flow_key = detect_flow_key_from_input(lowered) or "mac_dinh"
        step = flow_engine.start_flow(user_id, flow_key)
        return format_response(step.get("text", ""), source="flow")

    # 3. Trả lời theo mẫu response.json
    matched_response = find_response_from_json(user_input, response_entries)
    if matched_response:
        return format_response(matched_response, source="response")

    # 4. Tìm câu hỏi gần giống trong question.xlsx
    matched_similar = find_similar_question(user_input, domain)
    if matched_similar:
        return format_response(matched_similar, source="question.xlsx")

    # 5. Truy vấn từ vector
    vdb = VectorDatabase()
    results = vdb.search(domain, user_input, top_k=3)
    if results and results[0][1] >= 0.65:
        return format_response(results[0][0], source="vector")

    # 6. Fallback sang Ollama
    ollama = OllamaService()
    ollama_answer = ollama.ask(
        user_input,
        instruction="Trả lời ngắn gọn, đúng trọng tâm, không bịa đặt."
    )
    save_qa_to_excel(domain, user_input, ollama_answer)
    return format_response(ollama_answer, source="ollama")
