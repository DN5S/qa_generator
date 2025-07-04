# core/prompt_manager.py

import logging
from pathlib import Path

class PromptTemplateManager:
    _templates: dict[str, str] = {}

    def __init__(self, template_directory: Path):
        """
        PromptTemplateManager를 초기화하고 모든 템플릿을 로드한다.
        인스턴스는 호출자에 의해 생성 및 관리된다.
        """
        if not self._templates:
            logging.info(f"Initializing PromptTemplateManager. Loading templates from '{template_directory}'...")
            self._templates = {}  # 인스턴스별 템플릿 딕셔너리 초기화
            self._load_all_templates(template_directory)
            logging.info(f"Loaded {len(self._templates)} templates into cache.")

    def _load_all_templates(self, base_path: Path):
        """지정된 디렉터리와 하위 디렉터리에서 모든 템플릿 파일을 로드한다."""
        template_files = [p for p in base_path.rglob('*') if p.is_file() and p.suffix in ['.md', '.txt', '.json']]
        for file_path in template_files:
            key = file_path.relative_to(base_path).as_posix()
            try:
                self._templates[key] = file_path.read_text(encoding='utf-8')
            except Exception as e:
                logging.error(f"Failed to load template: {file_path}. Error: {e}")

    def get_template(self, key: str) -> str:
        """캐시된 템플릿을 반환한다. 없으면 에러를 낸다."""
        template = self._templates.get(key)
        if template is None:
            logging.error(f"FATAL: Template '{key}' not found in cache.")
            raise KeyError(f"Template '{key}' not found.")
        return template
