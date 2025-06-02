import os
import pandas as pd

def log_to_review_data(user_input: str, bot_response: str, domain: str):
    """
    Log câu hỏi chưa có đáp án vào review_data/{domain}/question.xlsx để admin bổ sung.
    Ghi thêm thời gian và trạng thái để admin duyệt sau này.
    """
    # Đảm bảo thư mục tồn tại
    log_dir = f"review_data/{domain}"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "question.xlsx")
    
    # Tạo file nếu chưa có
    columns = ["timestamp", "question", "answer", "status"]
    if os.path.exists(log_file):
        df = pd.read_excel(log_file)
    else:
        df = pd.DataFrame(columns=columns)
    
    # Không log trùng câu hỏi
    if not ((df["question"] == user_input).any()):
        from datetime import datetime
        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "question": user_input,
            "answer": bot_response or "",
            "status": "pending"  # Đánh dấu chờ admin duyệt
        }
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        df.to_excel(log_file, index=False)
