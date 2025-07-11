# core/handlers/llm/claude_handler.py

import asyncio
import logging
from typing import Optional

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from config.settings import Settings
from core.handlers.llm.base_handler import BaseLLMHandler
from core.registry import registry

logger = logging.getLogger(__name__)

@registry.register_handler("claude")
class ClaudeHandler(BaseLLMHandler):
    """Anthropic Claude API와의 통신을 책임지는 구체적인 핸들러."""

    def __init__(self, settings: Settings):
        self.settings = settings
        logger.info("Initializing Claude client with API key...")
        try:
            # API 키가 비어있는 경우 명시적인 오류 발생
            if not self.settings.llm.CLAUDE_API_KEY:
                raise ValueError("CLAUDE_API_KEY is not set in the environment or .env file.")
            api_key_str = self.settings.llm.CLAUDE_API_KEY.get_secret_value()
            self.client = AsyncAnthropic(api_key=api_key_str)
            logger.info("Claude client initialized successfully.")
        except (ValueError, Exception) as e:
            logger.critical(f"Failed to initialize Claude client: {e}")
            raise

        self.semaphore = asyncio.Semaphore(settings.llm.MAX_CONCURRENT_REQUESTS)

    async def generate_async(self, prompt: str) -> Optional[str]:
        """
        Claude API에 비동기적으로 요청을 보내고, 순수한 텍스트 응답을 반환한다.
        API 호출 실패 시 설정된 횟수만큼 재시도한다.

        Args:
            prompt: Claude API에 전달할 프롬프트.

        Returns:
            API 호출 성공 시 응답 텍스트(str), 최종 실패 시 None.
        """
        logger.debug(f"Sending prompt to Claude API. Length: {len(prompt)} chars.")
        async with self.semaphore:
            last_error: Optional[Exception] = None
            for attempt in range(self.settings.llm.API_RETRY_COUNT):
                try:
                    logger.info(
                        f"Requesting Claude API... (Attempt {attempt + 1}/{self.settings.llm.API_RETRY_COUNT})"
                    )

                    # Claude API는 system과 user 메시지를 분리해서 처리
                    # JSON 응답을 요청하는 시스템 메시지 추가
                    system_message = "You must respond with valid JSON format only. Do not include any text outside the JSON structure."
                    messages: list[MessageParam] = [{"role": "user", "content": prompt}]

                    response = await self.client.messages.create(
                        model=self.settings.llm.CLAUDE_MODEL.value,
                        max_tokens=self.settings.llm.GEN_MAX_OUTPUT_TOKENS,
                        temperature=self.settings.llm.GEN_TEMPERATURE,
                        top_p=self.settings.llm.GEN_TOP_P,
                        system=system_message,
                        messages=messages
                    )

                    if not response.content or not response.content[0].text:
                        raise ValueError("API response is empty.")

                    logger.info("Received response from Claude API.")
                    return response.content[0].text

                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"API call failed (Attempt {attempt + 1}/{self.settings.llm.API_RETRY_COUNT}). Retrying in {self.settings.llm.API_RETRY_DELAY}s... Error: {e}"
                    )
                    if attempt < self.settings.llm.API_RETRY_COUNT - 1:
                        await asyncio.sleep(self.settings.llm.API_RETRY_DELAY)

            logger.error(
                f"API call failed after {self.settings.llm.API_RETRY_COUNT} attempts. Last error: {last_error}"
            )
            return None
