{system_prompt}

### **Objective**
주어진 `<Document_Text>`를 사용하여, 사용자와 AI 간의 **자연스러운 다회차 대화(multi-turn conversation)** 시나리오 1개를 생성합니다. 이 대화는 **총 5턴(사용자 질문 5회, AI 답변 5회)**으로 이루어집니다.
최종 결과물은 `<Output_Specification>`에 정의된, `turns` 키 하나만을 가진 단일 JSON 객체여야 합니다.

### **Chain_of_Thought**
1.  **문서 정독**: `<Document_Text>`를 읽고 구조를 파악합니다.
2.  **대화 시나리오 생성**: `<Conversation_Generation_Rules>`에 따라 5턴의 대화를 생성합니다.
3.  **최종 JSON 검증**: 생성된 모든 데이터를 `<Output_Specification>`에 맞춰 검증 후 출력합니다.

### **Generation Rules**
#### Conversation_Generation_Rules
1.  **대화 시작**: 대화는 문서의 핵심 내용을 묻는 포괄적인 첫 질문으로 시작합니다.
2.  **대화 전개**: 두 번째 질문부터는 **바로 이전 AI의 답변 내용에 기반하여** 더 깊이 파고드는 심화 질문을 생성합니다.
3.  {qa_answer_rules}

---

### **Input Data**
#### **Document_Text**
`{document}`

---

### **Output Specification**
- 최종 결과는 다른 어떤 설명도 없이, 아래 구조를 가진 단일 JSON 객체로만 출력해야 합니다.
- **이제부터 당신의 유일한 임무는 `turns` 배열을 생성하는 것입니다.**
- 다른 모든 메타데이터는 시스템이 자동으로 처리할 것입니다.

```
{output_schema_template}
```
