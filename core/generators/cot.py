# core/generators/cot.py

from pathlib import Path
from typing import Type, List

from core.generators.base import DatasetGenerator
from schemas.qa_models import ValidationSchema, CotQA


class CoTGenerator(DatasetGenerator):
    """
    CoT(Chain of thought) QA 데이터셋을 생성하는 구체적인 구현체.
    """

    @property
    def _get_prompt_path(self) -> Path:
        return self.settings.PROMPTS_DIRECTORY / "cot" / "prompt.md"

    @property
    def _get_schema_template_name(self) -> str:
        return "schema.json"

    @property
    def _get_output_directory(self) -> Path:
        """CoT QA 데이터가 저장될 디렉터리 경로를 반환한다"""
        return self.settings.OUTPUT_BASE_DIRECTORY / "cot"

    def _get_validation_schema(self) -> Type[ValidationSchema]:
        """CoT QA 검증에 사용할 Pydantic 스키마를 반환한다."""
        return CotQA

    @property
    def _get_required_partials(self) -> List[str]:
        return ['system_prompt', 'metadata_rules', 'qa_answer_rules']
