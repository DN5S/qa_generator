# /main.py

import argparse
import asyncio
import importlib
import inspect
import logging
import pkgutil
from typing import Dict, Type

from config.settings import settings
from core.generators.base import DatasetGenerator
import core.generators

def setup_logging() -> None:
	"""
	애플리케이션의 로깅 시스템을 초기화한다.
	로그는 파일(processing.log)과 콘솔 스트림으로 동시에 출력된다.
	"""
	log_format = '%(asctime)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
	# root logger의 기존 핸들러를 모두 제거하여 중복 출력을 방지한다.
	for handler in logging.root.handlers[:]:
		logging.root.removeHandler(handler)

	logging.basicConfig(
		level=logging.INFO,
		format=log_format,
		handlers=[
			logging.FileHandler("processing.log", mode='w', encoding='utf-8'),
			logging.StreamHandler()
		]
	)
	logging.info("========================================")
	logging.info("Logging system initialized.")
	logging.info("========================================")

def setup_environment() -> None:
	"""
	애플리케이션 실행에 필요한 파일 시스템 환경을 준비한다.
	결과물(output)을 저장할 디렉터리가 존재하지 않으면 생성한다.
	"""
	logging.info("Preparing application environment...")
	try:
		logging.info("Environment setup is delegated to generators.")
	except OSError as e:
		logging.critical(f"FATAL: Failed to create output directories. Check permissions. Error: {e}",
						 exc_info=True)
		raise SystemExit(1)

def discover_generators() -> Dict[str, Type[DatasetGenerator]]:
	"""
	core.generators 패키지를 동적으로 탐색하여 사용 가능한 모든 제너레이터 클래스를 찾아 매핑한다.
	"""
	generator_map = {}
	package = core.generators

	for module_info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
		if module_info.name.endswith('.base'):
			continue

		# importlib.import_module을 사용하여 모듈을 명시적으로 임포트한다.
		module = importlib.import_module(module_info.name)
		for name, obj in inspect.getmembers(module, inspect.isclass):
			if issubclass(obj, DatasetGenerator) and obj is not DatasetGenerator:
				key = name.replace("Generator", "").lower()
				generator_map[key] = obj
				logging.info(f"Discovered generator: '{key}' -> {name}")

	if not generator_map:
		raise ImportError("No generator classes found in 'core/generators' package.")
	return generator_map

def setup_arg_parser(choices: list) -> argparse.ArgumentParser:
	"""
	스크립트 실행을 위한 명령행 인터페이스(CLI) 인자를 설정하고 반환한다.
	"""
	parser = argparse.ArgumentParser(
		description="A robust tool for generating AI-based QA datasets from Markdown documents."
	)
	parser.add_argument(
		"--type",
		type=str,
		choices=choices,
		required=True,
		help="Type of dataset to generate. Discovered: %(choices)s"
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
	메인 실행 함수.
	모든 컴포넌트를 조립하고 데이터 생성 파이프라인을 실행한다.
	"""
	setup_logging()

	try:
		generator_map = discover_generators()
		parser = setup_arg_parser(list(generator_map.keys()))
		args = parser.parse_args()

		if args.self_correction:
			settings.ENABLE_SELF_CORRECTION = True

		logging.info(f"Script execution started. Generation type: '{args.type}'")
		logging.info(f"Self-Correction Mode: {'ENABLED' if settings.ENABLE_SELF_CORRECTION else 'DISABLED'}")

		generator_class = generator_map[args.type]
		generator = generator_class(settings)
		await generator.run(num_files=args.num_files)

		logging.info("All tasks completed successfully.")

	except (ImportError, ValueError, FileNotFoundError) as e:
		logging.critical(f"Initialization failed: {e}", exc_info=True)
	except Exception as e:
		logging.critical(f"An unexpected critical error occurred: {e}", exc_info=True)


if __name__ == "__main__":
	asyncio.run(main())
