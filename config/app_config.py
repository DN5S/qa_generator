# config/app_config.py

# config/app_config.py

from dataclasses import dataclass
from config.settings import Settings
from core.handlers.file_handler import FileHandler
from core.prompt_manager import PromptTemplateManager

@dataclass(frozen=True)
class AppConfig:
    """
    애플리케이션의 모든 의존성을 담는 데이터 클래스.
    이 객체는 main 함수에서 생성되어 필요한 곳으로 '주입'된다.
    """
    settings: Settings
    file_handler: FileHandler
    template_manager: PromptTemplateManager
