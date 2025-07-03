# qa_generator

---

## Features
* QA 데이터셋 생성:
  * `Single-Turn QA`
  * `Multi-Turn QA`
  * `Chain-of-Thought (CoT) QA`
* LLM 연동:
  * `Google Gemini API`
  * ...
* LLM 응답을 `Pydantic` 스키마 기반으로 검증하고, `JSON` 형식이 유효하지 않을 경우 자동으로 복구
* LLM 응답이 유효하지 않을 경우, LLM 스스로 오류를 수정하도록 재요청

---

## Prerequisites
- `Python` >= 3.13

---

## Installation
```bash
git clone http://app.xten.co.kr:15300/develop/qa_generator.git
cd qa-generator
```

- `uv` 기반
```bash
uv venv
uv sync
```

- `pip` 기반
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
프로젝트 루트에 `.env` 파일 생성 후, `Google Gemini API` 키 설정
```ini, TOML
# .env
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
```

---

## Usage
```bash
python main.py --type <generator_type> --llm <llm_handler> [--num-files <count>] [--self-correction]
```
* `<generator_type>`: 생성할 데이터셋의 종류
    * `singleturn` : Single-Turn Dataset
    * `multiturn` : Multi-Turn Dataset
    * `cot` : CoT(Chain of Thought) Dataset
* `<llm_handler>` : 사용할 LLM 모델(Handler)
  * `gemini` : Google Gemini
  * `WIP`
    * `gpt`
    * `claude`
    * `ollama` : Local LLM
* `--num-files <count>` `optional` : 처리할 최대 파일 수
* `--self-correction` : LLM 응답에 오류가 있을 경우 자가 수정 활성화

```bash
python main.py --type singleturn --llm gemini --num-files 10
python main.py --type cot --llm gemini --self-correction
```

---

## Input
원본 문서는 `data/input/` 디렉토리에 `*.md` 확장자로 저장해야 한다.

`WIP` : `json` 등 다른 텍스트 기반 문서도 읽어올 수 있는 기능 구현

---

## Output
생성된 QA 데이터셋은 `data/output/<generator_type>/` 디렉토리에 `JSON` 형식으로 저장된다.
* 정상적으로 생성된 파일: `{원본파일이름}_qa.json`
* 오류가 발생한 파일 (자가 수정 비활성화 또는 실패 시): `{원본파일이름}_qa_broken.txt`

---

## Prompt Management & Structure
`core/prompt_manager.py` 에서 모든 프롬프트 템플릿을 캐시하고 관리한다.

`prompts/` 디렉토리에 정의된 계층 구조를 따른다.

### Prompt Structure
모든 메인 프롬프트 (`prompts/<type>/prompt.md`)는 다음의 공통 및 특정 구성 요소를 조합하여 생성된다.

* **시스템 프롬프트** (`partials/_system_prompt.md`): LLM의 역할과 응답 규칙, JSON 생성 규칙 등 대화의 기본 컨텍스트와 제약 조건을 정의한다.
* **메타데이터 추출 규칙** (`partials/_metadata_rules.md`): 
* **QA 답변 규칙** (`partials/_qa_answer_rules.md`): 생성될 QA 답변의 정확성, 구조(결론 + 상세설명 + 근거 인용), 그리고 문서 근거 인용 방식을 정의한다.
* **데이터셋별 메인 프롬프트** (`prompts/<type>/prompt.md`): 각 데이터셋 유형(Single-Turn, CoT, Multi-Turn)에 특화된 생성 목표, Chain-of-Thought 과정, 그리고 세부 생성 규칙을 정의한다.
* **JSON 스키마** (`prompts/<type>/schema.json`): LLM이 생성해야 할 최종 JSON 출력의 구조와 필드별 데이터 타입을 명시한다. Pydantic 스키마와 완벽히 일치해야 한다.
* ~~**지시문 후보** (예: `singleturn/instructions.txt`): Single-Turn QA의 경우, LLM이 질문과 함께 사용할 다양한 지시문(Instruction) 후보 목록을 제공한다.~~

### 자가 수정 프롬프트 
`partials/_self_correction_prompt.md` :
LLM이 유효하지 않은 JSON을 생성했을 경우, LLM에게 원본 프롬프트와 잘못된 출력을 제시하며 정확한 JSON을 다시 생성하도록 유도한다.

## Extensibility
### Add New LLM Handler
`core/handlers/llm/` 디렉토리에 `BaseLLMHandler`를 상속받는 새 클래스를 생성한다.

`core/handlers/llm/openai_handler.py`

```python
# core/handlers/llm/openai_handler.py
from core.handlers.llm.base_handler import BaseLLMHandler
# 필요한 import 구문...

class OpenAIHandler(BaseLLMHandler):
    # YOUR_CODE_HERE: OpenAI API와 통신하는 비동기 로직 구현
    async def generate_async(self, prompt: str, filename: str) -> Optional[str]:
        pass # BaseLLMHandler의 추상 메서드 구현.
```
`main.py`가 자동으로 핸들러를 감지한다.

### Add New Dataset Generator Type
`core/generators/` 디렉토리에 `DatasetGenerator`를 상속받는 새 클래스를 생성한다.

`core/generators/summary_generator.py`

```python
# core/generators/summary_generator.py
from core.generators.dataset_generator import DatasetGenerator
# 필요한 import 구문...

class SummaryGenerator(DatasetGenerator):
    GENERATOR_TYPE = "summary" # 고유 타입 정의 (필수)

    # YOUR_CODE_HERE:
    # _get_prompt_path, _get_schema_template_name, _get_required_partials
    # 등을 오버라이드하여 새로운 데이터셋 타입에 맞는 프롬프트 및 스키마 경로 지정.
    # 필요하다면 _get_extra_template_args()를 오버라이드하여 추가 인자를 주입할 것.
```
새로운 생성 타입에 맞는 `prompt`와 `JSON` schema를 `prompts/<new_type>/` 디렉토리에 추가한다.
* `prompts/<new_type>/prompt.md`
* `prompts/<new_type>/schema.json`

`schemas/datasets.py` 에 해당 데이터셋 타입의 _Pydantic_ `ValidationSchema`를 정의한다.

`DatasetGenerator`는 `schemas.datasets` 모듈을 동적으로 탐색하여 `GENERATOR_TYPE`, `ValidationSchema`를 매핑한다.

```python
# schemas/datasets.py
# ... (기존 코드)
class SummaryQA(BaseQASet[SummaryItem]): # SummaryItem은 정의 필요
    pass
```
`main.py`가 자동으로 제너레이터를 감지한다.

## Project Structure
```
QA-Generator/
├── config/
│   ├── __init__.py
│   └── settings.py
├── core/
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── cot_generator.py
│   │   ├── dataset_generator.py
│   │   ├── multi_turn_generator.py
│   │   └── single_turn_generator.py
│   ├── handlers/
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base_handler.py
│   │   │   └── gemini_handler.py
│   │   ├── __init__.py
│   │   └── file_handler.py
│   ├── processors/
│   │   ├── __init__.py
│   │   └── response_processor.py
│   ├── __init__.py
│   └── prompt_manager.py
├── prompts/
│   ├── cot/
│   │   ├── prompt.md
│   │   └── schema.json
│   ├── multiturn/
│   │   ├── prompt.md
│   │   └── schema.json
│   ├── partials/
│   │   ├── _metadata_rules.md
│   │   ├── _qa_answer_rules.md
│   │   ├── _self_correction_prompt.md
│   │   └── _system_prompt.md
│   ├── singleturn/
│       ├── instructions.txt
│       ├── prompt.md
│       └── schema.json
├── schemas/
│   ├── __init__.py
│   └── datasets.py
├── README.md
├── main.py
├── pyproject.toml
├── requirements.txt
└── uv.lock

```
