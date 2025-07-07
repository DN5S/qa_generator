# core/handlers/llm/base_handler.py

from abc import ABC, abstractmethod
from typing import Optional

class BaseLLMHandler(ABC):
    """
    모든 LLM API 핸들러가 상속해야 하는 추상 베이스 클래스(ABC).
    LLM API와의 상호작용에 대한 공통 인터페이스를 정의한다.
    """

    @abstractmethod
    async def generate_async(self, prompt: str) -> Optional[str]:
        """
        주어진 프롬프트를 사용하여 LLM으로부터 콘텐츠 생성을 비동기적으로 요청한다.

        구현하는 클래스는 API 호출, 재시도 로직, 동시성 제어를 책임져야 한다.
        성공 시 생성된 텍스트를 반환하고, 최종 실패 시 None을 반환해야 한다.

        Args:
            prompt: LLM에 전달할 전체 프롬프트 문자열.

        Returns:
            성공 시 LLM이 생성한 순수 텍스트(str) 응답, 실패 시 None.
        """
        pass
