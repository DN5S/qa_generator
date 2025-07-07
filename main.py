# /main.py

import argparse
import asyncio
import importlib
import inspect
import logging
import pkgutil
from typing import Dict, Type, TypeAlias

from config.settings import settings
from config.logging_config import ContextFilter
from core.generators.dataset_generator import DatasetGenerator
from core.handlers.file_handler import FileHandler
from core.handlers.llm.base_handler import BaseLLMHandler
from core.prompt_manager import PromptTemplateManager

GeneratorClass: TypeAlias = Type[DatasetGenerator]
LLMHandlerClass: TypeAlias = Type[BaseLLMHandler]

def setup_logging() -> None:
	"""
	애플리케이션의 로깅 시스템을 초기화한다.
	로그는 파일(processing.log)과 콘솔 스트림으로 동시에 출력된다.
	"""
	log_format = '%(asctime)s - %(levelname)s - [%(filename_context)s] - [%(name)s:%(lineno)d] - %(message)s'
	logging.basicConfig(
		level=logging.INFO,
		format=log_format,
		handlers=[
			logging.FileHandler("processing.log", mode='w', encoding='utf-8'),
			logging.StreamHandler()
		],
		force=True
	)

	for handler in logging.getLogger().handlers:
		handler.addFilter(ContextFilter())

	logging.info("========================================")
	logging.info("Logging system initialized.")
	logging.info("========================================")


def discover_modules(package_path, package_name, base_class, suffix) -> Dict[str, Type]:
	"""
	지정된 패키지에서 특정 베이스 클래스를 상속하는 모듈들을 동적으로 탐색한다.

	Args:
		package_path: 탐색할 패키지의 경로.
		package_name: 패키지의 이름.
		base_class: 찾아야 할 부모 클래스.
		suffix: 클래스 이름에서 제거할 접미사.

	Returns:
		{키: 클래스} 형태의 딕셔너리.
	"""
	module_map: Dict[str, Type] = {}

	for module_info in pkgutil.walk_packages(package_path, f"{package_name}."):
		try:
			module = importlib.import_module(module_info.name)
			for name, obj in inspect.getmembers(module, inspect.isclass):
				if issubclass(obj, base_class) and obj is not base_class:
					key = name.replace(suffix, "").lower()
					module_map[key] = obj
					logging.info(f"Discovered {base_class.__name__}: '{key}' -> {name}")
		except Exception as e:
			logging.error(f"Failed to import or inspect module {module_info.name}: {e}")

	if not module_map:
		raise ImportError(f"No modules found for {base_class.__name__} in '{package_name}'.")

	return module_map

def setup_arg_parser(gen_choices: list, llm_choices: list) -> argparse.ArgumentParser:
	"""스크립트 실행을 위한 명령행 인터페이스(CLI) 인자를 설정하고 반환한다."""
	parser = argparse.ArgumentParser(
		description="A robust tool for generating AI-based QA datasets from Markdown documents."
	)
	parser.add_argument(
		"--type",
		type=str,
		choices=gen_choices,
		required=True,
		help="Type of dataset to generate. Discovered: %(choices)s"
	)
	parser.add_argument(
		"--llm",
		type=str,
		choices=llm_choices,
		default=llm_choices[0] if llm_choices else None, # 첫 번째 발견된 핸들러를 기본값으로
		required=True,
		help="LLM handler to use for generation. Discovered: %(choices)s"
	)
	parser.add_argument(
		"--num-files",
		type=int,
		default=None,
		help="Maximum number of files to process. If not specified, all found files will be processed."
	)
	parser.add_argument(
		"--self-correction",
		action='store_true',
		help="Enable self-correction mode. The LLM will attempt to fix its own JSON errors."
	)
	return parser


async def main() -> None:
	"""
	메인 실행 함수. 의존성을 생성 및 주입하고, 전체 파이프라인을 실행한다.
	"""
	setup_logging()

	try:
		# --- 1. 동적 탐색: 사용 가능한 모든 전문가들을 찾아낸다 ---
		import core.generators
		import core.handlers.llm

		generator_map = discover_modules(core.generators.__path__, core.generators.__name__, DatasetGenerator,
		                                 "Generator")
		llm_handler_map = discover_modules(core.handlers.llm.__path__, core.handlers.llm.__name__, BaseLLMHandler,
		                                   "Handler")

		# --- 2. 명령행 인자 설정 및 파싱 ---
		parser = setup_arg_parser(list(generator_map.keys()), list(llm_handler_map.keys()))
		args = parser.parse_args()

		if args.self_correction:
			settings.llm.ENABLE_SELF_CORRECTION = True
			logging.info("Self-correction mode ENABLED by command-line argument.")

		logging.info(f"Script execution started. Generation type: '{args.type}', LLM Handler: '{args.llm}'")

		# --- 3. 의존성 생성 (Dependency Creation) ---
		file_handler = FileHandler(
			data_directory=settings.paths.DATA_DIRECTORY,
			output_base_directory=settings.paths.OUTPUT_BASE_DIRECTORY
		)

		llm_handler_class = llm_handler_map[args.llm]
		llm_handler: BaseLLMHandler = llm_handler_class(settings)
		template_manager = PromptTemplateManager(settings.paths.PROMPTS_DIRECTORY)

		# --- 4. 의존성 주입 (Dependency Injection) ---
		generator_class = generator_map[args.type]
		generator = generator_class(
			settings=settings,
			file_handler=file_handler,
			llm_handler=llm_handler,
			template_manager=template_manager
		)

		# --- 5. 파이프라인 실행 ---
		await generator.run(num_files=args.num_files)

		logging.info("All tasks completed successfully. Shutting down.")

	except (ImportError, ValueError, FileNotFoundError) as e:
		logging.critical(f"Initialization failed: {e}", exc_info=True)
	except Exception as e:
		logging.critical(f"An unexpected critical error occurred: {e}", exc_info=True)


if __name__ == "__main__":
	asyncio.run(main())
