# core/handlers/llm/gemini_handler.py

import asyncio
import logging
from typing import Optional

import google.genai as genai
from google.genai.types import GenerateContentConfig, GenerateContentResponse

from config.settings import Settings
from core.handlers.llm.base_handler import BaseLLMHandler

class GeminiHandler(BaseLLMHandler):
	"""Gemini API와의 통신을 책임지는 구체적인 핸들러."""

	def __init__(self, settings: Settings):
		self.settings = settings
		logging.info("Initializing Gemini client with API key...")
		self.client = genai.Client(api_key=self.settings.llm.GEMINI_API_KEY)
		logging.info("Gemini client initialized successfully.")

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
			async with self.semaphore:
				last_error: Optional[Exception] = None
				for attempt in range(self.settings.llm.API_RETRY_COUNT):
					try:
						logging.info(f"Requesting Gemini API... (Attempt {attempt + 1}/{self.settings.llm.API_RETRY_COUNT})")

						response: GenerateContentResponse = await self.client.aio.models.generate_content(
							model=self.settings.llm.MODEL_NAME.value,
							contents=prompt,
							config=self.generation_config
						)

						if not response.text:
							raise ValueError("API response is empty.")

						logging.info("Received response from Gemini API.")
						return response.text

					except Exception as e:
						last_error = e
						logging.warning(
							f"API call failed (Attempt {attempt + 1}/{self.settings.llm.API_RETRY_COUNT}). Retrying in {self.settings.llm.API_RETRY_DELAY}s... Error: {e}"
						)
						if attempt < self.settings.llm.API_RETRY_COUNT - 1:
							await asyncio.sleep(self.settings.llm.API_RETRY_DELAY)

				logging.error(f"API call failed after {self.settings.llm.API_RETRY_COUNT} attempts. Last error: {last_error}")
				return None
