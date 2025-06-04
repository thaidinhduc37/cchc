import requests

class OllamaService:
    def __init__(self, model="gemma:2b"):
        self.base_url = "http://localhost:11434/api/generate"
        self.model = model

    def ask(self, prompt: str, instruction: str = None) -> str:
        full_prompt = f"{instruction.strip()}\n\n{prompt.strip()}" if instruction else prompt

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False
        }

        try:
            response = requests.post(self.base_url, json=payload)
            if response.status_code == 200:
                return response.json()["response"]
            else:
                print("❌ Lỗi từ Ollama:", response.status_code, response.text)
                return "Xin lỗi, tôi chưa thể trả lời ngay."
        except Exception as e:
            print("⚠️ Lỗi kết nối Ollama:", e)
            return "Không thể kết nối tới mô hình trả lời."
