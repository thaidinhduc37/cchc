# llm_handler.py
import os
import requests
import json
import logging
from services.vector_rag.config import LLMConfig, LEGAL_PROMPT_TEMPLATE, DOMAIN_PROMPTS

logger = logging.getLogger(__name__)

class LLMHandler:
    """Xử lý LLM: auto dùng Ollama API nếu không có file local"""

    def __init__(self, model_path: str = None, config: LLMConfig = None, api_url: str = "http://localhost:11434", model_name: str = "gemma:2b"):
        self.config = config or LLMConfig()
        self.model_path = model_path
        self.api_url = api_url
        self.model_name = model_name

        # Nếu model_path là file gguf, ưu tiên dùng local LlamaCpp (nếu có)
        if self.model_path and os.path.exists(self.model_path):
            try:
                from langchain.llms import LlamaCpp
                from langchain.callbacks.manager import CallbackManager
                from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
                callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
                self.llm = LlamaCpp(
                    model_path=self.model_path,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                    top_p=self.config.top_p,
                    callback_manager=callback_manager,
                    verbose=False,
                    n_ctx=self.config.n_ctx,
                    n_threads=self.config.n_threads
                )
                self.use_ollama = False
                logger.info("✅ Local Gemma2B model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading local model: {str(e)}. Fallback to Ollama API.")
                self.use_ollama = True
        else:
            self.use_ollama = True

    def generate(self, prompt: str) -> str:
        if not self.use_ollama:
            return self.llm(prompt)
        # Call Ollama API
        try:
            url = f"{self.api_url}/api/generate"
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                    "num_ctx": self.config.n_ctx,
                    "num_predict": self.config.max_tokens
                }
            }
            response = requests.post(url, json=payload, stream=True)
            response.raise_for_status()
            result = ""
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line.decode("utf-8"))
                    if "response" in chunk:
                        result += chunk["response"]
                    if chunk.get("done", False):
                        break
            return result.strip()
        except Exception as e:
            logger.error(f"Ollama API call failed: {str(e)}")
            return "❌ Lỗi gọi LLM. Vui lòng thử lại sau."
