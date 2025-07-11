# config/settings.py

from enum import Enum
from pathlib import Path
from typing import Final

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

def _ensure_env_file_exists() -> None:
    """
    .env 파일이 존재하지 않으면 기본값으로 생성한다.
    최초 실행 시 필요한 환경 변수들을 포함한 .env 파일을 생성한다.
    """
    env_file_path = Path(".env")

    if not env_file_path.exists():
        print("Warning: .env file not found. Creating default .env file...")

        default_env_content = '''
        LLM_GEMINI_API_KEY=""
        LLM_OPENAI_API_KEY=""
        LLM_CLAUDE_API_KEY=""
        LLM_GEN_TEMPERATURE=1
        LLM_GEN_TOP_P=0.95
        LLM_GEN_MAX_OUTPUT_TOKENS=8192
        '''

        try:
            with open(env_file_path, 'w', encoding='utf-8') as f:
                f.write(default_env_content)
            print(f"Success: Created .env file at {env_file_path.absolute()}")
            print("Note: Please update LLM_GEMINI_API_KEY with your actual API key.")
        except Exception as e:
            print(f"Error: Failed to create .env file: {e}")
            raise

# Ensure .env file exists before defining Settings classes
_ensure_env_file_exists()

GEMINI_FLASH_MODEL: Final[str] = "gemini-2.0-flash"
GEMINI_PRO_MODEL: Final[str] = "gemini-1.5-pro"

OPENAI_GPT4_MODEL: Final[str] = "gpt-4o"
OPENAI_GPT4_MINI_MODEL: Final[str] = "gpt-4o-mini"
OPENAI_GPT35_MODEL: Final[str] = "gpt-3.5-turbo"

CLAUDE_SONNET_MODEL: Final[str] = "claude-3-7-sonnet-latest"
CLAUDE_HAIKU_MODEL: Final[str] = "claude-3-5-haiku-20241022"
CLAUDE_OPUS_MODEL: Final[str] = "claude-3-opus-20240229"

class GeminiModels(str, Enum):
    FLASH = GEMINI_FLASH_MODEL
    PRO = GEMINI_PRO_MODEL

class OpenAIModels(str, Enum):
    GPT4 = OPENAI_GPT4_MODEL
    GPT4_MINI = OPENAI_GPT4_MINI_MODEL
    GPT35_TURBO = OPENAI_GPT35_MODEL

class ClaudeModels(str, Enum):
    SONNET = CLAUDE_SONNET_MODEL
    HAIKU = CLAUDE_HAIKU_MODEL
    OPUS = CLAUDE_OPUS_MODEL

class PathSettings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIRECTORY: Path = BASE_DIR / "data/input"
    PROMPTS_DIRECTORY: Path = BASE_DIR / "prompts"
    OUTPUT_BASE_DIRECTORY: Path = BASE_DIR / "data/output"
    LOGS_DIRECTORY: Path = BASE_DIR / "logs"
    QA_FILENAME_TEMPLATE: str = "{stem}_qa.json"
    BROKEN_FILENAME_TEMPLATE: str = "{stem}_qa_broken.txt"

class LLMSettings(BaseSettings):
    """LLM API 관련 설정을 관리한다."""
    model_config = SettingsConfigDict(env_prefix='LLM_', env_file='.env', extra='ignore')

    # API Keys for different providers
    GEMINI_API_KEY: SecretStr = Field(default="", description="Google Gemini API Key.")
    OPENAI_API_KEY: SecretStr = Field(default="", description="OpenAI API Key.")
    CLAUDE_API_KEY: SecretStr = Field(default="", description="Anthropic Claude API Key.")

    # Common settings
    API_RETRY_COUNT: int = Field(default=3, description="API 호출 실패 시 재시도 횟수.")
    API_RETRY_DELAY: int = Field(default=5, description="API 재시도 간의 대기 시간(초).")
    MAX_CONCURRENT_REQUESTS: int = Field(default=5, description="동시 API 최대 요청 수를 제한한다.")
    MAX_RESPONSE_SIZE_MB: int = Field(default=1, description="처리할 최대 응답 크기(MB). DoS 공격 방지용.")
    ENABLE_SELF_CORRECTION: bool = Field(default=False,
                                         description="API 응답이 유효하지 않은 JSON일 경우, LLM에게 자가 수정을 요청하는 기능을 활성화한다.")

    # Model configurations (will be used by specific handlers)
    GEMINI_MODEL: GeminiModels = Field(default=GeminiModels.FLASH, description="사용할 Gemini 모델의 식별자.")
    OPENAI_MODEL: OpenAIModels = Field(default=OpenAIModels.GPT4_MINI, description="사용할 OpenAI 모델의 식별자.")
    CLAUDE_MODEL: ClaudeModels = Field(default=ClaudeModels.SONNET, description="사용할 Claude 모델의 식별자.")

    # Generation parameters
    GEN_TEMPERATURE: float = Field(default=1.0, description="LLM 생성 시 사용할 temperature 값.")
    GEN_TOP_P: float = Field(default=0.95, description="LLM 생성 시 사용할 top_p 값.")
    GEN_MAX_OUTPUT_TOKENS: int = Field(default=8192, description="LLM 생성 시 최대 출력 토큰 수.")

    # Backward compatibility
    @property
    def MODEL_NAME(self) -> GeminiModels:
        """Backward compatibility for existing Gemini handler."""
        return self.GEMINI_MODEL

class MetadataSettings(BaseSettings):
    """생성될 데이터셋의 메타데이터 기본값을 관리한다."""
    model_config = SettingsConfigDict(env_prefix='METADATA_')
    DATASET_VERSION: str = Field(default="1.0", description="데이터셋의 버전.")
    CREATOR: str = Field(default="㈜엑스텐정보", description="데이터 생성 기관.")

class LoggingSettings(BaseSettings):
    """로깅 관련 설정을 관리한다."""
    model_config = SettingsConfigDict(env_prefix='LOGGING_')
    DEFAULT_LEVEL: str = Field(default="INFO", description="기본 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)")

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
    logging: LoggingSettings = LoggingSettings()
