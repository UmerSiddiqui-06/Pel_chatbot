import { PelMark } from "../branding/PelMark";

export function TypingIndicator() {
  return (
    <div className="flex justify-start gap-2.5">
      <PelMark size={26} className="mt-0.5 shrink-0" />
      <div
        style={{ clipPath: "polygon(14px 0, 100% 0, 100% 100%, 0 100%, 0 14px)" }}
        className="flex items-center gap-1.5 bg-white dark:bg-ink-800 ring-1 ring-ink-100 dark:ring-ink-700 px-4 py-3"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-pel-400 animate-bounce [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 rounded-full bg-pel-400 animate-bounce [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 rounded-full bg-pel-400 animate-bounce" />
      </div>
    </div>
  );
}
