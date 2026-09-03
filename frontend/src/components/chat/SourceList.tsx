import { useEffect, useRef, useState } from "react";
import { Film, FileText } from "lucide-react";
import type { Source } from "../../types/chat";

export function SourceList({ sources }: { sources?: Source[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [videoIndex, setVideoIndex] = useState(0);
  const detailsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (openIndex === null || !detailsRef.current) return;

    requestAnimationFrame(() => {
      detailsRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }, [openIndex]);

  if (!sources || sources.length === 0) return null;

  const videoSources = Array.from(
    new Map(
      sources
        .filter((source) => source.videoUrl)
        .map((source) => [source.videoUrl, source] as const)
    ).values()
  );
  const selectedVideo = videoSources[videoIndex] ?? videoSources[0];
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";
  const videoUrl = selectedVideo?.videoUrl
    ? selectedVideo.videoUrl.startsWith("http")
      ? selectedVideo.videoUrl
      : `${apiBaseUrl}${selectedVideo.videoUrl}`
    : undefined;

  return (
    <div ref={detailsRef} className="mt-3">
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
              <div className="mt-2 w-full max-w-sm rounded-lg border border-ink-100 dark:border-ink-700 bg-white dark:bg-ink-800 p-3 shadow-lg text-xs">
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
      {selectedVideo && videoUrl && (
        <div className="mt-3 overflow-hidden rounded-xl border border-ink-200 bg-ink-950 shadow-sm dark:border-ink-700">
          <div className="flex items-center justify-between gap-3 px-3 py-2.5">
            <div className="flex min-w-0 items-center gap-2 text-xs text-white">
              <Film className="h-4 w-4 shrink-0 text-pel-300" />
              <span className="truncate font-medium">
                Page {selectedVideo.pageRange ?? selectedVideo.page ?? "reference"}
              </span>
            </div>
            <span className="shrink-0 text-[10px] uppercase tracking-widest text-ink-400">Reference video</span>
          </div>
          <video className="aspect-video w-full bg-black object-contain" controls preload="metadata" src={videoUrl} />
          {videoSources.length > 1 && (
            <div className="flex flex-wrap gap-1.5 border-t border-white/10 px-3 py-2.5">
              {videoSources.map((source, i) => (
                <button
                  key={`${source.videoUrl}-${i}`}
                  type="button"
                  onClick={() => setVideoIndex(i)}
                  className={`rounded-md px-2 py-1 text-[11px] transition-colors ${
                    i === videoIndex ? "bg-pel-500 text-white" : "bg-white/10 text-ink-300 hover:bg-white/20"
                  }`}
                >
                  {source.pageRange ?? `Page ${source.page ?? "reference"}`}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
