import { useState } from "react";
import { FileText } from "lucide-react";
import type { Source } from "../../types/chat";

export function SourceList({ sources }: { sources?: Source[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3">
      <p className="text-xs font-mono uppercase tracking-wide text-slate-400 mb-1.5">Sources</p>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((source, i) => (
          <div key={`${source.title}-${i}`} className="relative">
            <button
              type="button"
              onClick={() => setOpenIndex(openIndex === i ? null : i)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-100 transition-colors"
            >
              <FileText className="h-3.5 w-3.5 text-pel-600" />
              {source.title}
            </button>
            {openIndex === i && (
              <div className="absolute z-10 mt-1 w-56 rounded-lg border border-slate-200 bg-white p-3 shadow-lg text-xs">
                <p className="font-medium text-slate-800">{source.title}</p>
                {source.page !== undefined && <p className="text-slate-500 mt-0.5">Page {source.page}</p>}
                {source.section && <p className="text-slate-500 mt-0.5">Section: {source.section}</p>}
                <p className="text-slate-400 mt-1.5">Approved PEL document</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
