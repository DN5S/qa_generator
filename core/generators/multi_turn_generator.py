# core/generators/multiturn.py

from core.generators.dataset_generator import DatasetGenerator

class MultiTurnGenerator(DatasetGenerator):
    """
    Multi-Turn QA 데이터셋을 생성하는 구체적인 구현체.
    """
    GENERATOR_TYPE = "multiturn"
