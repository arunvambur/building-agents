import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Supported providers: "openai" | "ollama"
_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()


def get_llm() -> Any:
    if _PROVIDER == "ollama":
        return _get_ollama()
    return _get_openai()


def _get_openai() -> Any:
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set in environment or .env file.")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(api_key=api_key, model=model)


def _get_ollama() -> Any:
    from langchain_ollama import ChatOllama

    model = os.getenv("OLLAMA_MODEL", "gemma3")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    return ChatOllama(model=model, base_url=base_url)
