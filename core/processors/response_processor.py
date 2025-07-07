# core/processors/response_processor.py

import json
import logging
from typing import Optional, Type

from json_repair import repair_json
from pydantic import ValidationError

from schemas.datasets import ValidationSchema
from config.settings import Settings

logger = logging.getLogger(__name__)

class ProcessingResult:
	"""
	ResponseProcessor의 처리 결과를 담는 데이터 클래스.
	성공, 실패, 자가 수정 필요 등 다양한 상태를 명확하게 표현한다.
	"""
	def __init__(self, validated_data: Optional[ValidationSchema] = None, broken_text: Optional[str] = None, needs_self_correction: bool = False):
		self.validated_data = validated_data
		self.broken_text = broken_text
		self.needs_self_correction = needs_self_correction

	@property
	def is_successful(self) -> bool:
		return self.validated_data is not None

class ResponseProcessor:
	"""
	LLM API의 텍스트 응답을 검증, 복구, 처리하는 책임을 맡는다.
	"""

	@staticmethod
	async def process_async(
		response_text: str,
		validation_schema: Type[ValidationSchema],
		settings: Settings,
	) -> ProcessingResult:
		"""
		주어진 응답 텍스트에 대해 검증 및 복구 파이프라인을 비동기적으로 실행한다.

		Args:
			response_text: API 핸들러로부터 받은 원본 텍스트 응답.
			validation_schema: 응답을 검증할 Pydantic 스키마 클래스.
			settings: 애플리케이션 설정 객체.

		Returns:
			처리의 최종 결과를 담은 ProcessingResult 객체.
		"""
		logger.debug(
			f"Received raw response from LLM:\n---RAW RESPONSE START---\n{response_text[:500]}...\n---RAW RESPONSE END---")

		max_size = settings.llm.MAX_RESPONSE_SIZE_MB * 1024 * 1024
		if len(response_text.encode('utf-8')) > max_size:
			logger.error(f"Response size exceeds the limit of {settings.llm.MAX_RESPONSE_SIZE_MB}MB. "
			             f"Size: {len(response_text.encode('utf-8'))} bytes. Aborting.")
			return ProcessingResult(broken_text="Response too large.", needs_self_correction=False)

		# 1. 1차 검증 시도
		try:
			validated_data = validation_schema.model_validate_json(response_text)
			logger.info("Success on first validation attempt.")
			return ProcessingResult(validated_data=validated_data)
		except (json.JSONDecodeError, ValidationError) as e:
			logger.warning(f"Initial validation failed. Attempting to repair JSON. Error: {e}")
		# 2. 1차 검증 실패 시, JSON 복구 시도
		try:
			repaired_json_str = repair_json(response_text)
			logger.debug(
				f"Repaired JSON string:\n---REPAIRED JSON START---\n{repaired_json_str}\n---REPAIRED JSON END---")
			validated_data = validation_schema.model_validate_json(repaired_json_str)
			logger.info(f"Successfully repaired and validated JSON.")
			return ProcessingResult(validated_data=validated_data)
		except (json.JSONDecodeError, ValidationError) as repair_error:
			logger.error(f"JSON repair failed. Error: {repair_error}")
			return ProcessingResult(broken_text=response_text, needs_self_correction=True)
