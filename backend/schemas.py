from typing import List, Literal, Optional
from pydantic import BaseModel


class SourceSchema(BaseModel):
    title: str
    page: Optional[int] = None
    section: Optional[str] = None
    documentType: Optional[str] = None
    url: Optional[str] = None


MessageRole = Literal["user", "assistant"]
FeedbackValue = Literal["helpful", "not_helpful"]


class ChatMessageSchema(BaseModel):
    id: str
    role: MessageRole
    text: str
    sources: List[SourceSchema] = []
    isEmpty: bool = False
    isError: bool = False
    createdAt: str


class ConversationSchema(BaseModel):
    id: str
    title: str
    updatedAt: str
    messages: List[ChatMessageSchema] = []


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceSchema]
    conversation_id: str


class RenameRequest(BaseModel):
    title: str


class FeedbackRequest(BaseModel):
    value: FeedbackValue