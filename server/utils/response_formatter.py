def format_response(raw: str) -> str:
    return raw.strip().replace("\n", " ").replace("  ", " ")
