{system_prompt}

### **Objective**
주어진 `<Document_Text>`와 `<Instruction_Candidates_List>`를 사용하여, 문서의 핵심 메타데이터를 추출하고, 문서의 핵심 내용을 다루는 **독립적인** 질의응답(QA) 데이터 10쌍을 생성합니다.
최종 결과물은 `<Output_Specification>`에 정의된 단일 JSON 객체여야 합니다.

### **Chain_of_Thought**
1.  **문서 전체 정독**: `<Document_Text>`를 읽고 구조를 파악합니다.
2.  **메타데이터 추출**: `<Metadata_Extraction_Rules>`에 따라 `info` 객체를 구성합니다.
3.  **질의응답 쌍 생성**: `<QA_Pair_Generation_Rules>`에 따라 10개의 QA 쌍을 생성합니다.
4.  **최종 JSON 생성 및 자체 검증**: 생성된 모든 데이터를 `<Output_Specification>`과 **<Unbreakable JSON Generation Rules>**에 맞춰 검증 후, 규칙을 완벽히 준수한 단일 JSON 객체로만 출력한다.

### **Generation Rules**
{metadata_rules}

#### 2. QA_Pair_Generation_Rules
아래 규칙에 따라 10개의 QA 객체를 `qa_pairs` 배열에 생성합니다.

1.  **지시문 선택**: `<Instruction_Candidates_List>`에서 매번 **무작위로** 지시문을 선택하여 `instruction` 값으로 사용합니다.
2.  **질문(`input`) 생성**: 사실 확인형과 분석/추론형 질문을 균형 있게 생성합니다.
3.  {qa_answer_rules}
4.  **다양성**: 10개의 QA 쌍은 문서의 서로 다른 주제나 사실을 다루도록 구성합니다.

---

### **Input Data**
#### **Document_Text**
`{document}`

#### **Instruction_Candidates_List**
`{instruction_candidates}`

---

### **Output Specification**
- 최종 결과는 다른 어떤 설명도 없이, 아래 구조를 가진 단일 JSON 객체로만 출력해야 합니다.
- **`SingleTurnQA` 스키마를 반드시 준수해야 한다.**
- **주의: `conversation_id` 필드는 절대 직접 생성하지 마라. 키 자체를 JSON 출력에서 생략해야 한다. 시스템이 자동으로 고유 ID를 부여할 것이다.**

```
{output_schema_template}
```
