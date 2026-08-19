from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import engine, SessionLocal
from models import Conversation as ConversationModel, Message as MessageModel
from schemas import (
    ConversationSchema,
    ChatRequest,
    ChatResponse,
    RenameRequest,
    FeedbackRequest,
    SourceSchema,
)
from mappers import conversation_to_schema
import agent

import uuid

def parse_uuid_or_404(id_str: str) -> str:
    try:
        return str(uuid.UUID(id_str))
    except ValueError:
        raise HTTPException(status_code=404, detail="Conversation not found")

app = FastAPI(title="PEL AI Knowledge Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"status": "PEL AI backend is running"}


@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}


@app.get("/conversations", response_model=List[ConversationSchema])
def list_conversations(db: Session = Depends(get_db)):
    convos = db.query(ConversationModel).order_by(ConversationModel.updated_at.desc()).all()
    return [conversation_to_schema(c) for c in convos]


@app.get("/conversations/{conversation_id}", response_model=ConversationSchema)
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation_id = parse_uuid_or_404(conversation_id)
    convo = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation_to_schema(convo)


@app.post("/conversations", response_model=ConversationSchema)
def create_conversation(db: Session = Depends(get_db)):
    convo = ConversationModel(title="New conversation")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return conversation_to_schema(convo)


@app.patch("/conversations/{conversation_id}")
def rename_conversation(conversation_id: str, payload: RenameRequest, db: Session = Depends(get_db)):
    conversation_id = parse_uuid_or_404(conversation_id)
    convo = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    convo.title = payload.title
    db.commit()
    return {"status": "ok"}


@app.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation_id = parse_uuid_or_404(conversation_id)
    convo = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(convo)
    db.commit()
    return None


@app.post("/chat", response_model=ChatResponse)
def send_message(payload: ChatRequest, db: Session = Depends(get_db)):
    convo = db.query(ConversationModel).filter(ConversationModel.id == payload.conversation_id).first()
    if convo is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(convo.messages) == 0

    user_msg = MessageModel(conversation_id=convo.id, role="user", text=payload.message)
    db.add(user_msg)

    if is_first_message:
        convo.title = payload.message[:32]

    # This is the line your friend's RAG model plugs into later.
    result = agent.generate_answer(payload.message)

    assistant_msg = MessageModel(
        conversation_id=convo.id,
        role="assistant",
        text=result["answer"],
        sources=result["sources"],
        is_empty=len(result["sources"]) == 0,
    )

    db.add(assistant_msg)
    convo.updated_at = datetime.now(timezone.utc)
    db.commit()

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceSchema(**s) for s in result["sources"]],
        conversation_id=convo.id,
        message_id=assistant_msg.id,
    )


@app.post("/messages/{message_id}/feedback", status_code=204)
def send_feedback(message_id: str, payload: FeedbackRequest, db: Session = Depends(get_db)):
    message_id = parse_uuid_or_404(message_id)
    msg = db.query(MessageModel).filter(MessageModel.id == message_id).first()
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.feedback = payload.value
    db.commit()
    return None