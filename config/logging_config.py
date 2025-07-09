# config/logging_config.py

import logging
import re
from contextvars import ContextVar

# 컨텍스트 변수: 현재 처리 중인 파일명
# 이 변수는 비동기 작업 간에 안전하게 격리된다.
context_filename: ContextVar[str] = ContextVar("filename_context", default="N/A")

class ContextFilter(logging.Filter):
    """
    로그 레코드에 현재 파일명 컨텍스트를 주입하고,
    Typer 관련 로그를 필터링하며, 이모지 및 특수문자를 제거하는 필터.
    """

    # Typer 관련 모듈명 패턴
    TYPER_MODULES = {
        'typer', 'click', 'rich', 'shellingham'
    }

    # 이모지 및 특수문자 제거를 위한 정규식 패턴
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # 감정 표현 이모지
        "\U0001F300-\U0001F5FF"  # 기호 및 픽토그램
        "\U0001F680-\U0001F6FF"  # 교통 및 지도 기호
        "\U0001F1E0-\U0001F1FF"  # 국기 이모지
        "\U00002702-\U000027B0"  # 기타 기호 (한글과 겹치지 않는 범위)
        "\U0001F900-\U0001F9FF"  # 추가 이모지
        "\U0001FA70-\U0001FAFF"  # 최신 이모지
        "]+", 
        flags=re.UNICODE
    )

    def filter(self, record):
        """
        로그 레코드를 필터링하고 처리한다.
        1. Typer 관련 로그는 차단
        2. 파일명 컨텍스트 추가
        3. 이모지 및 특수문자 제거
        """
        # 1. Typer 관련 로그 필터링
        if any(module in record.name for module in self.TYPER_MODULES):
            return False

        # 2. 파일명 컨텍스트 추가
        record.filename_context = context_filename.get()

        # 3. 로그 메시지에서 이모지 및 특수문자 제거
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._remove_special_chars(record.msg)

        # 4. 포맷된 메시지에서도 이모지 제거 (필요시)
        if hasattr(record, 'message') and isinstance(record.message, str):
            record.message = self._remove_special_chars(record.message)

        return True

    def _remove_special_chars(self, text: str) -> str:
        """
        텍스트에서 이모지 및 특수문자를 제거한다.
        """
        # 이모지 제거
        text = self.EMOJI_PATTERN.sub('', text)

        # 기타 특수 문자 제거 (선택적)
        # 한글, 영문, 숫자, 기본 구두점만 유지
        text = re.sub(r'[^\w\s가-힣.,!?:;()\[\]{}"\'`-]', '', text, flags=re.UNICODE)

        # 연속된 공백을 하나로 정리
        text = re.sub(r'\s+', ' ', text).strip()

        return text
