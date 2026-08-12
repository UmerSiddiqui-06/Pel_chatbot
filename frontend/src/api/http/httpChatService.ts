import type { ChatResponse, Conversation, FeedbackValue } from "../../types/chat";

/**
 * Real backend implementation.
 *
 * Endpoints match section 25 ("API Integration Requirements") of the
 * Frontend Requirements doc. This file is intentionally NOT wired up
 * until VITE_API_BASE_URL is set — see api/chatService.ts.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      // TODO: attach auth token once auth screens are built, e.g.
      // Authorization: `Bearer ${getAccessToken()}`,
      ...options.headers,
    },
    credentials: "include",
  });

  if (!res.ok) {
    // Keep this generic for end users; log the real detail for admins/devs.
    // eslint-disable-next-line no-console
    console.error(`API error on ${path}:`, res.status, await res.text().catch(() => ""));
    throw new Error("Unable to reach PEL AI. Please try again.");
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const httpChatService = {
  listConversations: () => request<Conversation[]>("/conversations"),

  getConversation: (id: string) => request<Conversation>(`/conversations/${id}`),

  createConversation: () => request<Conversation>("/conversations", { method: "POST" }),

  renameConversation: (id: string, title: string) =>
    request<void>(`/conversations/${id}`, { method: "PATCH", body: JSON.stringify({ title }) }),

  deleteConversation: (id: string) => request<void>(`/conversations/${id}`, { method: "DELETE" }),

  sendMessage: (conversationId: string, text: string) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId, message: text }),
    }),

  sendFeedback: (messageId: string, value: FeedbackValue) =>
    request<void>(`/messages/${messageId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ value }),
    }),
};
