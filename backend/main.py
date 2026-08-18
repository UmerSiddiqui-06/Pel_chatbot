from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from database import engine

from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="PEL AI Knowledge Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Source(BaseModel):
    title: str
    page: Optional[int] = None
    section: Optional[str] = None
    documentType: Optional[str] = None
    url: Optional[str] = None


MessageRole = Literal["user", "assistant"]
FeedbackValue = Literal["helpful", "not_helpful"]


class ChatMessage(BaseModel):
    id: str
    role: MessageRole
    text: str
    sources: List[Source] = []
    isEmpty: bool = False
    isError: bool = False
    createdAt: str


class Conversation(BaseModel):
    id: str
    title: str
    updatedAt: str
    messages: List[ChatMessage]


class ChatRequest(BaseModel):
    conversation_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    conversation_id: str


class RenameRequest(BaseModel):
    title: str


class FeedbackRequest(BaseModel):
    value: FeedbackValue


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid(prefix: str) -> str:
    return f"{prefix}_{datetime.now(timezone.utc).timestamp():.0f}_{datetime.now(timezone.utc).microsecond}"


def seed_time(minutes: int = 0, hours: int = 0, days: int = 0) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes, hours=hours, days=days)).isoformat()


def seed_conversations() -> List[Conversation]:
    return [
        Conversation(
            id="c1",
            title="Warranty Policy",
            updatedAt=seed_time(minutes=30),
            messages=[
                ChatMessage(
                    id="m1",
                    role="user",
                    text="What's the warranty period for the CoolPro AC?",
                    createdAt=seed_time(minutes=31),
                ),
                ChatMessage(
                    id="m2",
                    role="assistant",
                    text="The warranty period for the CoolPro AC is two years from the date of purchase, covering the compressor and major components, according to the available PEL documentation.",
                    sources=[Source(title="Warranty Policy", page=4)],
                    createdAt=seed_time(minutes=30),
                ),
            ],
        ),
        Conversation(
            id="c2",
            title="Leave Policy",
            updatedAt=seed_time(days=1),
            messages=[
                ChatMessage(
                    id="m3",
                    role="user",
                    text="How many annual leaves do confirmed employees get?",
                    createdAt=seed_time(days=1),
                ),
                ChatMessage(
                    id="m4",
                    role="assistant",
                    text="Confirmed employees are entitled to 18 annual leave days per calendar year, as outlined in the Employee Leave Policy.",
                    sources=[
                        Source(title="Employee Leave Policy", page=6),
                        Source(title="HR Procedures Manual", section="Annual Leave"),
                    ],
                    createdAt=seed_time(days=1),
                ),
            ],
        ),
        Conversation(
            id="c3",
            title="Product Info",
            updatedAt=seed_time(days=3),
            messages=[
                ChatMessage(
                    id="m5",
                    role="user",
                    text="What categories of products does PEL manufacture?",
                    createdAt=seed_time(days=3),
                ),
                ChatMessage(
                    id="m6",
                    role="assistant",
                    text="Based on the available PEL documentation, product records include categories such as air conditioners, refrigerators, and home appliances, each with model-level specification sheets.",
                    sources=[Source(title="Product Database", section="Category Index")],
                    createdAt=seed_time(days=3),
                ),
            ],
        ),
    ]


conversations: Dict[str, Conversation] = {conversation.id: conversation for conversation in seed_conversations()}
feedback_events: List[dict] = []


def sorted_conversations() -> List[Conversation]:
    return sorted(conversations.values(), key=lambda c: c.updatedAt, reverse=True)


def generate_answer(question: str) -> dict:
    lowered = question.lower()

    if "warrant" in lowered:
        return {
            "answer": "PEL air conditioners are covered by a two-year warranty on the compressor and major components, according to the available PEL documentation.",
            "sources": [Source(title="Warranty Policy", page=4)],
        }

    if "leave" in lowered:
        return {
            "answer": "Confirmed employees are entitled to 18 annual leave days per calendar year. Leave requests should be submitted at least three working days in advance.",
            "sources": [Source(title="Employee Leave Policy", page=6)],
        }

    if "order" in lowered or "status" in lowered:
        return {
            "answer": "I can look up order status once this is connected to PEL's order-management system. In production this would call the live order status tool.",
            "sources": [Source(title="Product Database", section="Orders")],
        }

    return {
        "answer": "I couldn't find a confident answer in PEL's indexed documentation for that. Try rephrasing your question, or check back once more documents have been indexed.",
        "sources": [],
    }

@app.get("/")
def read_root():
    return {"status": "PEL AI backend is running"}


@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}


@app.get("/conversations", response_model=List[Conversation])
def list_conversations():
    return sorted_conversations()


@app.get("/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: str):
    conversation = conversations.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/conversations", response_model=Conversation)
def create_conversation():
    conversation = Conversation(id=uid("c"), title="New conversation", updatedAt=now_iso(), messages=[])
    conversations[conversation.id] = conversation
    return conversation


@app.patch("/conversations/{conversation_id}")
def rename_conversation(conversation_id: str, payload: RenameRequest):
    conversation = conversations.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversations[conversation_id] = conversation.model_copy(update={"title": payload.title, "updatedAt": now_iso()})
    return {"status": "ok"}


@app.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str):
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")

    del conversations[conversation_id]
    return None


@app.post("/chat", response_model=ChatResponse)
def send_message(payload: ChatRequest):
    conversation = conversations.get(payload.conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    user_message = ChatMessage(id=uid("m"), role="user", text=payload.message, createdAt=now_iso())
    conversation.messages.append(user_message)
    if len(conversation.messages) == 1:
        conversation.title = payload.message[:32]
    conversation.updatedAt = now_iso()

    generated = generate_answer(payload.message)
    assistant_message = ChatMessage(
        id=uid("m"),
        role="assistant",
        text=generated["answer"],
        sources=generated["sources"],
        isEmpty=len(generated["sources"]) == 0,
        createdAt=now_iso(),
    )
    conversation.messages.append(assistant_message)
    conversation.updatedAt = now_iso()

    return ChatResponse(answer=generated["answer"], sources=generated["sources"], conversation_id=conversation.id)


@app.post("/messages/{message_id}/feedback", status_code=204)
def send_feedback(message_id: str, payload: FeedbackRequest):
    feedback_events.append({"message_id": message_id, "value": payload.value, "createdAt": now_iso()})
    return None