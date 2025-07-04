# core/generators/dataset_generator.py

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Dict, Type, Optional, List

from config.settings import Settings
from core.handlers.file_handler import FileHandler
from core.handlers.llm.base_handler import BaseLLMHandler
from core.processors.response_processor import ResponseProcessor
from core.prompt_manager import PromptTemplateManager
import schemas.datasets as dataset_schemas
from schemas.datasets import ValidationSchema, Metadata, SingleTurnQA, CotQA, MultiTurnQA, MultiTurnConversation, BaseQASet

class DatasetGenerator(ABC):
	"""
	데이터셋 생성 파이프라인을 지휘하는 추상 베이스 클래스(ABC).

	이 클래스는 SRP, DIP 원칙에 따라 실제 작업을 각 전문가(Handler, Processor)에게
	위임하고, 자신은 전체 데이터 생성 흐름을 조율(Orchestration)하는 책임만 맡는다.
	구체적인 제너레이터(SingleTurn, CoT 등)는 이 클래스를 상속받아 구현된다.
	"""
	GENERATOR_TYPE: str = ""
	_validation_schema_map: Dict[str, Type[ValidationSchema]] = {}

	def __init__(self, settings: Settings, file_handler: FileHandler, llm_handler: BaseLLMHandler):
			"""
			DatasetGenerator를 초기화한다.

			의존성 주입(Dependency Injection)을 통해 필요한 모듈들을 주입받는다.

			Args:
				settings: 애플리케이션의 전역 설정 객체.
				file_handler: 파일 시스템 I/O를 담당하는 핸들러.
				llm_handler: LLM API 통신을 담당하는 핸들러.
			"""
			if not self.GENERATOR_TYPE:
				raise NotImplementedError(f"{self.__class__.__name__} must define a GENERATOR_TYPE.")

			self.settings = settings
			self.file_handler = file_handler
			self.llm_handler = llm_handler
			self.response_processor = ResponseProcessor()
			self.template_manager = PromptTemplateManager(self.settings.paths.PROMPTS_DIRECTORY)

			if not self.__class__._validation_schema_map:
				self.__class__._build_validation_schema_map()

	# --- Properties for Prompt Assembly ---

	@property
	def _get_prompt_path(self) -> Path:
		"""프롬프트 템플릿 파일의 경로를 반환해야 한다."""
		return self.settings.paths.PROMPTS_DIRECTORY / self.GENERATOR_TYPE / "prompt.md"

	@property
	def _get_schema_template_name(self) -> str:
		"""사용할 JSON 스키마 템플릿 파일명을 반환한다."""
		return "schema.json"

	@property
	def _get_required_partials(self) -> List[str]:
		"""모든 제너레이터가 공통으로 사용하는 partial 템플릿 목록."""
		return ['system_prompt', 'qa_answer_rules']

	def _get_extra_template_args(self) -> dict:
		"""
		프롬프트 템플릿에 주입할 추가적인 인자를 반환한다.
		자식 클래스는 이 메서드를 오버라이드하여 필요한 데이터를 제공할 수 있다.
		"""
		return {}

	# --- Prompt Assembly Methods ---

	@abstractmethod
	def _assemble_final_data(self, llm_output: ValidationSchema, metadata: Metadata,
	                         document_content: List[str]) -> ValidationSchema:
		"""
		LLM의 출력을 최종 저장될 데이터 구조로 조립한다.
		이 책임은 각 하위 제너레이터에 위임된다.

		Args:
			llm_output: LLM으로부터 받은, 검증된 Pydantic 모델.
			metadata: 생성된 메타데이터 객체.
			document_content: 원본 문서의 내용 (줄 단위 리스트).

		Returns:
			파일에 저장될 최종 Pydantic 모델 객체.
		"""
		pass

	def _assemble_prompt(self, **kwargs) -> str:
		"""
		메인 프롬프트 템플릿과 partial 템플릿들을 조합하여 최종 프롬프트를 조립한다.
		"""
		format_args = kwargs.copy()

		for partial_name in self._get_required_partials:
			partial_key = f'partials/_{partial_name}.md'
			try:
				format_args[partial_name] = self.template_manager.get_template(partial_key)
			except KeyError:
				# 경고가 아닌, 치명적 오류를 기록하고 시스템을 멈춘다.
				logging.critical(
					f"FATAL: Required partial template '{partial_key}' not found. The system cannot continue without its core components.")
				raise

		main_template_key = self._get_prompt_path.relative_to(self.settings.paths.PROMPTS_DIRECTORY).as_posix()
		main_template = self.template_manager.get_template(main_template_key)
		return main_template.format(**format_args)

	def _get_final_prompt(self, document: str) -> str:
		"""
		최종적으로 LLM에 전달될 프롬프트 문자열을 생성한다.
		"""
		schema_path = self._get_prompt_path.parent / self._get_schema_template_name
		schema_template_key = schema_path.relative_to(self.settings.paths.PROMPTS_DIRECTORY).as_posix()
		schema_template = self.template_manager.get_template(schema_template_key)

		format_args = {"document": document, "output_schema_template": schema_template}
		format_args.update(self._get_extra_template_args())

		return self._assemble_prompt(**format_args)

	@classmethod
	def _build_validation_schema_map(cls) -> None:
		""" schemas.datasets 모듈을 탐색하여 제너레이터 타입과 검증 스키마를 동적으로 매핑한다. """
		logging.info("Building LLM output validation schema map...")
		schema_map = {
			"singleturn": dataset_schemas.SingleTurnLLMOutput,
			"cot": dataset_schemas.CotLLMOutput,
			"multiturn": dataset_schemas.MultiTurnLLMOutput,
		}
		for gen_type, schema_class in schema_map.items():
			cls._validation_schema_map[gen_type] = schema_class
			logging.info(f"  Mapped LLM output schema: '{gen_type}' -> {schema_class.__name__}")

	def _get_validation_schema(self) -> Type[ValidationSchema]:
		""" 동적으로 빌드된 맵에서 현재 제너레이터에 맞는 검증 스키마를 반환한다. """
		schema = self._validation_schema_map.get(self.GENERATOR_TYPE)
		if not schema:
			raise ValueError(f"No validation schema found for GENERATOR_TYPE '{self.GENERATOR_TYPE}'.")
		return schema

	def _create_self_correction_prompt(self, original_prompt: str, broken_text: str) -> str:
		"""
		LLM에게 스스로 JSON 오류를 수정하도록 요청하는 프롬프트를 생성한다.

		Args:
		    original_prompt: 최초에 사용되었던 프롬프트.
		    broken_text: LLM이 생성한, 오류가 있는 텍스트.

		Returns:
		    자가 수정을 요청하는 새로운 프롬프트 문자열.
		"""
		logging.info("Creating self-correction prompt...")
		try:
			# 템플릿 관리자를 통해 자가 수정 프롬프트 템플릿을 가져온다.
			correction_template = self.template_manager.get_template('partials/_self_correction_prompt.md')

			# 템플릿에 실제 값을 채워 최종 프롬프트를 생성한다.
			return correction_template.format(
				original_prompt=original_prompt[:1500] + "...",  # 원본 프롬프트가 너무 길 경우를 대비
				broken_text=broken_text
			)
		except KeyError:
			logging.error("FATAL: Self-correction prompt template not found. Falling back to hardcoded prompt.")
			# 템플릿을 찾지 못할 경우를 대비한 fallback
			return (
				f"The JSON you previously generated is invalid. Please fix it.\n"
				f"Invalid JSON Output to fix:\n---\n{broken_text}\n---"
				f"Please provide ONLY the corrected, valid JSON object."
			)

	def _create_metadata(self, filepath: Path, file_index: int) -> Metadata:
		""" 프로그래밍 방식으로 메타데이터 객체를 생성한다. """
		return Metadata(
			identifier=f"{filepath.stem}_{self.GENERATOR_TYPE}_{file_index:05d}",
			dataset_version=self.settings.metadata.DATASET_VERSION,
			creator=self.settings.metadata.CREATOR,
			created_date=date.today(),
			source_document_id=filepath.name,
			subject=[self.GENERATOR_TYPE]  # 추후 확장 가능
		)

	async def _process_and_save(self, llm_output: ValidationSchema, filepath: Path, file_index: int,
	                            document_content: str):
		"""성공적인 LLM 출력을 최종 데이터로 조립하고 저장하는 로직을 캡슐화한다."""
		metadata = self._create_metadata(filepath, file_index)
		document_lines = document_content.splitlines()

		# 각 제너레이터에게 최종 데이터 조립을 위임한다.
		final_data = self._assemble_final_data(llm_output, metadata, document_lines)

		output_path = self.file_handler.get_output_path(self.GENERATOR_TYPE, filepath.name)
		await self.file_handler.write_file_async(output_path, final_data)

	async def execute_pipeline_for_file(self, filepath: Path, file_index: int) -> None:
		"""
		단일 파일에 대한 전체 데이터 생성 파이프라인을 지휘한다.

		이 메서드는 파일 읽기, 프롬프트 생성, API 호출, 응답 처리,
		그리고 자가 수정 시도 및 최종 파일 저장까지의 모든 과정을 조율한다.

		Args:
		    filepath: 처리할 대상 파일의 Path 객체.
		    file_index: 처리할 대상 파일의 index.
		"""
		filename = filepath.name
		logging.info(f"Executing pipeline for {filename}")
		try:
			# 1. 파일 읽기 (FileHandler 위임)
			document_content = await self.file_handler.read_file_async(filepath)

			# 2. 프롬프트 조립
			prompt = self._get_final_prompt(document_content)

			# 3. API 호출 (LLMHandler 위임)
			response_text = await self.llm_handler.generate_async(prompt, filename)
			if response_text is None:
				logging.error(f"[{filename}] Pipeline stopped because LLM response was None.")
				return

			# 4. 1차 응답 처리 (ResponseProcessor 위임)
			validation_schema = self._get_validation_schema()
			result = await self.response_processor.process_async(response_text, validation_schema, filename)

			# 5. 결과에 따른 분기 처리
			if result.is_successful:
				await self._process_and_save(result.validated_data, filepath, file_index, document_content)
				return

			# 6. 자가 수정 시도
			if result.needs_self_correction and self.settings.llm.ENABLE_SELF_CORRECTION:
				logging.info(f"[{filename}] Attempting self-correction...")
				correction_prompt = self._create_self_correction_prompt(prompt, result.broken_text)

				corrected_response_text = await self.llm_handler.generate_async(correction_prompt,
				                                                                f"{filename} (Correction)")
				if corrected_response_text:
					corrected_result = await self.response_processor.process_async(
						corrected_response_text,
						self._get_validation_schema(),
						filename
					)
					if corrected_result.is_successful:
						logging.info(f"[{filename}] Self-correction successful.")
						await self._process_and_save(corrected_result.validated_data, filepath, file_index,
						                             document_content)
						return

			# 7. 최종 실패 처리
			logging.error(f"[{filename}] All processing attempts failed.")
			output_path = self.file_handler.get_output_path(self.GENERATOR_TYPE, filename, is_broken=True)
			await self.file_handler.write_file_async(output_path, result.broken_text or response_text)

		except Exception as e:
			logging.critical(f"An unexpected critical error occurred during pipeline for {filename}: {e}",
			                 exc_info=True)

	async def run(self, num_files: Optional[int] = None) -> None:
		"""
        전체 데이터셋 생성 프로세스를 시작하고 관리한다.

        FileHandler를 통해 처리할 파일 목록을 가져오고, 각 파일에 대한
        파이프라인 실행을 비동기 태스크로 만들어 병렬 처리한다.

        Args:
            num_files: 처리할 최대 파일 수. None이면 모든 파일을 처리한다.
        """
		# FileHandler를 통해 처리할 파일 목록을 가져온다.
		files_to_process = self.file_handler.find_files(num_files=num_files)

		if not files_to_process:
			return

		tasks = []
		for i, filepath in enumerate(files_to_process):
			tasks.append(self.execute_pipeline_for_file(filepath, file_index=i + 1))

		await asyncio.gather(*tasks)
		logging.info("All file processing pipelines have been completed.")
