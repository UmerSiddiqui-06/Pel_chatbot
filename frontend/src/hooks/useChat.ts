import { useCallback, useEffect, useState } from "react";
import { chatService } from "../api/chatService";
import type { Conversation, FeedbackValue } from "../types/chat";

export function useChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeConversation = conversations.find((c) => c.id === activeId) ?? null;

  // Initial load
  useEffect(() => {
    let cancelled = false;
    setLoadingList(true);
    chatService
      .listConversations()
      .then((data) => {
        if (cancelled) return;
        setConversations(data);
        if (data.length > 0) setActiveId(data[0].id);
      })
      .catch(() => {
        if (!cancelled) setError("Unable to load conversations.");
      })
      .finally(() => {
        if (!cancelled) setLoadingList(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectConversation = useCallback((id: string) => setActiveId(id), []);

  const newConversation = useCallback(async () => {
    const convo = await chatService.createConversation();
    setConversations((prev) => [convo, ...prev]);
    setActiveId(convo.id);
  }, []);

  const deleteConversation = useCallback(
    async (id: string) => {
      await chatService.deleteConversation(id);
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        if (activeId === id) setActiveId(next[0]?.id ?? null);
        return next;
      });
    },
    [activeId]
  );

  const sendMessage = useCallback(
    async (text: string) => {
      if (!activeConversation || !text.trim()) return;
      const convoId = activeConversation.id;
      setError(null);

      // Optimistically show the user's message immediately.
      const optimisticMsg = {
        id: `pending_${Date.now()}`,
        role: "user" as const,
        text,
        createdAt: new Date().toISOString(),
      };
      setConversations((prev) =>
        prev.map((c) => (c.id === convoId ? { ...c, messages: [...c.messages, optimisticMsg] } : c))
      );

      setSending(true);
      try {
        const res = await chatService.sendMessage(convoId, text);
        setConversations((prev) =>
          prev.map((c) =>
            c.id === convoId
              ? {
                  ...c,
                  title: c.messages.length <= 1 ? text.slice(0, 32) : c.title,
                  messages: [
                    ...c.messages,
                    {
                      id: res.message_id,          // was: `m_${Date.now()}`
                      role: "assistant" as const,
                      text: res.answer,
                      sources: res.sources,
                      isEmpty: res.sources.length === 0,
                      createdAt: new Date().toISOString(),
                    },
                  ],
                }
              : c
          )
        );
      } catch {
        setError("Unable to send your message. Please try again.");
        setConversations((prev) =>
          prev.map((c) =>
            c.id === convoId
              ? {
                  ...c,
                  messages: [
                    ...c.messages,
                    {
                      id: `err_${Date.now()}`,
                      role: "assistant" as const,
                      text: "Unable to send your message. Please try again.",
                      isError: true,
                      createdAt: new Date().toISOString(),
                    },
                  ],
                }
              : c
          )
        );
      } finally {
        setSending(false);
      }
    },
    [activeConversation]
  );

  const sendFeedback = useCallback(async (messageId: string, value: FeedbackValue) => {
    try {
      await chatService.sendFeedback(messageId, value);
    } catch {
      // Feedback failures shouldn't interrupt the chat experience.
    }
  }, []);

  return {
    conversations,
    activeConversation,
    loadingList,
    sending,
    error,
    selectConversation,
    newConversation,
    deleteConversation,
    sendMessage,
    sendFeedback,
  };
}
