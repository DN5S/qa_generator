# core/generators/cot.py

from core.generators.base import DatasetGenerator


class CoTGenerator(DatasetGenerator):
    """
    CoT(Chain of thought) QA 데이터셋을 생성하는 구체적인 구현체.
    """
    GENERATOR_TYPE = "cot"
