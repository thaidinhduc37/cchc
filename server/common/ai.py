import os
import requests
from dotenv import load_dotenv
from common.conversation import get_history
import PyPDF2

load_dotenv()

GEMMA_HOST = os.getenv("GEMMA_HOST")
MODEL_NAME = os.getenv("MODEL_NAME")
OLLAMA_URL = os.getenv("OLLAMA_URL")

# Gọi Gemma (nếu cần sử dụng riêng)
def call_gemma(prompt: str) -> str:
    try:
        response = requests.post(f"{GEMMA_HOST}/api/generate", json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        })
        response.raise_for_status()
        return response.json().get("response", "Không có phản hồi từ mô hình Gemma.")
    except Exception as e:
        print("❌ Lỗi khi gọi Gemma:", e)
        return "Bot gặp lỗi khi gọi Gemma, bạn thử lại sau nhé."

# Gọi Ollama với lịch sử hội thoại

def query_ai(message, session_id="default"):
    history = get_history(session_id)
    messages = []
    for item in history:
        messages.append({"role": "user", "content": item["user"]})
        messages.append({"role": "assistant", "content": item["bot"]})

    messages.append({"role": "user", "content": message})

    try:
        res = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False
        })
        res.raise_for_status()
        data = res.json()
        return data.get("message", {}).get("content", "Xin lỗi, tôi chưa có câu trả lời.")
    except Exception as e:
        print("❌ Lỗi khi gọi Ollama:", e)
        return "Bot gặp lỗi khi xử lý, bạn thử lại sau nhé."

# Trích xuất văn bản từ PDF

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"❌ Lỗi khi đọc file PDF: {e}")
    return text

# Gọi Ollama với context từ PDF

def query_ollama_with_pdf(message, pdf_path):
    context = extract_text_from_pdf(pdf_path)
    return query_ollama_with_context(message, context)

# Gọi Ollama với context dạng văn bản (dùng cho flow hoặc pdf)
def query_ollama_with_context(message, context, session_id="default"):
    history = get_history(session_id)
    messages = []

    messages.append({
        "role": "system",
        "content": f"Bạn là một trợ lý ảo tiếng Việt giúp công dân thực hiện thủ tục hành chính. Dưới đây là kịch bản tham khảo để hướng dẫn:\n\n{context}"
    })

    for item in history:
        messages.append({"role": "user", "content": item["user"]})
        messages.append({"role": "assistant", "content": item["bot"]})

    messages.append({"role": "user", "content": message})

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False
        })
        response.raise_for_status()
        return response.json().get("message", {}).get("content", "Không có phản hồi.")
    except Exception as e:
        print(f"❌ Lỗi khi gọi Ollama với context: {e}")
        return "Bot gặp lỗi khi xử lý, bạn thử lại sau nhé."

# Hàm kiểm tra mô hình hoạt động

def test_ollama_connection():
    try:
        response = requests.get(OLLAMA_URL.replace("/api/generate", "/api/tags"))
        if response.status_code == 200:
            return True
    except Exception:
        return False
    return False