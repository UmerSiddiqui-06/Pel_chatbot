import { useState } from "react";
import { Copy, ThumbsUp, ThumbsDown, Check } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage, FeedbackValue } from "../../types/chat";
import { SourceList } from "./SourceList";
import { PelMark } from "../branding/PelMark";

interface Props {
  message: ChatMessage;
  onFeedback: (messageId: string, value: FeedbackValue) => void;
}

// Sharp-cut top corner on the sender's side — the one geometric "tell" on
// each bubble, echoing the rotated-square mark without repeating it outright.
const userClip = { clipPath: "polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)" };
const assistantClip = { clipPath: "polygon(14px 0, 100% 0, 100% 100%, 0 100%, 0 14px)" };

export function ChatMessageBubble({ message, onFeedback }: Props) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackValue | null>(null);

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div
          style={userClip}
          className="max-w-lg rounded-2xl bg-gradient-to-br from-pel-500 to-pel-700 px-4 py-2.5 text-sm text-white whitespace-pre-wrap shadow-sm shadow-pel-900/20"
        >
          {message.text}
        </div>
      </div>
    );
  }

  const handleCopy = () => {
    navigator.clipboard?.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  const handleFeedback = (value: FeedbackValue) => {
    setFeedback(value);
    onFeedback(message.id, value);
  };

  const toneClasses = message.isError
    ? "bg-red-50 dark:bg-red-950/40 text-red-800 dark:text-red-200 ring-1 ring-red-200 dark:ring-red-900"
    : message.isEmpty
    ? "bg-amber-50 dark:bg-amber-950/30 text-amber-900 dark:text-amber-200 ring-1 ring-amber-200 dark:ring-amber-900"
    : "bg-white dark:bg-ink-800 text-ink-800 dark:text-ink-100 ring-1 ring-ink-100 dark:ring-ink-700";

  return (
    <div className="flex justify-start gap-2.5">
      <PelMark size={26} className="mt-0.5 shrink-0" />
      <div className="max-w-xl">
        <p className="text-xs font-medium text-ink-400 dark:text-ink-500 mb-1.5">PEL AI</p>

        <div style={assistantClip} className={`px-4 py-3 text-sm ${toneClasses}`}>
          <ReactMarkdown
            components={{
              h1: ({ children }) => <h1 className="text-base font-semibold mb-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-base font-semibold mt-3 mb-1.5">{children}</h2>,
              h3: ({ children }) => <h3 className="text-sm font-semibold mt-3 mb-1.5">{children}</h3>,
              p: ({ children }) => <p className="leading-6 mb-2 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="list-disc pl-5 space-y-1 mb-2 last:mb-0">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1 mb-2 last:mb-0">{children}</ol>,
              li: ({ children }) => <li className="pl-1">{children}</li>,
              strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
              hr: () => <div className="my-3 border-t border-ink-100 dark:border-ink-700" />,
            }}
          >
            {message.text}
          </ReactMarkdown>
          <SourceList sources={message.sources} />
        </div>

        {!message.isError && !message.isEmpty && (
          <div className="flex items-center gap-3 mt-1.5 ml-1">
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1 text-xs text-ink-400 dark:text-ink-500 hover:text-ink-600 dark:hover:text-ink-300"
            >
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy"}
            </button>
            <button
              type="button"
              onClick={() => handleFeedback("helpful")}
              className={`flex items-center gap-1 text-xs ${
                feedback === "helpful"
                  ? "text-emerald-600 dark:text-emerald-400"
                  : "text-ink-400 dark:text-ink-500 hover:text-ink-600 dark:hover:text-ink-300"
              }`}
            >
              <ThumbsUp className="h-3 w-3" /> Helpful
            </button>
            <button
              type="button"
              onClick={() => handleFeedback("not_helpful")}
              className={`flex items-center gap-1 text-xs ${
                feedback === "not_helpful"
                  ? "text-red-600 dark:text-red-400"
                  : "text-ink-400 dark:text-ink-500 hover:text-ink-600 dark:hover:text-ink-300"
              }`}
            >
              <ThumbsDown className="h-3 w-3" /> Not helpful
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
