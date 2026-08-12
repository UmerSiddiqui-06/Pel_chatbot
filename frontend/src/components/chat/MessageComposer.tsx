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
    <div className="border-t border-slate-200 bg-white p-4">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          placeholder="Ask a question..."
          className="flex-1 resize-none rounded-xl border border-slate-200 px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-pel-500 focus:border-pel-500"
        />
        <button
          type="button"
          onClick={submit}
          disabled={!value.trim() || disabled}
          className="h-10 w-10 shrink-0 rounded-xl bg-pel-600 text-white flex items-center justify-center hover:bg-pel-700 disabled:opacity-40 transition-colors"
          aria-label="Send message"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
      <p className="text-center text-xs text-slate-400 mt-2">
        Responses are generated from approved PEL sources. Verify important details.
      </p>
    </div>
  );
}
