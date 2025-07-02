{system_prompt}

### **Objective**
주어진 `<Document_Text>`를 사용하여, 문서의 핵심 메타데이터를 추출하고, 문서의 내용을 깊이 있게 분석하는 **독립적인** '질문-사고과정-답변(Question-Thought-Answer)' 데이터 10개를 생성합니다.
최종 결과물은 `<Output_Specification>`에 정의된 단일 JSON 객체여야 합니다.

### **Chain_of_Thought**
1.  **문서 전체 정독**: `<Document_Text>`를 읽고 구조를 파악합니다.
2.  **메타데이터 추출**: `<Metadata_Extraction_Rules>`에 따라 `info` 객체를 구성합니다.
3.  **질문-사고-답변(QTA) 생성**: `<QTA_Generation_Rules>`에 따라 10개의 QTA 쌍을 생성합니다. 
4.  **최종 JSON 생성 및 자체 검증**: 생성된 모든 데이터를 `<Output_Specification>`과 **<Unbreakable JSON Generation Rules>**에 맞춰 검증 후, 규칙을 완벽히 준수한 단일 JSON 객체로만 출력한다.

### **Generation Rules**
{metadata_rules}

#### 2. QTA_Generation_Rules
아래 규칙에 따라 10개의 QTA 객체를 `qa_pairs` 배열에 생성합니다.
1.  **질문(`question`) 생성**: 사실 확인형과 분석/추론형 질문을 균형 있게 생성합니다. 질문은 문서의 핵심 내용을 파고들어야 한다.
2.  **사고 과정(`thought`) 생성**: **아래 4단계 사고 과정을 반드시 따라서 서술해야 한다.** 각 단계는 명확히 구분되어야 한다.
    * **1단계: 질문 분해 (Deconstruction)**
        -   질문의 핵심 키워드와 의도를 파악한다. "이 질문은 정확히 무엇을 묻고 있는가?"
    * **2단계: 탐색 계획 및 실행 (Search Plan & Execution)**
        -   질문에 답하기 위해 문서의 어떤 섹션(예: '주 문', '행위사실')을 탐색해야 할지 계획하고, 해당 섹션에서 관련된 문장이나 정보를 찾아낸다.
    * **3단계: 정보 연결 및 추론 (Connection & Inference)**
        -   찾아낸 여러 정보 조각들을 논리적으로 연결한다. "A라는 사실과 B라는 사실을 조합하면 C라는 결론에 도달할 수 있다." 이 단계가 추론의 핵심이다.
    * **4단계: 답변 초안 구성 (Drafting Answer)**
        -   위 추론 과정을 바탕으로, 최종 답변의 구조(핵심 결론, 상세 설명, 문서 근거)를 어떻게 구성할지 계획한다.
3.  **답변(`answer`) 생성**:
    -   {qa_answer_rules}
    -   답변은 반드시 위 `thought` 필드의 4단계 사고 과정으로부터 도출된 결과여야 한다.
4.  **다양성**: 10개의 QTA 쌍은 문서의 서로 다른 주제나 사실을 다루도록 구성합니다.
---

### **Input Data**
#### **Document_Text**
`{document}`
---

### **Output Specification**
- 최종 결과는 다른 어떤 설명도 없이, 아래 구조를 가진 단일 JSON 객체로만 출력해야 합니다.
- **`CotQA` 스키마를 반드시 준수해야 한다.** 
- **`thought` 필드는 반드시 문자열의 JSON 배열(an array of strings) 형식이어야 한다.** 각 문자열은 사고 과정의 한 단계를 의미한다.
- **주의: `conversation_id` 필드는 절대 직접 생성하지 마라. 키 자체를 JSON 출력에서 생략해야 한다. 시스템이 자동으로 고유 ID를 부여할 것이다.**

```
{output_schema_template}
```
