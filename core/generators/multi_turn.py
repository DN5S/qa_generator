# core/generators/multi_turn.py

from pathlib import Path
from typing import Type, List

from core.generators.base import DatasetGenerator
from schemas.qa_models import MultiTurnQA, ValidationSchema

class MultiTurnGenerator(DatasetGenerator):
    """
    Multi-Turn QA 데이터셋을 생성하는 구체적인 구현체.
    """

    @property
    def _get_prompt_path(self) -> Path:
        return self.settings.PROMPTS_DIRECTORY / "multi_turn" / "prompt.md"

    @property
    def _get_schema_template_name(self) -> str:
        return "schema.json"

    @property
    def _get_output_directory(self) -> Path:
        """Multi-turn QA 데이터가 저장될 디렉터리 경로를 반환한다."""
        return self.settings.OUTPUT_BASE_DIRECTORY / "multi_turn"

    def _get_validation_schema(self) -> Type[ValidationSchema]:
        """Multi-turn QA 검증에 사용할 Pydantic 스키마를 반환한다."""
        return MultiTurnQA

    @property
    def _get_required_partials(self) -> List[str]:
        return ['system_prompt', 'metadata_rules', 'qa_answer_rules']
