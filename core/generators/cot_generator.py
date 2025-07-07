# core/generators/cot_generator.py

from typing import List, Type
from core.generators.dataset_generator import DatasetGenerator
from core.registry import registry
from schemas.datasets import ValidationSchema, Metadata, CotQA, CotLLMOutput

@registry.register_generator("cot")
class CoTGenerator(DatasetGenerator):
    """
    CoT(Chain of thought) QA 데이터셋을 생성하는 구체적인 구현체.
    """
    # GENERATOR_TYPE = "cot"

    def _get_validation_schema(self) -> Type[ValidationSchema]:
        return CotLLMOutput

    def _assemble_final_data(self, llm_output: CotLLMOutput, metadata: Metadata,
                             document_content: List[str]) -> ValidationSchema:
        """CoT QA 데이터의 최종 형태를 조립한다."""
        return CotQA(
            metadata=metadata,
            source_document_content=document_content,
            qa_pairs=llm_output.qa_pairs
        )
