# server/utils/response_formatter.py

from datetime import datetime

def format_response(text: str, source: str = "unknown", metadata: dict = None) -> dict:
    """
    Format response với metadata
    Args:
        text: Nội dung trả lời
        source: Nguồn trả lời (rag, flow, ollama, etc)
        metadata: Thông tin bổ sung (sources, confidence, etc)
    """
    response = {
        "reply": text,
        "source": source,
        "type": "answer",
        "timestamp": datetime.now().isoformat()
    }
    
    # Thêm metadata nếu có
    if metadata:
        response["metadata"] = metadata
        
    return response