# /main.py

import asyncio
import logging
from datetime import datetime
from typing import Type, TypeAlias, Optional
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, TaskID, TimeElapsedColumn, BarColumn, TextColumn, TaskProgressColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich import print as rprint
import questionary

from config.settings import Settings
from config.logging_config import ContextFilter
from config.app_config import AppConfig
from core.generators.dataset_generator import DatasetGenerator
from core.handlers.file_handler import FileHandler
from core.handlers.llm.base_handler import BaseLLMHandler
from core.prompt_manager import PromptTemplateManager
from core.registry import registry

# --- Type Aliases ---
GeneratorClass: TypeAlias = Type[DatasetGenerator]
LLMHandlerClass: TypeAlias = Type[BaseLLMHandler]

# --- Typer 앱 인스턴스 생성 ---
app = typer.Typer(
	name="qa-generator",
	help="AI 기반 QA 데이터셋 생성을 위한 강력한 도구입니다.",
	add_completion=False,
	rich_markup_mode="rich"
)
console = Console()


def setup_logging(level: str, settings: Settings) -> None:
	"""
	애플리케이션의 로깅 시스템을 초기화한다.
	로그는 파일(processing.log)과 콘솔 스트림으로 동시에 출력된다.
	Args:
		level: 로그 레벨
		settings: 애플리케이션 설정 객체
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

	# 4. 로깅 기본 설정 (콘솔 출력 제거, 파일에만 기록)
	log_format = '%(asctime)s - %(levelname)s - [%(filename_context)s] - [%(name)s:%(lineno)d] - %(message)s'
	logging.basicConfig(
		level=log_level,  # 동적으로 설정된 로그 레벨 사용
		format=log_format,
		handlers=[
			logging.FileHandler(log_filepath, mode='w', encoding='utf-8'),  # 타임스탬프 파일에만 저장
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
	initial_logger.info("Logging system initialized.")


def get_available_choices() -> tuple[list[str], list[str]]:
	"""
	사용 가능한 제너레이터와 LLM 핸들러 목록을 반환한다.
	컴포넌트 등록 후에 호출되어야 한다.
	"""
	return list(registry.generators.keys()), list(registry.handlers.keys())

def discover_and_register_components() -> None:
	"""
	'core' 패키지를 탐색하여 모든 제너레이터와 핸들러를
	레지스트리에 자동으로 등록한다.
	"""
	registry.discover_components("core.generators")
	registry.discover_components("core.handlers.llm")

@app.command()
def generate(
		dataset_type: str = typer.Argument(
			...,
			help="Specify the type of dataset to generate."
		),
		llm: str = typer.Option(
			None,
			"--llm",
			help="Specify the LLM handler to use."
		),
		num_files: Optional[int] = typer.Option(
			None,
			"--num-files",
			help="Specify the maximum number of files to process. If not specified, all files will be processed."
		),
		self_correction: bool = typer.Option(
			False,
			"--self-correction",
			help="Enable self-correction mode. The LLM will attempt to fix its own JSON errors."
		),
		log_level: str = typer.Option(
			"INFO",
			"--log-level",
			help="Set the application's log level."
		),
		show_progress: bool = typer.Option(
			True,
			"--progress/--no-progress",
			help="Set whether to display the progress bar."
		)
) -> None:
	"""
	Generate AI-based QA datasets.

	A powerful tool for generating high-quality QA datasets from Markdown documents.
	"""
	asyncio.run(_generate_async(dataset_type, llm, num_files, self_correction, log_level, show_progress))


async def _generate_async(
		dataset_type: str,
		llm: Optional[str],
		num_files: Optional[int],
		self_correction: bool,
		log_level: str,
		show_progress: bool
) -> None:
	"""
	비동기 생성 함수. 의존성을 생성 및 주입하고, 전체 파이프라인을 실행한다.
	"""
	# --- 0. 설정 객체 생성 ---
	settings = Settings()
	setup_logging(level=log_level, settings=settings)
	logger = logging.getLogger(__name__)

	try:
		# --- 1. 컴포넌트 자동 등록 ---
		discover_and_register_components()

		# --- 2. 사용 가능한 선택지 확인 ---
		gen_choices, llm_choices = get_available_choices()

		# 데이터셋 타입 검증
		if dataset_type not in gen_choices:
			console.print(f"[red]Error:[/red] Unknown dataset type '{dataset_type}'")
			console.print(f"Available types: {', '.join(gen_choices)}")
			raise typer.Exit(1)

		# LLM 핸들러 설정 (기본값 또는 검증)
		if llm is None:
			llm = llm_choices[0] if llm_choices else None
			if llm is None:
				console.print("[red]Error:[/red] No available LLM handlers.")
				raise typer.Exit(1)
			console.print(f"Using default LLM handler: {llm}")
		elif llm not in llm_choices:
			console.print(f"[red]Error:[/red] Unknown LLM handler '{llm}'")
			console.print(f"Available handlers: {', '.join(llm_choices)}")
			raise typer.Exit(1)

		# --- 3. 의존성 컨테이너 생성 ---
		app_config = AppConfig(
			settings=settings,
			file_handler=FileHandler(
				data_directory=settings.paths.DATA_DIRECTORY,
				output_base_directory=settings.paths.OUTPUT_BASE_DIRECTORY,
				settings=settings
			),
			template_manager=PromptTemplateManager(settings.paths.PROMPTS_DIRECTORY)
		)

		if self_correction:
			app_config.settings.llm.ENABLE_SELF_CORRECTION = True
			logger.info("Self-correction mode ENABLED by command-line argument.")

		console.print(f"Starting dataset generation: [bold blue]{dataset_type}[/bold blue], LLM: [bold green]{llm}[/bold green]")

		# --- 4. 동적 의존성 선택 및 주입 ---
		llm_handler_class = registry.handlers[llm]
		generator_class = registry.generators[dataset_type]

		llm_handler: BaseLLMHandler = llm_handler_class(app_config.settings)
		generator = generator_class(
			config=app_config,
			llm_handler=llm_handler,
			generator_type=dataset_type
		)

		# --- 5. 파이프라인 실행 (프로그래스 바 포함) ---
		if show_progress:
			await _run_with_progress(generator, num_files)
		else:
			await generator.run(num_files=num_files)

		console.print("[bold green]All tasks completed successfully![/bold green]")

	except (ImportError, ValueError, FileNotFoundError) as e:
		logger.critical(f"Initialization failed: {e}", exc_info=True)
		console.print(f"[red]Initialization failed:[/red] {e}")
		raise typer.Exit(1)
	except Exception as e:
		logger.critical(f"An unexpected critical error occurred: {e}", exc_info=True)
		console.print(f"[red]Unexpected error occurred:[/red] {e}")
		raise typer.Exit(1)


async def _run_with_progress(generator: DatasetGenerator, num_files: Optional[int]) -> None:
	"""
	프로그래스 바와 함께 데이터셋 생성을 병렬로 실행한다.
	MAX_CONCURRENT_REQUESTS 설정에 따라 동시 요청 수를 제한한다.
	"""
	# 처리할 파일 목록 가져오기
	files_to_process = generator.file_handler.find_files(num_files=num_files)

	if not files_to_process:
		console.print("[yellow]No files to process.[/yellow]")
		return

	total_files = len(files_to_process)
	max_concurrent = generator.config.settings.llm.MAX_CONCURRENT_REQUESTS
	console.print(f"Processing {total_files} files with max {max_concurrent} concurrent requests.")

	# 동시성 제어를 위한 세마포어 생성
	semaphore = asyncio.Semaphore(max_concurrent)

	# 프로그래스 바 설정 (경과 시간 표시, 1초마다 갱신)
	with Progress(
		TextColumn("[progress.description]{task.description}"),
		BarColumn(),
		TaskProgressColumn(),
		TimeElapsedColumn(),
		console=console,
		refresh_per_second=1  # 1초마다 갱신
	) as progress:
		task = progress.add_task(
			"[cyan]Processing files...",
			total=total_files
		)

		# 동시성 제어를 위한 락과 카운터
		progress_lock = asyncio.Lock()
		completed_files = 0
		failed_files = 0

		async def process_file_with_progress(filepath, file_index):
			"""개별 파일 처리 및 프로그래스 바 업데이트 (세마포어로 동시성 제어)"""
			nonlocal completed_files, failed_files

			async with semaphore:  # 세마포어로 동시 요청 수 제한
				try:
					await generator.execute_pipeline_for_file(filepath, file_index)
					async with progress_lock:
						completed_files += 1
						progress.update(
							task,
							advance=1,
							description=f"[green]Completed: {completed_files}[/green] | [red]Failed: {failed_files}[/red] | Current: {filepath.name}"
						)
				except Exception as e:
					async with progress_lock:
						failed_files += 1
						progress.update(
							task,
							advance=1,
							description=f"[green]Completed: {completed_files}[/green] | [red]Failed: {failed_files}[/red] | [red]Error: {filepath.name}[/red]"
						)
					logging.getLogger(__name__).error(f"파일 처리 실패 {filepath}: {e}")

		# 모든 파일을 병렬로 처리 (세마포어로 동시성 제어)
		tasks = [
			process_file_with_progress(filepath, i + 1)
			for i, filepath in enumerate(files_to_process)
		]
		await asyncio.gather(*tasks)

	# 결과 요약 출력
	_print_summary(completed_files, failed_files, total_files)


def _print_summary(completed: int, failed: int, total: int) -> None:
	"""
	처리 결과 요약을 출력한다.
	"""
	table = Table(title="Processing Summary")
	table.add_column("Item", style="cyan", no_wrap=True)
	table.add_column("Count", style="magenta")
	table.add_column("Percentage", style="green")

	table.add_row("Total Files", str(total), "100%")
	table.add_row("Successful", str(completed), f"{completed/total*100:.1f}%")
	table.add_row("Failed", str(failed), f"{failed/total*100:.1f}%")

	console.print(table)


@app.command()
def list_components() -> None:
	"""
	List available dataset types and LLM handlers.
	"""
	try:
		discover_and_register_components()
		gen_choices, llm_choices = get_available_choices()

		console.print("[bold blue]Available Dataset Types:[/bold blue]")
		for gen_type in gen_choices:
			console.print(f"  • {gen_type}")

		console.print("\n[bold green]Available LLM Handlers:[/bold green]")
		for llm_handler in llm_choices:
			console.print(f"  • {llm_handler}")

	except Exception as e:
		console.print(f"[red]Failed to retrieve component list:[/red] {e}")
		raise typer.Exit(1)


@app.command()
def interactive() -> None:
	"""
	Generate QA datasets in interactive mode.

	Users can proceed with dataset generation by selecting options step by step.
	"""
	console.print("[bold blue]Interactive QA Dataset Generator[/bold blue]")
	console.print("Generate datasets by selecting options step by step.\n")

	try:
		# 컴포넌트 등록
		discover_and_register_components()
		gen_choices, llm_choices = get_available_choices()

		if not gen_choices:
			console.print("[red]No available dataset types.[/red]")
			raise typer.Exit(1)

		if not llm_choices:
			console.print("[red]No available LLM handlers.[/red]")
			raise typer.Exit(1)

		# 1. 데이터셋 타입 선택
		console.print("[cyan]1. Select dataset type:[/cyan]")
		dataset_type = questionary.select(
			"Choose a dataset type:",
			choices=gen_choices,
			default=gen_choices[0] if gen_choices else None
		).ask()

		if dataset_type is None:
			console.print("[yellow]Operation cancelled.[/yellow]")
			raise typer.Exit(0)

		console.print(f"Selected dataset type: [green]{dataset_type}[/green]\n")

		# 2. LLM 핸들러 선택
		console.print("[cyan]2. Select LLM handler:[/cyan]")
		llm = questionary.select(
			"Choose an LLM handler:",
			choices=llm_choices,
			default=llm_choices[0] if llm_choices else None
		).ask()

		if llm is None:
			console.print("[yellow]Operation cancelled.[/yellow]")
			raise typer.Exit(0)

		console.print(f"Selected LLM handler: [green]{llm}[/green]\n")

		# 3. 파일 수 제한 설정
		console.print("[cyan]3. Set file processing limit:[/cyan]")
		limit_files = questionary.confirm("Limiting the number of files?", default=False).ask()

		if limit_files is None:
			console.print("[yellow]Operation cancelled.[/yellow]")
			raise typer.Exit(0)

		num_files = None
		if limit_files:
			num_files = questionary.text(
				"Maximum number of files to process:",
				default="",
				validate=lambda text: text.isdigit() and int(text) > 0
			).ask()

			if num_files is None:
				console.print("[yellow]Operation cancelled.[/yellow]")
				raise typer.Exit(0)

			num_files = int(num_files)
			console.print(f"Maximum files: [green]{num_files}[/green]\n")
		else:
			console.print("All files will be processed.\n")

		# 4. 자체 수정 모드 설정
		console.print("[cyan]4. Configure self-correction mode:[/cyan]")
		self_correction = questionary.confirm("Enable self-correction mode?", default=False).ask()

		if self_correction is None:
			console.print("[yellow]Operation cancelled.[/yellow]")
			raise typer.Exit(0)

		console.print(f"Self-correction mode: [green]{'Enabled' if self_correction else 'Disabled'}[/green]\n")

		# 5. 로그 레벨 설정
		console.print("[cyan]5. Select log level:[/cyan]")
		log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
		log_level = questionary.select(
			"Choose a log level:",
			choices=log_levels,
			default="INFO"
		).ask()

		if log_level is None:
			console.print("[yellow]Operation cancelled.[/yellow]")
			raise typer.Exit(0)

		console.print(f"Selected log level: [green]{log_level}[/green]\n")

		# 6. 프로그래스 바 설정
		console.print("[cyan]6. Configure progress bar display:[/cyan]")
		show_progress = questionary.confirm("Do you want to display the progress bar?", default=True).ask()

		if show_progress is None:
			console.print("[yellow]Operation cancelled.[/yellow]")
			raise typer.Exit(0)

		console.print(f"Progress bar: [green]{'Show' if show_progress else 'Hide'}[/green]\n")

		# 7. 설정 확인 및 실행
		console.print("[yellow]Configuration Summary:[/yellow]")
		summary_table = Table(show_header=False)
		summary_table.add_column("Item", style="cyan")
		summary_table.add_column("Value", style="green")

		summary_table.add_row("Dataset Type", dataset_type)
		summary_table.add_row("LLM Handler", llm)
		summary_table.add_row("File Limit", str(num_files) if num_files else "No limit")
		summary_table.add_row("Self-correction Mode", "Enabled" if self_correction else "Disabled")
		summary_table.add_row("Log Level", log_level)
		summary_table.add_row("Progress Bar", "Show" if show_progress else "Hide")

		console.print(summary_table)
		console.print()

		start_generation = questionary.confirm("Do you want to start dataset generation with the above settings?", default=True).ask()

		if start_generation is None:
			console.print("[yellow]Operation cancelled.[/yellow]")
			raise typer.Exit(0)
		elif start_generation:
			console.print("[bold green]Starting dataset generation...[/bold green]\n")
			asyncio.run(_generate_async(dataset_type, llm, num_files, self_correction, log_level, show_progress))
		else:
			console.print("[yellow]Operation cancelled.[/yellow]")

	except Exception as e:
		console.print(f"[red]Error occurred: {e}[/red]")
		raise typer.Exit(1)


@app.command()
def info() -> None:
	"""
	Display application information.
	"""
	settings = Settings()

	table = Table(title="Application Information")
	table.add_column("Setting", style="cyan", no_wrap=True)
	table.add_column("Value", style="magenta")

	table.add_row("Data Directory", str(settings.paths.DATA_DIRECTORY))
	table.add_row("Output Directory", str(settings.paths.OUTPUT_BASE_DIRECTORY))
	table.add_row("Prompts Directory", str(settings.paths.PROMPTS_DIRECTORY))
	table.add_row("Logs Directory", str(settings.paths.LOGS_DIRECTORY))
	table.add_row("Self-correction Mode", "Enabled" if settings.llm.ENABLE_SELF_CORRECTION else "Disabled")

	console.print(table)


if __name__ == "__main__":
	app()
