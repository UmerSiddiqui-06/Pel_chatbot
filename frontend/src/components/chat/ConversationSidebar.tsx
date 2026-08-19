import { MessageSquare, Plus, Trash2 } from "lucide-react";
import type { Conversation } from "../../types/chat";

interface Props {
  conversations: Conversation[];
  activeId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}

export function ConversationSidebar({ conversations, activeId, loading, onSelect, onNew, onDelete }: Props) {
  return (
    <div className="w-64 shrink-0 border-r border-ink-100 dark:border-ink-800 bg-white/60 dark:bg-ink-900/60 backdrop-blur-md flex flex-col">
      <div className="p-3">
        <button
          type="button"
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 rounded-lg bg-gradient-to-br from-pel-500 to-pel-700 text-white text-sm font-medium py-2.5 shadow-sm shadow-pel-900/20 hover:shadow-md hover:shadow-pel-900/30 hover:-translate-y-px transition-all"
        >
          <Plus className="h-4 w-4" /> New chat
        </button>
      </div>

      <p className="px-4 text-[11px] font-mono uppercase tracking-widest text-ink-400 dark:text-ink-500 mt-2 mb-1">
        Recent chats
      </p>

      <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
        {loading && (
          <p className="text-xs text-ink-400 dark:text-ink-500 px-2 py-4 text-center">Loading conversations...</p>
        )}

        {!loading && conversations.length === 0 && (
          <p className="text-xs text-ink-400 dark:text-ink-500 px-2 py-4 text-center">
            No conversations yet. Start a new one to ask the PEL AI Knowledge Agent a question.
          </p>
        )}

        {conversations.map((c) => (
          <button
            key={c.id}
            type="button"
            onClick={() => onSelect(c.id)}
            className={`w-full group flex items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors ${
              activeId === c.id
                ? "bg-pel-50 dark:bg-pel-900/40 text-pel-700 dark:text-pel-200"
                : "text-ink-600 dark:text-ink-300 hover:bg-ink-50 dark:hover:bg-ink-800/60"
            }`}
          >
            <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" />
            <span className="truncate flex-1">{c.title}</span>
            <Trash2
              onClick={(e) => {
                e.stopPropagation();
                onDelete(c.id);
              }}
              className="h-3.5 w-3.5 shrink-0 opacity-0 group-hover:opacity-60 hover:!opacity-100"
            />
          </button>
        ))}
      </div>
    </div>
  );
}
