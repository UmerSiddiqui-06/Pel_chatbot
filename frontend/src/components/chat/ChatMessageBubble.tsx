import { useState } from "react";
import { Bot, Copy, ThumbsUp, ThumbsDown, Check } from "lucide-react";
import type { ChatMessage, FeedbackValue } from "../../types/chat";
import { SourceList } from "./SourceList";

interface Props {
  message: ChatMessage;
  onFeedback: (messageId: string, value: FeedbackValue) => void;
}

export function ChatMessageBubble({ message, onFeedback }: Props) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackValue | null>(null);

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-lg rounded-2xl rounded-tr-sm bg-pel-600 px-4 py-2.5 text-sm text-white whitespace-pre-wrap">
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
    ? "bg-red-50 text-red-800 ring-1 ring-red-200"
    : message.isEmpty
    ? "bg-amber-50 text-amber-900 ring-1 ring-amber-200"
    : "bg-white text-slate-800 ring-1 ring-slate-200";

  return (
    <div className="flex justify-start">
      <div className="max-w-xl">
        <div className="flex items-center gap-2 mb-1.5">
          <div className="h-6 w-6 rounded-md bg-pel-600 flex items-center justify-center">
            <Bot className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-xs font-medium text-slate-500">PEL AI</span>
        </div>

        <div className={`rounded-2xl rounded-tl-sm px-4 py-3 text-sm whitespace-pre-wrap ${toneClasses}`}>
          {message.text}
          <SourceList sources={message.sources} />
        </div>

        {!message.isError && !message.isEmpty && (
          <div className="flex items-center gap-3 mt-1.5 ml-1">
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600"
            >
              {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy"}
            </button>
            <button
              type="button"
              onClick={() => handleFeedback("helpful")}
              className={`flex items-center gap-1 text-xs ${
                feedback === "helpful" ? "text-emerald-600" : "text-slate-400 hover:text-slate-600"
              }`}
            >
              <ThumbsUp className="h-3 w-3" /> Helpful
            </button>
            <button
              type="button"
              onClick={() => handleFeedback("not_helpful")}
              className={`flex items-center gap-1 text-xs ${
                feedback === "not_helpful" ? "text-red-600" : "text-slate-400 hover:text-slate-600"
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
