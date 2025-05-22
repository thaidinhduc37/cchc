# server/utils/response_formatter.py

def format_response(text: str, source: str = "unknown") -> dict:
    return {
        "text": text,
        "source": source
    }
