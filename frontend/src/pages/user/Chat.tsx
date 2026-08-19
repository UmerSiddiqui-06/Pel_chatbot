import { useEffect, useRef } from "react";
import { AlertTriangle } from "lucide-react";
import { useChat } from "../../hooks/useChat";
import { ConversationSidebar } from "../../components/chat/ConversationSidebar";
import { ChatMessageBubble } from "../../components/chat/ChatMessageBubble";
import { TypingIndicator } from "../../components/chat/TypingIndicator";
import { MessageComposer } from "../../components/chat/MessageComposer";
import { PelMark } from "../../components/branding/PelMark";

export function ChatPage() {
  const {
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
  } = useChat();

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [activeConversation?.messages.length, sending]);

  return (
    <div className="flex h-full">
      <ConversationSidebar
        conversations={conversations}
        activeId={activeConversation?.id ?? null}
        loading={loadingList}
        onSelect={selectConversation}
        onNew={newConversation}
        onDelete={deleteConversation}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {activeConversation ? (
          <>
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
              {activeConversation.messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center">
                  <div className="relative mb-4">
                    <div className="absolute inset-0 rounded-full bg-pel-500/20 blur-2xl" />
                    <PelMark size={56} className="relative" />
                  </div>
                  <p className="font-display font-medium text-lg text-ink-800 dark:text-white">
                    How can I help you today?
                  </p>
                  <p className="text-sm text-ink-400 dark:text-ink-500 mt-1">
                    Ask about policies, manuals, warranty, or product info.
                  </p>
                </div>
              ) : (
                activeConversation.messages.map((m) => (
                  <ChatMessageBubble key={m.id} message={m} onFeedback={sendFeedback} />
                ))
              )}
              {sending && <TypingIndicator />}
            </div>

            {error && (
              <div className="mx-6 mb-2 flex items-center gap-2 rounded-lg bg-red-50 dark:bg-red-950/40 px-3 py-2 text-xs text-red-700 dark:text-red-300 ring-1 ring-red-200 dark:ring-red-900">
                <AlertTriangle className="h-3.5 w-3.5" /> {error}
              </div>
            )}

            <MessageComposer onSend={sendMessage} disabled={sending} />
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
            <PelMark size={44} className="mb-3 opacity-60" />
            <p className="text-sm font-medium text-ink-700 dark:text-ink-200">No conversations yet.</p>
            <p className="text-xs text-ink-400 dark:text-ink-500 mt-1 max-w-xs">
              Start a new conversation to ask the PEL AI Knowledge Agent a question.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
