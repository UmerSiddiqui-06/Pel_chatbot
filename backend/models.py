import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

def gen_uuid():
    return str(uuid.uuid4())


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    title = Column(String, nullable=False, default="New conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)   # "user" or "assistant"
    text = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)   # list of {title, page, section}
    is_empty = Column(String, nullable=True)   # "true" when no confident answer was found
    feedback = Column(String, nullable=True)   # "helpful" | "not_helpful" | null
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversation = relationship("Conversation", back_populates="messages")