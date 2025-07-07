# config/logging_config.py

import logging
from contextvars import ContextVar
from typing import Final

# 컨텍스트 변수: 현재 처리 중인 파일명
# 이 변수는 비동기 작업 간에 안전하게 격리된다.
context_filename: ContextVar[str] = ContextVar("filename_context", default="N/A")

class ContextFilter(logging.Filter):
    """
    로그 레코드에 현재 파일명 컨텍스트를 주입하는 필터.
    contextvars를 사용하여 현재 작업의 파일명을 추적한다.
    """
    def filter(self, record):
        """
        로그 레코드에 'filename_context' 속성을 추가한다.
        포맷터에서 `%(filename_context)s` 형태로 사용할 수 있다.
        """
        record.filename_context = context_filename.get()
        return True
