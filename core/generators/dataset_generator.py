# core/generators/dataset_generator.py

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Dict, Type, Optional, List

from config.logging_config import context_filename
from config.app_config import AppConfig
from core.handlers.llm.base_handler import BaseLLMHandler
from core.processors.response_processor import ResponseProcessor
import schemas.datasets as dataset_schemas
from schemas.datasets import ValidationSchema, Metadata

logger = logging.getLogger(__name__)

class DatasetGenerator(ABC):
	"""
	데이터셋 생성 파이프라인을 지휘하는 추상 베이스 클래스(ABC).

	이 클래스는 SRP, DIP 원칙에 따라 실제 작업을 각 전문가(Handler, Processor)에게
	위임하고, 자신은 전체 데이터 생성 흐름을 조율(Orchestration)하는 책임만 맡는다.
	구체적인 제너레이터(SingleTurn, CoT 등)는 이 클래스를 상속받아 구현된다.
	"""
	_validation_schema_map: Dict[str, Type[ValidationSchema]] = {}

	def __init__(self, config: AppConfig, llm_handler: BaseLLMHandler, generator_type: str):
			"""
			DatasetGenerator 초기화.
			의존성 주입(Dependency Injection)을 통해 필요한 모듈들을 주입받는다.
			Args:
				config: 애플리케이션의 전역 설정 객체.
					- file_handler: 파일 시스템 I/O를 담당하는 핸들러.
					- template_manager: 프롬프트 템플릿을 관리하는 매니저.
				llm_handler: LLM API 통신을 담당하는 핸들러.
			"""
			if not generator_type:
				raise NotImplementedError(f"{self.__class__.__name__} must define a GENERATOR_TYPE.")

			self.type = generator_type
			self.config = config
			self.settings = config.settings
			self.file_handler = config.file_handler
			self.template_manager = config.template_manager
			self.llm_handler = llm_handler
			self.response_processor = ResponseProcessor()

			if not self.__class__._validation_schema_map:
				self.__class__._build_validation_schema_map()
				logger.info("Validation schema map built.")

	# --- Properties for Prompt Assembly ---

	@property
	def _get_prompt_path(self) -> Path:
		"""프롬프트 템플릿 파일의 경로를 반환해야 한다."""
		return self.settings.paths.PROMPTS_DIRECTORY / self.type / "prompt.md"

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
	def _get_validation_schema(self) -> Type[ValidationSchema]:
		"""
		LLM의 출력을 검증할 Pydantic 스키마 타입을 반환한다.
		이 책임은 각 하위 제너레이터에 위임된다.
		"""
		pass

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
				logger.critical(f"FATAL: Required partial template '{partial_key}' not found.")
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

		final_prompt = self._assemble_prompt(**format_args)
		logger.debug(f"Assembled final prompt:\n---PROMPT START---\n{final_prompt[:500]}...\n---PROMPT END---")
		return final_prompt

	@classmethod
	def _build_validation_schema_map(cls) -> None:
		""" schemas.datasets 모듈을 탐색하여 제너레이터 타입과 검증 스키마를 동적으로 매핑한다. """
		logger.info("Building LLM output validation schema map...")
		schema_map = {
			"singleturn": dataset_schemas.SingleTurnLLMOutput,
			"cot": dataset_schemas.CotLLMOutput,
			"multiturn": dataset_schemas.MultiTurnLLMOutput,
		}
		for gen_type, schema_class in schema_map.items():
			cls._validation_schema_map[gen_type] = schema_class
			logger.info(f"  Mapped LLM output schema: '{gen_type}' -> {schema_class.__name__}")

	def _create_self_correction_prompt(self, original_prompt: str, broken_text: str) -> str:
		"""
		LLM에게 스스로 JSON 오류를 수정하도록 요청하는 프롬프트를 생성한다.

		Args:
		    original_prompt: 최초에 사용되었던 프롬프트.
		    broken_text: LLM이 생성한, 오류가 있는 텍스트.

		Returns:
		    자가 수정을 요청하는 새로운 프롬프트 문자열.
		"""
		logger.info("Creating self-correction prompt...")
		logger.debug(f"Broken text for self-correction:\n---BROKEN TEXT START---\n{broken_text}\n---BROKEN TEXT END---")
		try:
			# 템플릿 관리자를 통해 자가 수정 프롬프트 템플릿을 가져온다.
			correction_template = self.template_manager.get_template('partials/_self_correction_prompt.md')

			# 템플릿에 실제 값을 채워 최종 프롬프트를 생성한다.
			return correction_template.format(
				original_prompt=original_prompt[:3000] + "...",  # 원본 프롬프트가 너무 길 경우를 대비
				broken_text=broken_text
			)
		except KeyError:
			logger.error("FATAL: Self-correction prompt template not found. Falling back to hardcoded prompt.")
			# 템플릿을 찾지 못할 경우를 대비한 fallback
			return (
				f"The JSON you previously generated is invalid. Please fix it.\n"
				f"Invalid JSON Output to fix:\n---\n{broken_text}\n---"
				f"Please provide ONLY the corrected, valid JSON object."
			)

	def _create_metadata(self, filepath: Path, file_index: int) -> Metadata:
		""" 프로그래밍 방식으로 메타데이터 객체를 생성한다. """
		metadata = Metadata(
			identifier=f"{filepath.stem}_{self.type}_{file_index:05d}",
			dataset_version=self.settings.metadata.DATASET_VERSION,
			creator=self.settings.metadata.CREATOR,
			created_date=date.today(),
			source_document_id=filepath.name,
			subject=[self.type]  # 추후 확장 가능
		)
		logger.debug(f"Created metadata: {metadata.model_dump_json()}")
		return metadata

	async def _process_and_save(self, llm_output: ValidationSchema, filepath: Path, file_index: int,
	                            document_content: str):
		"""성공적인 LLM 출력을 최종 데이터로 조립하고 저장하는 로직을 캡슐화한다."""
		metadata = self._create_metadata(filepath, file_index)
		document_lines = document_content.splitlines()

		# 각 제너레이터에게 최종 데이터 조립을 위임한다.
		final_data = self._assemble_final_data(llm_output, metadata, document_lines)
		logger.debug(f"Assembled final data for saving: {final_data.model_dump_json(indent=2)[:500]}...")

		output_path = self.file_handler.get_output_path(self.type, filepath.name)
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
		token = context_filename.set(filepath.name)
		logger.info(f"Executing pipeline for file index {file_index}")

		try:
			# 1. 파일 읽기 (FileHandler 위임)
			document_content = await self.file_handler.read_file_async(filepath)

			# 2. 프롬프트 조립
			prompt = self._get_final_prompt(document_content)

			# 3. API 호출 (LLMHandler 위임)
			response_text = await self.llm_handler.generate_async(prompt)
			if response_text is None:
				logger.error("Pipeline stopped: LLM response was None.")
				raise RuntimeError("LLM API call failed - response was None")

			# 4. 1차 응답 처리 (ResponseProcessor 위임)
			validation_schema = self._get_validation_schema()
			result = await self.response_processor.process_async(response_text, validation_schema, self.settings)

			# 5. 결과에 따른 분기 처리
			if result.is_successful:
				await self._process_and_save(result.validated_data, filepath, file_index, document_content)
				return

			# 6. 자가 수정 시도
			if result.needs_self_correction and self.settings.llm.ENABLE_SELF_CORRECTION:
				logger.info("Attempting self-correction...")
				correction_prompt = self._create_self_correction_prompt(prompt, result.broken_text)

				corrected_response_text = await self.llm_handler.generate_async(correction_prompt)
				if corrected_response_text:
					corrected_result = await self.response_processor.process_async(
						corrected_response_text, self._get_validation_schema(), self.settings
					)
					if corrected_result.is_successful:
						logger.info("Self-correction successful.")
						await self._process_and_save(
							corrected_result.validated_data, filepath, file_index, document_content
						)
						return

			# 7. 최종 실패 처리
			logger.error("All processing attempts failed.")
			output_path = self.file_handler.get_output_path(self.GENERATOR_TYPE, filepath.name, is_broken=True)
			await self.file_handler.write_file_async(output_path, result.broken_text or response_text)
			raise RuntimeError("All processing attempts failed - unable to generate valid output")

		except Exception as e:
			logger.critical(f"An unexpected critical error occurred during pipeline: {e}", exc_info=True)
			raise
		finally:
			context_filename.reset(token)

	async def run(self, num_files: Optional[int] = None) -> None:
		"""
        전체 데이터셋 생성 프로세스를 시작하고 관리한다.

        FileHandler를 통해 처리할 파일 목록을 가져오고, 각 파일에 대한
        파이프라인 실행을 비동기 태스크로 만들어 병렬 처리한다.
        MAX_CONCURRENT_REQUESTS 설정에 따라 동시 요청 수를 제한한다.

        Args:
            num_files: 처리할 최대 파일 수. None이면 모든 파일을 처리한다.
        """
		# FileHandler를 통해 처리할 파일 목록을 가져온다.
		files_to_process = self.file_handler.find_files(num_files=num_files)

		if not files_to_process:
			return

		# 동시성 제어를 위한 세마포어 생성
		max_concurrent = self.settings.llm.MAX_CONCURRENT_REQUESTS
		semaphore = asyncio.Semaphore(max_concurrent)
		logger.info(f"Processing {len(files_to_process)} files with max {max_concurrent} concurrent requests.")

		async def process_file_with_semaphore(filepath, file_index):
			"""세마포어로 동시성을 제어하면서 파일을 처리한다."""
			async with semaphore:
				await self.execute_pipeline_for_file(filepath, file_index)

		tasks = [process_file_with_semaphore(filepath, i + 1) for i, filepath in enumerate(files_to_process)]
		await asyncio.gather(*tasks)
		logger.info("All file processing pipelines have been completed.")
