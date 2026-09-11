"""Configuration and settings for SSE Learning Bot backend."""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded dynamically from environment at runtime."""
    
    @property
    def gemini_api_key(self) -> str:
        load_dotenv(override=True)
        key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
        return key.strip().strip('"').strip("'")

    @property
    def gemini_model(self) -> str:
        load_dotenv(override=True)
        return os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip().strip('"').strip("'")

    @property
    def deepgram_api_key(self) -> str:
        load_dotenv(override=True)
        key = os.getenv("DEEPGRAM_API_KEY", "")
        return key.strip().strip('"').strip("'")

    @property
    def deepgram_stt_model(self) -> str:
        load_dotenv(override=True)
        return os.getenv("DEEPGRAM_STT_MODEL", "nova-3").strip().strip('"').strip("'")

    @property
    def deepgram_tts_model(self) -> str:
        load_dotenv(override=True)
        return os.getenv("DEEPGRAM_TTS_MODEL", "aura-asteria-en").strip().strip('"').strip("'")

    @property
    def openai_api_key(self) -> str:
        load_dotenv(override=True)
        key = os.getenv("OPENAI_API_KEY", "")
        return key.strip().strip('"').strip("'")

    @property
    def openai_llm_model(self) -> str:
        load_dotenv(override=True)
        return os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini").strip().strip('"').strip("'")

    @property
    def BASE_URL(self) -> str:
        load_dotenv(override=True)
        return os.getenv("BASE_URL", "https://api.openai.com/v1").strip().strip('"').strip("'")

    @property
    def openrouter_api_key(self) -> str:
        load_dotenv(override=True)
        return os.getenv("OPENROUTER_API_KEY", "").strip('"').strip("'")

    @property
    def openrouter_model(self) -> str:
        load_dotenv(override=True)
        return os.getenv("OPENROUTER_MODEL", "openrouter/auto").strip('"').strip("'")

    @property
    def openrouter_base_url(self) -> str:
        load_dotenv(override=True)
        return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip('"').strip("'")

    @property
    def tavily_api_key(self) -> str:
        load_dotenv(override=True)
        return os.getenv("TAVILY_API_KEY", "").strip('"').strip("'")

    @classmethod
    def reload(cls):
        """Reload settings from environment."""
        load_dotenv(override=True)


# Global settings instance
settings = Settings()

