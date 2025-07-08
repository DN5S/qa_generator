{system_prompt}

### **Objective**
주어진 `<Document_Text>`와 `<Instruction_Candidates_List>`를 사용하여, 문서의 핵심 내용을 다루는 **독립적인** 질의응답(QA) 데이터 10쌍을 생성합니다.
최종 결과물은 `<Output_Specification>`에 정의된, `qa_pairs` 키 하나만을 가진 단일 JSON 객체여야 합니다.

### **Chain_of_Thought**
1.  **문서 전체 정독**: `<Document_Text>`를 읽고 구조를 파악합니다.
2.  **질의응답 쌍 생성**: `<QA_Pair_Generation_Rules>`에 따라 10개의 QA 쌍을 생성합니다.
3.  **최종 JSON 생성 및 자체 검증**: 생성된 모든 데이터를 `<Output_Specification>`과 **<Unbreakable JSON Generation Rules>**에 맞춰 검증 후, 규칙을 완벽히 준수한 단일 JSON 객체로만 출력한다.

### **Generation Rules**
#### **QA_Generation_Rules**
10개의 `qa_pairs` 배열을 생성할 때, 아래 두 가지 유형을 **약 8:2 비율**로 구성해야 합니다.

**유형 1: 사실 기반 질문 (8개)**
- 문서에 명시적으로 언급된 사실, 수치, 정의, 절차 등을 묻는 질문을 생성합니다.
- 답변은 '결론 + 상세설명 + 근거 인용' 구조를 따릅니다.

**유형 2: 정보 없음 질문 (2개)**
- 문서에 언급된 특정 대상(인물, 기관 등)에 대해, **문서 내에서는 찾아볼 수 없는 정보**를 의도적으로 질문합니다.
- 답변(`answer`)은 추측하는 대신, "주어진 정보만으로는 알 수 없다" 또는 "문서에 언급되지 않았다"고 명확히 밝혀야 합니다.
---

### **Input Data**
#### **Document_Text**
`{document}`

#### **Instruction_Candidates_List**
`{instruction_candidates}`

---

### **Output Specification**
- 최종 결과는 다른 어떤 설명도 없이, 아래 구조를 가진 단일 JSON 객체로만 출력해야 합니다.
- **이제부터 당신의 유일한 임무는 `qa_pairs` 배열을 생성하는 것입니다.**
- 다른 모든 메타데이터는 시스템이 자동으로 처리할 것입니다.

```
{output_schema_template}
```
