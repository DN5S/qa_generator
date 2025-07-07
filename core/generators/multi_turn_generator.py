# core/generators/multiturn.py

from typing import List, Type
from core.generators.dataset_generator import DatasetGenerator
from core.registry import registry
from schemas.datasets import ValidationSchema, Metadata, MultiTurnQA, MultiTurnConversation, MultiTurnLLMOutput

@registry.register_generator("multiturn")
class MultiTurnGenerator(DatasetGenerator):
    """
    Multi-Turn QA 데이터셋을 생성하는 구체적인 구현체.
    """
    # GENERATOR_TYPE = "multiturn"

    def _get_validation_schema(self) -> Type[ValidationSchema]:
        return MultiTurnLLMOutput

    def _assemble_final_data(self, llm_output: MultiTurnLLMOutput, metadata: Metadata,
                             document_content: List[str]) -> ValidationSchema:
        """Multi-turn 대화 데이터의 최종 형태를 조립한다."""
        conversation = MultiTurnConversation(
            metadata=metadata,
            source_document_content=document_content,
            turns=llm_output.turns
        )
        return MultiTurnQA(conversations=[conversation])
