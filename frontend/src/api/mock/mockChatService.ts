import type { ChatMessage, ChatResponse, Conversation, FeedbackValue, Source } from "../../types/chat";
import { seedConversations } from "./mockData";

/**
 * In-memory mock of the chat backend.
 *
 * This exists ONLY so the frontend has something real to run against
 * before the backend is available. Every function here has a 1:1
 * counterpart in `api/http/httpChatService.ts` with the same signature —
 * see chatService.ts for how the swap happens.
 */

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Simple in-memory "database" for this browser session only.
let conversations: Conversation[] = JSON.parse(JSON.stringify(seedConversations));

function uid(prefix: string) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function generateAnswer(question: string): { answer: string; sources: Source[]; isEmpty?: boolean } {
  const q = question.toLowerCase();

  if (q.includes("warrant")) {
    return {
      answer:
        "PEL air conditioners are covered by a two-year warranty on the compressor and major components, according to the available PEL documentation.",
      sources: [{ title: "Warranty Policy", page: 4 }],
    };
  }
  if (q.includes("leave")) {
    return {
      answer:
        "Confirmed employees are entitled to 18 annual leave days per calendar year. Leave requests should be submitted at least three working days in advance.",
      sources: [{ title: "Employee Leave Policy", page: 6 }],
    };
  }
  if (q.includes("order") || q.includes("status")) {
    return {
      answer:
        "I can look up order status once this is connected to PEL's order-management system. In production this would call the get_order_status() tool against live data.",
      sources: [{ title: "Product Database", section: "Orders" }],
    };
  }
  return {
    answer:
      "I couldn't find a confident answer in PEL's indexed documentation for that. Try rephrasing your question, or check back once more documents have been indexed.",
    sources: [],
    isEmpty: true,
  };
}

export const mockChatService = {
  async listConversations(): Promise<Conversation[]> {
    await delay(400);
    return JSON.parse(JSON.stringify(conversations)).sort(
      (a: Conversation, b: Conversation) => +new Date(b.updatedAt) - +new Date(a.updatedAt)
    );
  },

  async getConversation(id: string): Promise<Conversation> {
    await delay(150);
    const conversation = conversations.find((c) => c.id === id);
    if (!conversation) {
      throw new Error("Conversation not found");
    }
    return JSON.parse(JSON.stringify(conversation));
  },

  async createConversation(): Promise<Conversation> {
    await delay(150);
    const convo: Conversation = {
      id: uid("c"),
      title: "New conversation",
      updatedAt: new Date().toISOString(),
      messages: [],
    };
    conversations = [convo, ...conversations];
    return convo;
  },

  async renameConversation(id: string, title: string): Promise<void> {
    await delay(150);
    conversations = conversations.map((c) => (c.id === id ? { ...c, title } : c));
  },

  async deleteConversation(id: string): Promise<void> {
    await delay(150);
    conversations = conversations.filter((c) => c.id !== id);
  },

  /**
   * Sends a message and returns the assistant's reply.
   * Mirrors POST /chat -> { answer, sources, conversation_id }
   */
  async sendMessage(conversationId: string, text: string): Promise<ChatResponse> {
    const userMsg: ChatMessage = { id: uid("m"), role: "user", text, createdAt: new Date().toISOString() };
    conversations = conversations.map((c) =>
      c.id === conversationId
        ? {
            ...c,
            title: c.messages.length === 0 ? text.slice(0, 32) : c.title,
            updatedAt: new Date().toISOString(),
            messages: [...c.messages, userMsg],
          }
        : c
    );

    await delay(900 + Math.random() * 600);

    const { answer, sources, isEmpty } = generateAnswer(text);
    const assistantMsg: ChatMessage = {
      id: uid("m"),
      role: "assistant",
      text: answer,
      sources,
      isEmpty,
      createdAt: new Date().toISOString(),
    };
    conversations = conversations.map((c) =>
      c.id === conversationId ? { ...c, updatedAt: new Date().toISOString(), messages: [...c.messages, assistantMsg] } : c
    );

    return { answer, sources, conversation_id: conversationId, message_id: assistantMsg.id };
  },

  async sendFeedback(messageId: string, value: FeedbackValue): Promise<void> {
    await delay(200);
    // eslint-disable-next-line no-console
    console.log("[mock] feedback recorded", { messageId, value });
  },
};
