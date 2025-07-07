# core/registry.py

import inspect
import pkgutil
import importlib
import logging
from typing import Dict, Type, Callable, Any

logger = logging.getLogger(__name__)

class Registry:
    """
    애플리케이션의 확장 가능한 구성요소(제너레이터, 핸들러 등)를
    동적으로 등록하고 관리하는 중앙 레지스트리.
    """
    def __init__(self):
        self.generators: Dict[str, Type] = {}
        self.handlers: Dict[str, Type] = {}
        logger.info("Registry initialized.")

    def register_generator(self, name: str) -> Callable:
        """제너레이터 클래스를 등록하는 데코레이터."""
        def decorator(cls: Type) -> Type:
            logger.info(f"Registering generator '{name}' -> {cls.__name__}")
            self.generators[name] = cls
            # 원래 클래스를 그대로 반환
            return cls
        return decorator

    def register_handler(self, name: str) -> Callable:
        """LLM 핸들러 클래스를 등록하는 데코레이터."""
        def decorator(cls: Type) -> Type:
            logger.info(f"Registering handler '{name}' -> {cls.__name__}")
            self.handlers[name] = cls
            return cls
        return decorator

    def discover_components(self, package_path: str):
        """
        지정된 패키지 경로에서 모듈을 동적으로 임포트하여
        데코레이터를 통해 구성요소가 자동으로 등록되게 한다.
        """
        logger.info(f"Discovering components in '{package_path}'...")
        # pkgutil을 사용하여 패키지 내의 모든 모듈을 순회
        package = importlib.import_module(package_path)
        for _, module_name, _ in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
            try:
                # 모듈을 임포트하는 것만으로 @registry 데코레이터가 실행됨
                importlib.import_module(module_name)
            except Exception as e:
                logger.error(f"Failed to import module {module_name}: {e}")

# 애플리케이션 전역에서 사용될 레지스트리 싱글 인스턴스
# 이 인스턴스는 상태를 가지지만, 구성요소를 '등록'하는 행위 자체는
# 애플리케이션 시작 시 한 번만 일어나므로 테스트 용이성에 영향을 주지 않음.
registry = Registry()
