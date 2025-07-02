# schemas/datasets.py

from datetime import date
from pydantic import BaseModel, Field, conlist, ConfigDict
from typing import List, Optional, TypeVar, Generic
from uuid import UUID, uuid4

class ValidationSchema(BaseModel):
    """모든 데이터 검증 스키마의 기반이 되는 Pydantic BaseModel."""
    model_config = ConfigDict(populate_by_name=True)

class Info(BaseModel):
    """문서의 메타데이터 구조를 정의한다."""
    case_name: Optional[str] = Field(None, description="사건명")
    case_no: Optional[str] = Field(None, description="사건번호")
    resolution_no: Optional[str] = Field(None, description="의결번호")
    accused: Optional[str] = Field(None, description="피심인")
    resolution_date: Optional[date] = Field(None, description="의결일자 (YYYY-MM-DD)")

# ============================================
# --- 공통 QA 구조체 (Common QA Structures) ---
# ============================================

# TypeVar를 사용하여 제네릭 아이템 타입을 정의한다.
QAItem = TypeVar('QAItem', bound=BaseModel)

class BaseQASet(ValidationSchema, Generic[QAItem]):
    """
    모든 QA 세트의 공통 구조를 정의하는 제네릭 베이스 모델.
    info, topic, conversation_id 등 공통 필드를 포함한다.
    """
    conversation_id: UUID = Field(default_factory=uuid4, description="QA 세트를 식별하기 위한 고유 UUID")
    topic: str = Field(..., description="QA 세트의 전체 주제.")
    info: Info = Field(..., description="문서의 메타데이터 정보")
    qa_pairs: conlist(QAItem, min_length=1) = Field(
        ...,
        description="질문-답변 쌍의 리스트"
    )

# ===================
# --- Single-Turn ---
# ===================

class SingleTurnQAItem(BaseModel):
    """단일 질문-답변 한 쌍의 구조."""
    instruction: str = Field(..., description="모델에게 주어진 지시사항")
    question: str = Field(..., description="생성된 질문")
    answer: str = Field(..., description="생성된 답변")

class SingleTurnQA(BaseQASet[SingleTurnQAItem]):
    """Single-Turn QA 데이터셋의 전체 구조."""
    pass

# ========================
# --- Chain-of-Thought ---
# ========================

class CotQAItem(BaseModel):
    """Chain-of-Thought(CoT)의 단일 아이템 구조."""
    question: str = Field(..., description="생성된 질문")
    thought: List[str] = Field(..., description="단계별 사고 과정(The chain of thought)의 리스트")
    answer: str = Field(..., description="사고 과정에 기반한 최종 답변")

class CotQA(BaseQASet[CotQAItem]):
    """CoT QA 데이터셋의 전체 구조."""
    pass

# ==================
# --- Multi-Turn ---
# ==================

class ConversationTurn(BaseModel):
    """Multi-turn 대화의 개별 '턴'에 대한 구조."""
    turn: int = Field(..., gt=0, description="대화의 순서 (1 이상).")
    question: str = Field(..., description="사용자 역할의 발화 내용.")
    answer: str = Field(..., description="모델 역할의 발화 내용.")

class MultiTurnConversation(BaseModel):
    """하나의 완전한 Multi-turn 대화 세션의 데이터 구조."""
    info: Info = Field(..., description="대화의 기반이 된 문서의 메타데이터 정보.")
    conversation_id: UUID = Field(default_factory=uuid4, description="대화 세션을 식별하기 위한 고유 UUID.")
    topic: str = Field(..., description="대화의 전체 주제.")
    turns: conlist(ConversationTurn, min_length=1) = Field(..., description="대화 턴의 리스트.")

class MultiTurnQA(ValidationSchema):
    """
    Multi-Turn QA 데이터셋의 전체 구조.
    하나 이상의 대화 세션 리스트를 포함한다.
    """
    conversations: conlist(MultiTurnConversation, min_length=1) = Field(
        ...,
        description="여러 대화 세션의 리스트."
    )
