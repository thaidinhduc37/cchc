from common.utils import normalize_text
from common.data_loader import search_in_pdf
from fuzzywuzzy import process

def find_best_match(user_input, keywords):
    best_match, score = process.extractOne(user_input, keywords)
    return best_match if score > 80 else None  # Ngưỡng khớp 80%

def process_query(user_input, user_id, data, conversation_manager):
    user_input = normalize_text(user_input)
    domain = conversation_manager.identify_domain(user_input)

    print(f"User Input: {user_input}")
    print(f"Xác định domain: {domain}")

    if domain in data:
        print(f"📌 Dữ liệu của domain {domain}: {data[domain]}")  # 🛑 Debug
        for entry in data[domain]:
            best_match = find_best_match(user_input, entry['keywords'])
            if best_match:
                print(f"✅ Tìm thấy câu trả lời (match: {best_match}):", entry['text'])
                return entry['text']

    print("❌ Không tìm thấy câu trả lời")
    return "Xin lỗi, tôi không tìm thấy thông tin bạn cần."
