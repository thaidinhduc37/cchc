import requests
import os

api_key = os.getenv("GEMINI_API_KEY")

# Dùng v1beta và tên model chính xác này
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

headers = {'Content-Type': 'application/json'}
data = {
    "contents": [{
        "parts": [{"text": "Chào bạn, tôi quay lại dùng bản 1.5 Flash đây!"}]
    }]
}

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    print("✅ 1.5 Flash hoạt động!")
    print(response.json()['candidates'][0]['content']['parts'][0]['text'])
else:
    print(f"❌ Lỗi {response.status_code}: {response.text}")