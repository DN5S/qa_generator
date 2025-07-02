# core/generators/base.py

import asyncio
import inspect
import json
import logging
import re
from pathlib import Path
from abc import ABC
from typing import Type, Union, Optional, List, Dict

from pydantic import ValidationError
from json_repair import repair_json
import google.genai as genai
from google.genai.types import GenerateContentConfig

from config.settings import Settings
from core.client import get_gemini_client
from core.prompt_manager import PromptTemplateManager
import schemas.datasets as dataset_schemas
from schemas.datasets import ValidationSchema


class DatasetGenerator(ABC):
	"""
	데이터셋 생성기를 위한 추상 베이스 클래스(ABC).
	모든 구체적인 생성기 클래스가 상속받아야 하는 공통 인터페이스와 핵심 로직을 정의한다.
	동적 스키마 탐색과 경로 구성을 통해 자식 클래스의 중복을 원천적으로 제거한다.
	"""
	GENERATOR_TYPE: str = ""
	_validation_schema_map: Dict[str, Type[ValidationSchema]] = {}

	def __init__(self, settings: Settings):
		if not self.GENERATOR_TYPE:
			raise NotImplementedError(f"{self.__class__.__name__} must define a GENERATOR_TYPE.")

		self.settings = settings
		self.client: genai.client.Client = get_gemini_client()
		self.template_manager = PromptTemplateManager(self.settings.PROMPTS_DIRECTORY)

		# 클래스가 처음 인스턴스화될 때만 스키마 맵을 동적으로 빌드한다.
		if not self.__class__._validation_schema_map:
			self.__class__._build_validation_schema_map()

		self._get_output_directory.mkdir(parents=True, exist_ok=True)
		self.semaphore = asyncio.Semaphore(self.settings.MAX_CONCURRENT_REQUESTS)

	@classmethod
	def _build_validation_schema_map(cls) -> None:
		"""
		schemas.datasets 모듈을 탐색하여 명명 규칙에 따라
		제너레이터 타입과 검증 스키마를 동적으로 매핑한다.
		"""
		logging.info("  Building validation schema map dynamically...")

		for name, schema_class in inspect.getmembers(dataset_schemas, inspect.isclass):
			if issubclass(schema_class, ValidationSchema) and name != 'ValidationSchema':
				# 예: 'SingleTurnQA' -> 'singleturn'
				# 1. '_qa' 또는 'QA' 접미사 제거 -> 'SingleTurn'
				base_name = name.removesuffix("QA").removesuffix("_qa")
				# 2. 소문자로 변환 -> 'singleturn'
				generator_type_key = base_name.lower()

				cls._validation_schema_map[generator_type_key] = schema_class
				logging.info(f"  Discovered and mapped schema: '{generator_type_key}' -> {name}")

		if not cls._validation_schema_map:
			raise ImportError("No validation schemas found in 'schemas/datasets.py'.")

	def _assemble_prompt(self, **kwargs) -> str:
		"""
		메인 프롬프트 템플릿과 partial 템플릿들을 읽어와 최종 프롬프트를 조립한다.
		"""
		format_args = kwargs.copy()

		for partial_name in self._get_required_partials:
			try:
				format_args[partial_name] = self.template_manager.get_template(f'partials/_{partial_name}.md')
			except KeyError:
				# 필요하다고 했는데 없으면, 경고를 남긴다.
				logging.warning(
					f"Partial '{partial_name}' required by {self.__class__.__name__} not found. Using empty string.")
				format_args[partial_name] = ""

		main_template_key = self._get_prompt_path.relative_to(self.settings.PROMPTS_DIRECTORY).as_posix()
		main_template = self.template_manager.get_template(main_template_key)
		return main_template.format(**format_args)


	@property
	def _get_prompt_path(self) -> Path:
		"""프롬프트 템플릿 파일의 경로를 반환해야 한다."""
		return self.settings.PROMPTS_DIRECTORY / self.GENERATOR_TYPE / "prompt.md"

	@property
	def _get_output_directory(self) -> Path:
		"""출력 디렉터리의 경로를 반환해야 한다."""
		return self.settings.OUTPUT_BASE_DIRECTORY / self.GENERATOR_TYPE

	@property
	def _get_schema_template_name(self) -> str:
		"""사용할 JSON 스키마 템플릿 파일명을 반환한다."""
		return "schema.json"

	@property
	def _get_required_partials(self) -> List[str]:
		"""모든 제너레이터가 공통으로 사용하는 partial 템플릿 목록."""
		return ['system_prompt', 'metadata_rules', 'qa_answer_rules']

	def _get_validation_schema(self) -> Type[ValidationSchema]:
		"""동적으로 빌드된 맵에서 현재 제너레이터에 맞는 검증 스키마를 반환한다."""
		schema = self._validation_schema_map.get(self.GENERATOR_TYPE)
		if not schema:
			raise ValueError(f"No validation schema found for GENERATOR_TYPE '{self.GENERATOR_TYPE}'.")
		return schema

	def _get_extra_template_args(self) -> dict:
		"""
		프롬프트 템플릿에 주입할 추가적인 인자를 반환한다.
		자식 클래스는 이 메서드를 오버라이드하여 필요한 데이터를 제공할 수 있다.
		"""
		return {}  # 기본적으로는 빈 딕셔너리를 반환한다.

	def _get_final_prompt(self, document: str) -> str:
		"""
		문서와 각 생성기 타입에 필요한 추가 데이터를 사용하여 최종 프롬프트를 조립한다.
		"""
		schema_template_key = (self._get_prompt_path.parent.relative_to(
			self.settings.PROMPTS_DIRECTORY) / self._get_schema_template_name).as_posix()
		schema_template = self.template_manager.get_template(schema_template_key)

		format_args = {"document": document, "output_schema_template": schema_template}
		format_args.update(self._get_extra_template_args())
		return self._assemble_prompt(**format_args)

	async def _generate_api_call(self, document_text: str, filename: str) -> Optional[Union[ValidationSchema, str]]:
		"""
		Gemini API에 비동기적으로 요청을 보내고, 지정된 스키마에 따라 응답을 검증한다.
		JSON 파싱/검증 오류 시 복구를 시도하며, API 호출 실패 시 재시도한다.
		"""
		prompt = self._get_final_prompt(document_text)
		validation_schema = self._get_validation_schema()
		generation_config = GenerateContentConfig(response_mime_type="application/json")
		last_error: Optional[Exception] = None

		for attempt in range(self.settings.API_RETRY_COUNT):
			response_text = None
			try:
				response = await self.client.aio.models.generate_content(
					model=self.settings.MODEL_NAME, contents=prompt, config=generation_config
				)
				response_text = response.text
				validated_data = validation_schema.model_validate_json(response_text)

				logging.info(f"Success on first try for {filename}.")
				return validated_data

			except (json.JSONDecodeError, ValidationError) as e:
				last_error = e
				logging.warning(f"Initial validation failed for {filename}. Attempting repair. Error: {e}")

				if response_text is None: continue

				# '자가 수정' 모드 활성화 시, LLM에게 수정 요청
				if self.settings.ENABLE_SELF_CORRECTION:
					logging.info(f"Attempting self-correction for {filename}...")
					correction_prompt = (
						f"The JSON you previously generated is invalid. Please fix it.\n"
						f"Original Prompt (for context):\n---\n{prompt[:1000]}...\n---\n"
						f"Invalid JSON Output:\n---\n{response_text}\n---\n"
						f"Validation Error:\n---\n{e}\n---\n"
						f"Please provide only the corrected, valid JSON object that adheres strictly to the schema."
					)

					try:
						correction_response = await self.client.aio.models.generate_content(
							model=self.settings.MODEL_NAME, contents=correction_prompt, config=generation_config
						)
						corrected_text = correction_response.text
						validated_data = validation_schema.model_validate_json(corrected_text)
						logging.info(f"Successfully self-corrected and validated JSON for {filename}.")
						return validated_data

					except Exception as self_correction_error:
						logging.warning(
							f"Self-correction failed for {filename}. Falling back to json_repair. Error: {self_correction_error}")

				# 자가 수정 실패 시 json_repair로 넘어간다.
				try:
					repaired_json_str = repair_json(response_text)
					validated_data = validation_schema.model_validate_json(repaired_json_str)
					logging.info(f"Successfully repaired and validated JSON for {filename}.")
					return validated_data

				except (json.JSONDecodeError, ValidationError) as repair_error:
					logging.error(
						f"JSON repair failed for {filename}. Saving original text. Repair Error: {repair_error}")
					return response_text

			except Exception as e:
				last_error = e
				logging.warning(
					f"API call for {filename} failed (Attempt {attempt + 1}/{self.settings.API_RETRY_COUNT}). Retrying... Error: {e}")
				await asyncio.sleep(self.settings.API_RETRY_DELAY)

		logging.error(
			f"API call failed for {filename} after {self.settings.API_RETRY_COUNT} attempts. Last error: {last_error}")
		return None

	async def process_file(self, filepath: Path) -> None:
		"""단일 파일을 비동기적으로 처리하여 QA 데이터를 생성하고 저장한다."""
		async with self.semaphore:
			logging.info(f"Processing file: {filepath.name}")
			try:
				document_content = await asyncio.to_thread(filepath.read_text, encoding='utf-8')
				result = await self._generate_api_call(document_content, filepath.name)

				if result is None:
					logging.error(f"Failed to generate data for {filepath.name}, skipping.")
					return

				if isinstance(result, ValidationSchema):
					output_filepath = self._get_output_directory / f"{filepath.stem}_qa.json"
					json_to_write = result.model_dump_json(indent=2, by_alias=True)
					await asyncio.to_thread(output_filepath.write_text, json_to_write, encoding='utf-8')
					logging.info(f"Successfully saved valid JSON to '{output_filepath}'")
				else:
					output_filepath = self._get_output_directory / f"{filepath.stem}_qa_broken.txt"
					await asyncio.to_thread(output_filepath.write_text, str(result), encoding='utf-8')
					logging.warning(f"Saved broken/unrepaired text to '{output_filepath}'")

			except Exception as e:
				logging.error(f"An unexpected error occurred while processing {filepath.name}: {e}", exc_info=True)

	async def run(self, num_files: Optional[int] = None) -> None:
		"""지정된 디렉토리의 파일을 찾아 비동기 처리 파이프라인을 실행한다."""
		logging.info(f"Searching for markdown files in '{self.settings.DATA_DIRECTORY}'...")
		all_files = list(self.settings.DATA_DIRECTORY.rglob('*.md'))

		if not all_files:
			logging.warning("No files found to process.")
			return

		files_to_process = all_files[:num_files] if num_files is not None else all_files
		logging.info(f"Processing a subset of {len(files_to_process)} files out of {len(all_files)} total.")
		tasks = [self.process_file(filepath) for filepath in files_to_process]
		await asyncio.gather(*tasks)
		logging.info("All file processing has been completed.")
