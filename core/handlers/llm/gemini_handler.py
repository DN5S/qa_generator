# core/handlers/llm/gemini_handler.py

import asyncio
import logging
from typing import Optional

import google.genai as genai
from google.genai.types import GenerateContentConfig, GenerateContentResponse

from config.settings import Settings
from core.handlers.llm.base_handler import BaseLLMHandler
from core.registry import registry

logger = logging.getLogger(__name__)

@registry.register_handler("gemini")
class GeminiHandler(BaseLLMHandler):
	"""Gemini API와의 통신을 책임지는 구체적인 핸들러."""

	def __init__(self, settings: Settings):
		self.settings = settings
		logger.info("Initializing Gemini client with API key...")
		try:
			# API 키가 비어있는 경우 명시적인 오류 발생
			if not self.settings.llm.GEMINI_API_KEY:
				raise ValueError("GEMINI_API_KEY is not set in the environment or .env file.")
			api_key_str = self.settings.llm.GEMINI_API_KEY.get_secret_value()
			self.client = genai.Client(api_key=api_key_str)
			logger.info("Gemini client initialized successfully.")
		except (ValueError, Exception) as e:
			logger.critical(f"Failed to initialize Gemini client: {e}")
			raise

		self.semaphore = asyncio.Semaphore(settings.llm.MAX_CONCURRENT_REQUESTS)
		self.generation_config = GenerateContentConfig(response_mime_type="application/json")

	async def generate_async(self, prompt: str) -> Optional[str]:
			"""
			Gemini API에 비동기적으로 요청을 보내고, 순수한 텍스트 응답을 반환한다.
			API 호출 실패 시 설정된 횟수만큼 재시도한다.

			Args:
				prompt: Gemini API에 전달할 프롬프트.

			Returns:
				API 호출 성공 시 응답 텍스트(str), 최종 실패 시 None.
			"""
			logger.debug(f"Sending prompt to Gemini API. Length: {len(prompt)} chars.")
			async with self.semaphore:
				last_error: Optional[Exception] = None
				for attempt in range(self.settings.llm.API_RETRY_COUNT):
					try:
						logger.info(
							f"Requesting Gemini API... (Attempt {attempt + 1}/{self.settings.llm.API_RETRY_COUNT})"
						)

						response: GenerateContentResponse = await self.client.aio.models.generate_content(
							model=self.settings.llm.MODEL_NAME.value,
							contents=prompt,
							config=self.generation_config
						)

						if not response.text:
							raise ValueError("API response is empty.")

						logger.info("Received response from Gemini API.")
						return response.text

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
