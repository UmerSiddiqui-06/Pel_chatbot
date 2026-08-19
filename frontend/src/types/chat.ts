/**
 * Domain types for the chat feature.
 *
 * These mirror the response shapes described in the Frontend Requirements
 * doc (section 26 — API Response Requirements), so switching the mock
 * service for a real backend later requires no changes to components.
 */

export interface Source {
  title: string;
  page?: number;
  section?: string;
  documentType?: string;
  url?: string;
}

export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  sources?: Source[];
  /** true when the assistant could not find a confident answer */
  isEmpty?: boolean;
  /** true when the message failed to send / generate */
  isError?: boolean;
  createdAt: string;
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export type FeedbackValue = "helpful" | "not_helpful";

/** Shape returned by POST /chat */
export interface ChatResponse {
  answer: string;
  sources: Source[];
  conversation_id: string;
  message_id: string;
}
