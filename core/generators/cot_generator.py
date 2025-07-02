# core/generators/cot_generator.py

from core.generators.dataset_generator import DatasetGenerator


class CoTGenerator(DatasetGenerator):
    """
    CoT(Chain of thought) QA 데이터셋을 생성하는 구체적인 구현체.
    """
    GENERATOR_TYPE = "cot"
