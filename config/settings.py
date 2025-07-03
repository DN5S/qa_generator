# config/settings.py

from enum import Enum
from pathlib import Path
from typing import Final


# ================
# --- 상수 정의 ---
# ================
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

GEMINI_FLASH_MODEL: Final[str] = "gemini-2.0-flash"
GEMINI_PRO_MODEL: Final[str] = "gemini-1.5-pro"

# ======================
# --- 설정 클래스 정의 ---
# ======================

class GeminiModels(str, Enum):
    FLASH = GEMINI_FLASH_MODEL
    PRO = GEMINI_PRO_MODEL

class PathSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIRECTORY: Path = BASE_DIR / "data/input"
    PROMPTS_DIRECTORY: Path = BASE_DIR / "prompts"
    OUTPUT_BASE_DIRECTORY: Path = BASE_DIR / "data/output"

    QA_FILENAME_TEMPLATE: str = "{stem}_qa.json"
    BROKEN_FILENAME_TEMPLATE: str = "{stem}_qa_broken.txt"

class LLMSettings(BaseSettings):
    """LLM API 관련 설정을 관리한다."""
    model_config = SettingsConfigDict(env_prefix='LLM_', env_file='.env', extra='ignore')

    GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key.")
    API_RETRY_COUNT: int = Field(default=3, description="API 호출 실패 시 재시도 횟수.")
    API_RETRY_DELAY: int = Field(default=5, description="API 재시도 간의 대기 시간(초).")
    MODEL_NAME: GeminiModels = Field(default=GeminiModels.FLASH, description="사용할 Gemini 모델의 식별자.")
    MAX_CONCURRENT_REQUESTS: int = Field(default=5, description="동시 API 최대 요청 수를 제한한다.")
    ENABLE_SELF_CORRECTION: bool = Field(default=False,
                                         description="API 응답이 유효하지 않은 JSON일 경우, LLM에게 자가 수정을 요청하는 기능을 활성화한다.")

class MetadataSettings(BaseSettings):
    """생성될 데이터셋의 메타데이터 기본값을 관리한다."""
    model_config = SettingsConfigDict(env_prefix='METADATA_')
    DATASET_VERSION: str = Field(default="1.0", description="데이터셋의 버전.")
    CREATOR: str = Field(default="㈜엑스텐정보", description="데이터 생성 기관.")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # 경로 설정
    paths: PathSettings = PathSettings()
    llm: LLMSettings = LLMSettings()
    metadata: MetadataSettings = MetadataSettings()

# 애플리케이션 전역에서 사용될 설정(Settings) 클래스의 싱글톤 인스턴스.
settings = Settings()
