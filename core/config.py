from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_API_KEY_2: Optional[str] = None
    GEMINI_API_KEY_SECONDARY: Optional[str] = None
    MAX_CONTEXT_HISTORY: int = 5
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()