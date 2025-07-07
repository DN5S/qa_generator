# /main.py

import argparse
import asyncio
import importlib
import inspect
import logging
import pkgutil
from datetime import datetime
from typing import Dict, Type, TypeAlias

from config.settings import settings
from config.logging_config import ContextFilter
from core.generators.dataset_generator import DatasetGenerator
from core.handlers.file_handler import FileHandler
from core.handlers.llm.base_handler import BaseLLMHandler
from core.prompt_manager import PromptTemplateManager

GeneratorClass: TypeAlias = Type[DatasetGenerator]
LLMHandlerClass: TypeAlias = Type[BaseLLMHandler]

def setup_logging(level: str) -> None:
	"""
	애플리케이션의 로깅 시스템을 초기화한다.
	로그는 파일(processing.log)과 콘솔 스트림으로 동시에 출력된다.
	Args:
		level: 로그 레벨
	"""
	# 1. 로그 레벨 설정
	log_level = getattr(logging, level.upper(), logging.INFO)

	# 2. 로그 디렉토리 생성
	log_dir = settings.paths.LOGS_DIRECTORY
	log_dir.mkdir(parents=True, exist_ok=True)

	# 3. 타임스탬프 기반 로그 파일명 생성
	timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
	log_filename = f"{timestamp}.log"
	log_filepath = log_dir / log_filename

	# 4. 로깅 기본 설정
	log_format = '%(asctime)s - %(levelname)s - [%(filename_context)s] - [%(name)s:%(lineno)d] - %(message)s'
	logging.basicConfig(
		level=log_level,  # 동적으로 설정된 로그 레벨 사용
		format=log_format,
		handlers=[
			logging.FileHandler(log_filepath, mode='w', encoding='utf-8'),  # 타임스탬프 파일에 저장
			logging.StreamHandler()
		],
		force=True
	)

	# 5. 모든 핸들러에 ContextFilter 적용
	context_filter = ContextFilter()
	for handler in logging.getLogger().handlers:
		handler.addFilter(context_filter)

	logging.getLogger("httpx").setLevel(logging.WARNING)
	logging.getLogger("google_genai").setLevel(logging.WARNING)

	initial_logger = logging.getLogger(__name__)
	initial_logger.info("========================================")
	initial_logger.info("Logging system initialized.")
	initial_logger.info("========================================")


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
	logger = logging.getLogger(__name__)

	for module_info in pkgutil.walk_packages(package_path, f"{package_name}."):
		try:
			module = importlib.import_module(module_info.name)
			for name, obj in inspect.getmembers(module, inspect.isclass):
				if issubclass(obj, base_class) and obj is not base_class:
					key_name = getattr(obj, 'GENERATOR_TYPE', None) or name.replace(suffix, "").lower()
					module_map[key_name] = obj
					logger.info(f"Discovered {base_class.__name__}: '{key_name}' -> {name}")
		except Exception as e:
			logger.error(f"Failed to import or inspect module {module_info.name}: {e}")

	if not module_map:
		logger.critical(f"No modules found for {base_class.__name__} in '{package_name}'.")
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
	parser.add_argument(
		'--log-level',
		type=str,
		default=settings.logging.DEFAULT_LEVEL,
		choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
		help='Set the logging level for the application.'
	)
	return parser


async def main() -> None:
	"""
	메인 실행 함수. 의존성을 생성 및 주입하고, 전체 파이프라인을 실행한다.
	"""
	# 인자 파싱을 로깅 설정보다 먼저 수행해야 함
	# 임시로 기본 파서만 만들어 log-level 인자만 먼저 파싱
	temp_parser = argparse.ArgumentParser(add_help=False)
	temp_parser.add_argument('--log-level', type=str, default=settings.logging.DEFAULT_LEVEL)
	temp_args, _ = temp_parser.parse_known_args()

	setup_logging(level=temp_args.log_level)
	logger = logging.getLogger(__name__)

	try:
		# --- 1. 동적 탐색 ---
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
			logger.info("Self-correction mode ENABLED by command-line argument.")

		logger.info(f"Script execution started. Generation type: '{args.type}', LLM Handler: '{args.llm}'")

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

		logger.info("All tasks completed successfully. Shutting down.")

	except (ImportError, ValueError, FileNotFoundError) as e:
		logger.critical(f"Initialization failed: {e}", exc_info=True)
	except Exception as e:
		logger.critical(f"An unexpected critical error occurred: {e}", exc_info=True)


if __name__ == "__main__":
	asyncio.run(main())
