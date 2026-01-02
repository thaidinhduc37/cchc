import re

def split_text_into_chunks(text, max_length=500):
    # Tách theo dòng xuống hàng hoặc dấu chấm
    parts = re.split(r'[\\n\\r\\.]{1,}', text)
    return [p.strip() for p in parts if len(p.strip()) >= 30]
