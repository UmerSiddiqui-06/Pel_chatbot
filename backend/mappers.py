from schemas import ConversationSchema, ChatMessageSchema, SourceSchema


def message_to_schema(msg) -> ChatMessageSchema:
    return ChatMessageSchema(
        id=msg.id,
        role=msg.role,
        text=msg.text,
        sources=[SourceSchema(**s) for s in (msg.sources or [])],
        isEmpty=msg.is_empty,
        isError=False,
        createdAt=msg.created_at.isoformat(),
    )


def conversation_to_schema(convo) -> ConversationSchema:
    return ConversationSchema(
        id=convo.id,
        title=convo.title,
        updatedAt=convo.updated_at.isoformat(),
        messages=[message_to_schema(m) for m in convo.messages],
    )