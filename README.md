# QA Generator

AI 기반 QA 데이터셋 생성 도구

---

## Features

* **다양한 QA 데이터셋 생성**:
  * `Single-Turn QA` - 단일 질문-답변 쌍
  * `Multi-Turn QA` - 다중 턴 대화형 QA
  * `Chain-of-Thought (CoT) QA` - 사고 과정이 포함된 QA
* **LLM 연동**:
  * `Google Gemini API` (gemini-2.0-flash, gemini-1.5-pro)
  * 확장 가능한 핸들러 아키텍처로 추가 LLM 지원 예정
* **고급 기능**:
  * `Pydantic` 스키마 기반 응답 검증
  * JSON 형식 오류 시 자동 복구
  * LLM 자가 수정 기능
  * 비동기 병렬 처리로 성능 최적화
  * Rich 기반 프로그래스 바 및 사용자 인터페이스
  * 대화형 모드 지원

---

## Prerequisites

- **Python** >= 3.13
- **Google Gemini API Key**

---

## Installation

### 1. 프로젝트 클론
```bash
git clone https://github.com/DN5S/qa_generator.git
cd qa-generator
```

### 2. 의존성 설치

#### uv 사용 (권장)
```bash
uv venv
uv sync
```

#### pip 사용
```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate
# Windows
.\venv\Scripts\activate

pip install -e .
```

---

## Configuration

### 환경 변수 설정
프로젝트 루트에 `.env` 파일을 생성하고 다음 설정 추가:

```ini
# 필수 설정
GEMINI_API_KEY=your_gemini_api_key_here

# LLM 설정 (선택사항)
LLM_MODEL_NAME=gemini-2.0-flash  # 또는 gemini-1.5-pro
LLM_API_RETRY_COUNT=3
LLM_API_RETRY_DELAY=5
LLM_MAX_CONCURRENT_REQUESTS=5
LLM_MAX_RESPONSE_SIZE_MB=1
LLM_ENABLE_SELF_CORRECTION=false

# 메타데이터 설정 (선택사항)
METADATA_DATASET_VERSION=1.0
METADATA_CREATOR=㈜엑스텐정보

# 로깅 설정 (선택사항)
LOGGING_DEFAULT_LEVEL=INFO
```

---

## Usage

QA Generator 4가지 명령어:

### 1. 기본 생성 명령어
```bash
python main.py generate <dataset_type> --llm <llm_handler> [OPTIONS]
```

**매개변수:**
- `<dataset_type>`: 생성할 데이터셋 종류
  - `singleturn` - Single-Turn Dataset
  - `multiturn` - Multi-Turn Dataset  
  - `cot` - Chain-of-Thought Dataset
- `--llm <handler>`: 사용할 LLM 핸들러
  - `gemini` - Google Gemini

**옵션:**
- `--num-files <count>`: 처리할 최대 파일 수 (기본값: 모든 파일)
- `--self-correction`: LLM 자가 수정 모드 활성화
- `--log-level <level>`: 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--progress/--no-progress`: 프로그래스 바 표시 여부 (기본값: 표시)

**예시:**
```bash
# 기본 사용법
python main.py generate singleturn --llm gemini

# 파일 수 제한 및 자가 수정 활성화
python main.py generate cot --llm gemini --num-files 10 --self-correction

# 디버그 모드로 실행
python main.py generate multiturn --llm gemini --log-level DEBUG
```

### 2. 사용 가능한 컴포넌트 확인
```bash
python main.py list-components
```
등록된 데이터셋 타입과 LLM 핸들러 목록 표시

### 3. 대화형 모드
```bash
python main.py interactive
```
단계별 설정을 통한 대화형 인터페이스

### 4. 애플리케이션 정보 확인
```bash
python main.py info
```
현재 설정된 경로와 구성 정보 표시

---

## Progress Bar

Rich 기반 프로그래스 바로 진행 상황 시각화

### 기능
* **경과 시간 표시**: 프로그램 시작부터 현재까지 경과 시간 실시간 표시
* **실시간 업데이트**: 1초마다 진행 상황과 시간 정보 갱신
* **파일 처리 상태**: 완료/실패 파일 수, 현재 처리 중인 파일명 표시
* **진행률 표시**: 전체 작업 대비 현재 진행률 백분율과 진행 바 표시
* **처리 결과 요약**: 완료 후 성공/실패 통계 테이블 표시

### 표시 정보
```
Completed: 5 | Failed: 0 | Current: example.md ████████████████████ 100% 0:02:15
```

---

## Input

원본 문서는 `data/input/` 디렉토리에 `*.md` 확장자로 저장

> **참고**: 향후 JSON 등 다른 텍스트 기반 문서 형식도 지원 예정

---

## Output

생성된 QA 데이터셋은 `data/output/<dataset_type>/` 디렉토리에 저장:

* **정상 생성**: `{원본파일이름}_qa.json`
* **오류 발생**: `{원본파일이름}_qa_broken.txt` (자가 수정 비활성화 또는 실패 시)

---

## Architecture

### Component Registry System
QA Generator 동적 컴포넌트 등록 시스템:
- **자동 발견**: `core.generators`와 `core.handlers.llm` 패키지 자동 탐색
- **동적 등록**: 런타임에 사용 가능한 제너레이터와 핸들러 등록
- **확장성**: 새로운 컴포넌트 추가 시 자동 인식

### Prompt Management
`core/prompt_manager.py`에서 모든 프롬프트 템플릿 캐시 및 관리

#### Prompt Structure
메인 프롬프트 구성 요소:

* **시스템 프롬프트** (`partials/_system_prompt.md`): LLM의 역할과 응답 규칙 정의
* **메타데이터 추출 규칙** (`partials/_metadata_rules.md`): 문서 메타데이터 추출 방식
* **QA 답변 규칙** (`partials/_qa_answer_rules.md`): QA 답변의 구조와 품질 기준
* **데이터셋별 메인 프롬프트** (`prompts/<type>/prompt.md`): 각 데이터셋 유형별 특화 규칙
* **JSON 스키마** (`prompts/<type>/schema.json`): 출력 JSON 구조 정의
* **자가 수정 프롬프트** (`partials/_self_correction_prompt.md`): JSON 오류 시 수정 요청

---

## Extensibility

### 새로운 LLM 핸들러 추가

1. `core/handlers/llm/` 디렉토리에 새 핸들러 클래스 생성:

```python
# core/handlers/llm/openai_handler.py
from core.handlers.llm.base_handler import BaseLLMHandler
from typing import Optional

class OpenAIHandler(BaseLLMHandler):
    async def generate_async(self, prompt: str, filename: str) -> Optional[str]:
        # OpenAI API 연동 로직 구현
        pass
```

2. 애플리케이션이 자동으로 새 핸들러 감지 및 등록

### 새로운 데이터셋 제너레이터 추가

1. `core/generators/` 디렉토리에 새 제너레이터 클래스 생성:

```python
# core/generators/summary_generator.py
from core.generators.dataset_generator import DatasetGenerator

class SummaryGenerator(DatasetGenerator):
    GENERATOR_TYPE = "summary"  # 고유 타입 정의 (필수)

    # 필요한 메서드 오버라이드:
    # _get_prompt_path, _get_schema_template_name, _get_required_partials 등
```

2. 새로운 프롬프트와 스키마 파일 추가:
   - `prompts/summary/prompt.md`
   - `prompts/summary/schema.json`

3. `schemas/datasets.py`에 Pydantic 검증 스키마 정의:

```python
# schemas/datasets.py
class SummaryQA(BaseQASet[SummaryItem]):
    pass
```

4. 애플리케이션이 자동으로 새 제너레이터 감지 및 등록

---

## Logging

### 로그 레벨 정책
* **INFO**: 일반적인 실행 시 사용하는 기본 레벨. 핵심 이벤트만 기록하며 민감한 정보는 포함하지 않음
* **DEBUG**: 문제 해결 시에만 사용. 상세한 변수 값, 함수 흐름, 프롬프트 내용 등 민감한 정보 포함

### 로그 파일 관리
* 로그는 `logs/` 디렉토리에 타임스탬프 기반 파일명으로 저장
* DEBUG 레벨 로그는 분석 후 즉시 삭제하거나 안전한 장소에 보관
* 로그 파일은 로컬 시스템 외부로 전송 금지

### 사용 권장사항
```bash
# 평상시 실행
python main.py generate singleturn --llm gemini

# 문제 발생 시 디버깅
python main.py generate singleturn --llm gemini --log-level DEBUG
```

---

## Project Structure

```
qa_generator/
├── config/
│   ├── __init__.py
│   ├── app_config.py          # 애플리케이션 설정 컨테이너
│   ├── logging_config.py      # 로깅 설정
│   └── settings.py            # 환경 변수 및 설정 관리
├── core/
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── dataset_generator.py    # 기본 제너레이터 클래스
│   │   ├── cot_generator.py        # CoT 데이터셋 제너레이터
│   │   ├── multi_turn_generator.py # Multi-Turn 제너레이터
│   │   └── single_turn_generator.py # Single-Turn 제너레이터
│   ├── handlers/
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base_handler.py     # LLM 핸들러 기본 클래스
│   │   │   └── gemini_handler.py   # Gemini API 핸들러
│   │   ├── __init__.py
│   │   └── file_handler.py         # 파일 처리 핸들러
│   ├── processors/
│   │   ├── __init__.py
│   │   └── response_processor.py   # LLM 응답 처리
│   ├── __init__.py
│   ├── prompt_manager.py           # 프롬프트 템플릿 관리
│   └── registry.py                 # 컴포넌트 등록 시스템
├── data/
│   ├── input/                      # 입력 마크다운 파일
│   └── output/                     # 생성된 QA 데이터셋
│       ├── cot/
│       ├── multiturn/
│       └── singleturn/
├── logs/                           # 로그 파일
├── prompts/
│   ├── cot/
│   │   ├── prompt.md
│   │   └── schema.json
│   ├── multiturn/
│   │   ├── prompt.md
│   │   └── schema.json
│   ├── singleturn/
│   │   ├── prompt.md
│   │   └── schema.json
│   └── partials/
│       ├── _qa_answer_rules.md
│       ├── _self_correction_prompt.md
│       ├── _system_prompt.md
│       └── _metadata_rules.md
├── schemas/
│   ├── __init__.py
│   └── datasets.py                 # Pydantic 검증 스키마
├── tests/                          # 테스트 파일 (구현 예정)
├── .env                           # 환경 변수 (사용자 생성)
├── main.py                        # CLI 진입점
├── pyproject.toml                 # 프로젝트 메타데이터 및 의존성
├── README.md
└── uv.lock                        # 의존성 잠금 파일
```

---

## Dependencies

주요 의존성 패키지:

* **CLI & UI**: `typer`, `rich`, `questionary`
* **LLM Integration**: `google-genai`
* **Data Processing**: `pandas`, `pydantic-settings`
* **Utilities**: `python-dotenv`, `json-repair`
* **Development**: `pytest`, `pytest-asyncio`, `pip-audit`

전체 의존성 목록은 `pyproject.toml` 파일 참조

---

## Development

### 개발 환경 설정
```bash
# 개발 의존성 포함 설치
uv sync --dev

# 코드 품질 검사
pip-audit  # 보안 취약점 검사
```

### 테스트 실행
```bash
pytest  # 테스트 실행 (구현 예정)
```

---

## Contributing

1. 새로운 기능 개발 시 해당 컴포넌트의 기본 클래스를 상속받아 구현
2. 환경 변수는 `config/settings.py`에 적절한 설정 클래스에 추가
3. 로그 레벨 정책을 준수하여 로깅 구현
4. 새로운 의존성 추가 시 `pyproject.toml` 업데이트

---

## License



---

## Version

**Current Version**: 0.1.0

프로젝트 버전 정보는 `pyproject.toml` 파일에서 관리
