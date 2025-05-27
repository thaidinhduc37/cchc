# server/utils/response_formatter.py

def format_response(text, source="chatbot"):
    return {
        "text": text,
        "source": source,
        "type": "answer"
    }