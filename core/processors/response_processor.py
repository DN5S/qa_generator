# core/processors/response_processor.py

import json
import logging
from typing import Optional, Type

from json_repair import repair_json
from pydantic import ValidationError

from schemas.datasets import ValidationSchema

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
	) -> ProcessingResult:
		"""
		주어진 응답 텍스트에 대해 검증 및 복구 파이프라인을 비동기적으로 실행한다.

		Args:
			response_text: API 핸들러로부터 받은 원본 텍스트 응답.
			validation_schema: 응답을 검증할 Pydantic 스키마 클래스.

		Returns:
			처리의 최종 결과를 담은 ProcessingResult 객체.
		"""
		# 1. 1차 검증 시도
		try:
			validated_data = validation_schema.model_validate_json(response_text)
			logging.info("Success on first validation attempt.")
			return ProcessingResult(validated_data=validated_data)
		except (json.JSONDecodeError, ValidationError) as e:
			logging.warning(f"Initial validation failed. Attempting to repair JSON. Error: {e}")
		# 2. 1차 검증 실패 시, JSON 복구 시도
		try:
			repaired_json_str = repair_json(response_text)
			validated_data = validation_schema.model_validate_json(repaired_json_str)
			logging.info("Successfully repaired and validated JSON.")
			return ProcessingResult(validated_data=validated_data)
		except (json.JSONDecodeError, ValidationError) as repair_error:
			logging.error(f"JSON repair failed. Error: {repair_error}")
			return ProcessingResult(broken_text=response_text, needs_self_correction=True)
