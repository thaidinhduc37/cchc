import importlib

# Từ khóa ánh xạ sang tên thư mục lĩnh vực
KEYWORDS_TO_DOMAIN = {
    "căn cước": "cancuoc",
    "cccd": "cancuoc",
    "cmnd": "cancuoc",
    "chứng minh": "cancuoc",
    "tạm trú": "cutru",
    "cư trú": "cutru",
    "thường trú": "cutru",
    "hộ khẩu": "cutru",
    "xe": "dangkyxe",
    "đăng ký xe": "dangkyxe",
    "ô tô": "dangkyxe",
    "xe máy": "dangkyxe",
    "biển số": "dangkyxe",
}

def get_domain_module(domain_name):
    try:
        return importlib.import_module(f"domains.{domain_name}.domain")
    except ImportError:
        return None

def get_domain_context(message: str) -> str:
    message = message.lower()
    for keyword, domain in KEYWORDS_TO_DOMAIN.items():
        if keyword in message:
            mod = get_domain_module(domain)
            return mod.get_domain_context() if mod else "Không thể tải module lĩnh vực."
    return "Tôi chưa xác định được lĩnh vực bạn đang hỏi. Bạn vui lòng cung cấp thêm thông tin cụ thể."

def get_flow_handler(message: str):
    message = message.lower()
    for keyword, domain in KEYWORDS_TO_DOMAIN.items():
        if keyword in message:
            mod = get_domain_module(domain)
            return getattr(mod, "get_next_step", None)
    return None