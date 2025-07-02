# core/client.py

import logging
import google.genai as genai
from typing import Optional
from config.settings import settings

_client: Optional[genai.client.Client] = None

def get_gemini_client() -> genai.client.Client:
    """
    Google Gemini API 클라이언트 인스턴스를 반환한다.
    Singleton 패턴을 적용하여, 애플리케이션 실행 동안 단일 인스턴스만 사용하도록 보장한다.
    """
    global _client
    if _client is None:
        logging.info("Initializing Google Gemini API client...")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logging.info("Google Gemini API client initialized successfully.")
    return _client
