# response_processor.py

class ResponseProcessor:
    def format_legal_response(self, raw_response, domain):
        # Tuỳ chỉnh logic format cho từng domain, ví dụ chỉ return raw luôn
        return raw_response

    def add_confidence_indicator(self, response, confidence):
        # Thêm biểu tượng/tỉ lệ độ tin cậy vào câu trả lời
        return f"[Độ tin cậy: {confidence:.2%}] {response}"

    def add_source_references(self, response, source_docs):
        # Thêm tham chiếu nguồn vào cuối câu trả lời
        if not source_docs:
            return response
        refs = "\n\nNguồn tham khảo:\n" + "\n".join(
            f"- {doc.metadata.get('source', 'Không rõ')}" for doc in source_docs
        )
        return response + refs

class ResponseCache:
    def __init__(self):
        self.cache = {}

    def get(self, question, domain):
        key = (question, domain)
        return self.cache.get(key)

    def set(self, question, response, domain):
        key = (question, domain)
        self.cache[key] = response

    def clear(self):
        self.cache.clear()
