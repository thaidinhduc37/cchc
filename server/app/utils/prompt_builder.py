def build_prompt(message: str, context: list = None) -> str:
    prompt = ""
    if context:
        for item in context:
            prompt += f"Người dùng: {item['user']}\nTrợ lý: {item['bot']}\n"
    prompt += f"Người dùng: {message}\nTrợ lý:"
    return prompt
