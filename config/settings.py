# config/settings.py

from enum import Enum
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class GeminiModels(str, Enum):
    FLASH = 'gemini-2.0-flash'
    PRO = 'gemini-1.5-pro'

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # Gemini 설정
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key.")
    API_RETRY_COUNT: int = Field(default=3, description="API 호출 실패 시 재시도 횟수.")
    API_RETRY_DELAY: int = Field(default=5, description="API 재시도 간의 대기 시간(초).")
    MODEL_NAME: GeminiModels = Field(default=GeminiModels.FLASH, description="사용할 Gemini 모델의 식별자.")
    MAX_CONCURRENT_REQUESTS: int = Field(default=5, description="동시 API 최대 요청 수를 제한한다.")
    ENABLE_SELF_CORRECTION: bool = Field(default=False,
                                         description="API 응답이 유효하지 않은 JSON일 경우, LLM에게 자가 수정을 요청하는 기능을 활성화한다.")

    # 경로 설정
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIRECTORY: Path = BASE_DIR / "data/input"
    PROMPTS_DIRECTORY: Path = BASE_DIR / "prompts"
    OUTPUT_BASE_DIRECTORY: Path = BASE_DIR / "data/output"

# 애플리케이션 전역에서 사용될 설정(Settings) 클래스의 싱글톤 인스턴스.
settings = Settings()
