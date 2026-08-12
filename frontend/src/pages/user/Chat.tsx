import { useEffect, useRef } from "react";
import { Bot, AlertTriangle } from "lucide-react";
import { useChat } from "../../hooks/useChat";
import { ConversationSidebar } from "../../components/chat/ConversationSidebar";
import { ChatMessageBubble } from "../../components/chat/ChatMessageBubble";
import { TypingIndicator } from "../../components/chat/TypingIndicator";
import { MessageComposer } from "../../components/chat/MessageComposer";

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

      <div className="flex-1 flex flex-col bg-slate-50 min-w-0">
        {activeConversation ? (
          <>
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
              {activeConversation.messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center">
                  <div className="h-11 w-11 rounded-xl bg-pel-600 flex items-center justify-center mb-3">
                    <Bot className="h-6 w-6 text-white" />
                  </div>
                  <p className="text-slate-700 font-medium">How can I help you today?</p>
                  <p className="text-sm text-slate-400 mt-1">Ask about policies, manuals, warranty, or product info.</p>
                </div>
              ) : (
                activeConversation.messages.map((m) => (
                  <ChatMessageBubble key={m.id} message={m} onFeedback={sendFeedback} />
                ))
              )}
              {sending && <TypingIndicator />}
            </div>

            {error && (
              <div className="mx-6 mb-2 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700 ring-1 ring-red-200">
                <AlertTriangle className="h-3.5 w-3.5" /> {error}
              </div>
            )}

            <MessageComposer onSend={sendMessage} disabled={sending} />
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
            <Bot className="h-8 w-8 text-slate-300 mb-3" />
            <p className="text-sm font-medium text-slate-700">No conversations yet.</p>
            <p className="text-xs text-slate-500 mt-1 max-w-xs">
              Start a new conversation to ask the PEL AI Knowledge Agent a question.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
