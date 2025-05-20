# Quản lý lịch sử hội thoại và bước hiện tại theo session

history_map = {}
step_map = {}

def add_to_history(session_id, user_msg, bot_msg):
    if session_id not in history_map:
        history_map[session_id] = []
    history_map[session_id].append({"user": user_msg, "bot": bot_msg})

def get_history(session_id):
    if isinstance(session_id, list):
        session_id = "_".join(map(str, session_id))  # Chuyển danh sách thành chuỗi
    return history_map.get(session_id, [])

def clear_history(session_id):
    history_map.pop(session_id, None)
    step_map.pop(session_id, None)

def get_step_id(session_id):
    return step_map.get(session_id, None)

def set_step_id(session_id, step_id):
    step_map[session_id] = step_id