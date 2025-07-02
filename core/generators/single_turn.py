# core/generators/single_turn.py

from pathlib import Path
from typing import Type, List

from core.generators.base import DatasetGenerator
from schemas.qa_models import SingleTurnQA, ValidationSchema

class SingleTurnGenerator(DatasetGenerator):
	"""
	단일 질문-답변(Single-Turn QA) 데이터셋을 생성하는 구현체.
	"""

	@property
	def _get_prompt_path(self) -> Path:
		return self.settings.PROMPTS_DIRECTORY / "single_turn" / "prompt.md"

	@property
	def _get_schema_template_name(self) -> str:
		return "schema.json"

	@property
	def _get_output_directory(self) -> Path:
		"""Single-turn QA 데이터가 저장될 디렉터리 경로를 반환한다."""
		return self.settings.OUTPUT_BASE_DIRECTORY / "single_turn"

	def _get_validation_schema(self) -> Type[ValidationSchema]:
		"""Single-turn QA 검증에 사용할 Pydantic 스키마를 반환한다."""
		return SingleTurnQA

	@property
	def _get_required_partials(self) -> List[str]:
		return ['system_prompt', 'metadata_rules', 'qa_answer_rules']

	# --- SingleTurnGenerator 보조 메서드 ---

	def _get_extra_template_args(self) -> dict:
		"""Single-turn 생성에 필요한 instruction 후보 목록을 반환한다."""
		template_key = "single_turn/instructions.txt"

		try:
			instructions_content = self.template_manager.get_template(template_key)
			lines = instructions_content.splitlines()
			loaded_instructions = [line.strip() for line in lines if line.strip()]

			if not loaded_instructions:
				raise ValueError(f"Instruction template '{template_key}' is empty.")

			return {
				"instruction_candidates": "\n".join(
					f"{i + 1}. {c}" for i, c in enumerate(loaded_instructions)
				)
			}
		except KeyError:
			raise
