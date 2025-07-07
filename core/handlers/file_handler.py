# core/handlers/file_handler.py

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Union, Sequence

from schemas.datasets import ValidationSchema
from config.settings import settings

logger = logging.getLogger(__name__)

class FileHandler:
	"""
	파일 시스템과의 상호작용(읽기, 쓰기, 경로 관리)을 전담하는 클래스.
	SRP 원칙에 따라 파일 관련 모든 책임을 이 클래스로 위임.
	"""

	def __init__(self, data_directory: Path, output_base_directory: Path):
		"""
		FileHandler를 초기화한다.

		Args:
			data_directory: 원본 문서 파일(들)이 있는 디렉토리.
			output_base_directory: 모든 결과물이 저장될 최상위 디렉토리.
		"""
		self.data_directory = data_directory
		self.output_base_directory = output_base_directory
		self._setup_directories()

	def _setup_directories(self) -> None:
		"""출력 디렉터리가 존재하는지 확인하고, 없으면 생성한다."""
		try:
			self.output_base_directory.mkdir(parents=True, exist_ok=True)
			logger.info(f"Base output directory '{self.output_base_directory}' is ready.")
		except OSError as e:
			logger.critical(f"FATAL: Failed to create base output directory '{self.output_base_directory}'."
			                f" Check permissions. Error: {e}", exc_info=True)
			raise

	def get_output_path(self, generator_type: str, original_filename: str, is_broken: bool = False) -> Path:
		"""
		결과물을 저장할 최종 파일 경로를 생성한다.

		Args:
			generator_type: 현재 실행 중인 제너레이터의 타입 (e.g., 'singleturn').
			original_filename: 원본 파일의 이름.
			is_broken: JSON 파싱/검증에 최종 실패한 결과물인지 여부.

		Returns:
			결과물을 저장할 Path 객체.
		"""
		output_dir = self.output_base_directory / generator_type
		output_dir.mkdir(parents=True, exist_ok=True)

		stem = Path(original_filename).stem
		if is_broken:
			filename = settings.paths.BROKEN_FILENAME_TEMPLATE.format(stem=stem)
		else:
			filename = settings.paths.QA_FILENAME_TEMPLATE.format(stem=stem)

		path = output_dir / filename
		logger.debug(f"Generated output path: {path}")
		return output_dir / filename

	def find_files(self, allowed_extensions: Sequence[str] = ('.md',), num_files: Optional[int] = None) -> List[Path]:
		"""
		지정된 데이터 디렉토리에서 지정된 확장자를 가진 파일을 검색한다.

		Args:
			allowed_extensions: 검색할 파일 확장자 시퀀스.
			num_files: 처리할 최대 파일 수. None이면 모든 파일을 반환.

		Returns:
			검색된 파일 경로의 리스트.
		"""
		logger.info(f"Searching for files with extensions {allowed_extensions} in '{self.data_directory}'...")
		all_files = []
		for ext in allowed_extensions:
			all_files.extend(self.data_directory.rglob(f'*{ext}'))

		if not all_files:
			logger.warning("No files found to process.")
			return []

		# 정렬하여 일관된 순서 보장
		all_files.sort()

		files_to_process = all_files[:num_files] if num_files is not None else all_files
		logger.info(f"Found {len(files_to_process)} files to process out of {len(all_files)} total.")
		return files_to_process

	@staticmethod
	async def read_file_async(filepath: Path) -> str:
		"""비동기적으로 텍스트 파일을 읽어 내용을 반환한다."""
		logger.debug(f"Reading file: {filepath.name}")
		try:
			loop = asyncio.get_running_loop()
			return await loop.run_in_executor(None, lambda: filepath.read_text('utf-8'))
		except Exception as e:
			logger.error(f"Error reading file {filepath.name}: {e}", exc_info=True)
			raise

	@staticmethod
	async def write_file_async(output_path: Path, content: Union[ValidationSchema, str]) -> None:
		"""검증된 데이터 모델 또는 깨진 텍스트를 파일에 비동기적으로 쓴다."""
		logger.debug(f"Writing to file: {output_path.name}")
		try:
			if isinstance(content, ValidationSchema):
				data_to_write = content.model_dump_json(indent=2, by_alias=True)
				message = f"Successfully saved valid JSON to '{output_path}'"
			else:
				data_to_write = str(content)
				message = f"Saved broken/unrepaired text to '{output_path}'"

			loop = asyncio.get_running_loop()
			await loop.run_in_executor(None, output_path.write_text, data_to_write, 'utf-8')

			if isinstance(content, ValidationSchema):
				logger.info(message)
			else:
				logger.warning(message)

		except Exception as e:
			logger.error(f"Error writing to file {output_path}: {e}", exc_info=True)
			raise
