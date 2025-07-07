# core/generators/singleturn.py

from typing import List, Type
from core.generators.dataset_generator import DatasetGenerator
from core.registry import registry
from schemas.datasets import ValidationSchema, Metadata, SingleTurnQA, SingleTurnLLMOutput

@registry.register_generator("singleturn")
class SingleTurnGenerator(DatasetGenerator):
	"""
	단일 질문-답변(Single-Turn QA) 데이터셋을 생성하는 구현체.
	"""

	def _get_extra_template_args(self) -> dict:
		"""Single-turn 생성에 필요한 instruction 후보 목록을 반환한다."""
		template_key = "singleturn/instructions.txt"

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

	def _get_validation_schema(self) -> Type[ValidationSchema]:
		return SingleTurnLLMOutput

	def _assemble_final_data(self, llm_output: SingleTurnLLMOutput, metadata: Metadata,
	                         document_content: List[str]) -> ValidationSchema:
		"""Single-turn QA 데이터의 최종 형태를 조립한다."""
		return SingleTurnQA(
			metadata=metadata,
			source_document_content=document_content,
			qa_pairs=llm_output.qa_pairs
		)
