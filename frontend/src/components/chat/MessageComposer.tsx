import { useState, type KeyboardEvent } from "react";
import { Send } from "lucide-react";

interface Props {
  onSend: (text: string) => void;
  disabled?: boolean;
}

export function MessageComposer({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");

  const submit = () => {
    if (!value.trim() || disabled) return;
    onSend(value.trim());
    setValue("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-ink-100 dark:border-ink-800 bg-white/80 dark:bg-ink-900/80 backdrop-blur-md p-4">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Ask a question..."
          className="flex-1 resize-none rounded-2xl border border-ink-200 dark:border-ink-700 bg-white dark:bg-ink-800 text-ink-800 dark:text-ink-100 placeholder:text-ink-400 dark:placeholder:text-ink-500 px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-pel-500 focus:border-pel-500 transition-shadow"
        />
        {/* Diamond at rest, squares up on hover/focus — the send action
            literally "resolves" the geometric mark into motion. */}
        <button
          type="button"
          onClick={submit}
          disabled={!value.trim() || disabled}
          aria-label="Send message"
          className="group h-10 w-10 shrink-0 flex items-center justify-center disabled:opacity-40 transition-transform"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-pel-500 to-pel-700 text-white shadow-sm shadow-pel-900/20 rotate-45 group-hover:rotate-0 group-focus-visible:rotate-0 transition-transform duration-300">
            <Send className="h-4 w-4 -rotate-45 group-hover:rotate-0 group-focus-visible:rotate-0 transition-transform duration-300" />
          </span>
        </button>
      </div>
      <p className="text-center text-xs text-ink-400 dark:text-ink-500 mt-2">
        Responses are generated from approved PEL sources. Verify important details.
      </p>
    </div>
  );
}
