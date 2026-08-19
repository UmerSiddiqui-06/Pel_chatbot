import { useState } from "react";
import { FileText } from "lucide-react";
import type { Source } from "../../types/chat";

export function SourceList({ sources }: { sources?: Source[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3">
      <p className="text-[11px] font-mono uppercase tracking-widest text-ink-400 dark:text-ink-500 mb-1.5">
        Sources
      </p>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((source, i) => (
          <div key={`${source.title}-${i}`} className="relative">
            <button
              type="button"
              onClick={() => setOpenIndex(openIndex === i ? null : i)}
              className="flex items-center gap-1.5 rounded-lg border border-ink-100 dark:border-ink-700 bg-ink-50 dark:bg-ink-800 px-2.5 py-1.5 text-xs text-ink-700 dark:text-ink-200 hover:bg-pel-50 dark:hover:bg-ink-700 hover:border-pel-200 dark:hover:border-pel-800 transition-colors"
            >
              <FileText className="h-3.5 w-3.5 text-pel-600 dark:text-pel-400" />
              {source.title}
            </button>
            {openIndex === i && (
              <div className="absolute z-10 mt-1 w-56 rounded-lg border border-ink-100 dark:border-ink-700 bg-white dark:bg-ink-800 p-3 shadow-lg text-xs">
                <p className="font-medium text-ink-800 dark:text-ink-100">{source.title}</p>
                {source.page !== undefined && (
                  <p className="text-ink-500 dark:text-ink-400 mt-0.5">Page {source.page}</p>
                )}
                {source.section && (
                  <p className="text-ink-500 dark:text-ink-400 mt-0.5">Section: {source.section}</p>
                )}
                <p className="text-ink-400 dark:text-ink-500 mt-1.5">Approved PEL document</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
