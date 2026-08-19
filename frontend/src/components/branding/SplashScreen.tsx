import { useEffect, useState } from "react";
import { PelMark } from "./PelMark";

interface Props {
  onFinished: () => void;
}

/**
 * Orchestrated load sequence, deliberately one moment rather than several
 * scattered effects: mark scales/fades in over a breathing glow (900ms),
 * holds briefly, then the whole scrim iris-wipes open from center to
 * reveal the chat shell already mounted underneath it.
 */
export function SplashScreen({ onFinished }: Props) {
  const [wiping, setWiping] = useState(false);

  useEffect(() => {
    const holdTimer = setTimeout(() => setWiping(true), 1150);
    const doneTimer = setTimeout(onFinished, 1150 + 900);
    return () => {
      clearTimeout(holdTimer);
      clearTimeout(doneTimer);
    };
  }, [onFinished]);

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center bg-ink-950 ${
        wiping ? "animate-iris-wipe" : ""
      }`}
    >
      <div className="relative flex items-center justify-center">
        <div className="absolute h-56 w-56 rounded-full bg-pel-500/40 blur-3xl animate-glow-breathe" />
        <PelMark size={88} animated className="relative" />
      </div>
      <div className="absolute bottom-16 left-1/2 -translate-x-1/2 text-center">
        <p className="font-display text-sm tracking-[0.3em] text-ink-200 uppercase">PEL AI</p>
        <p className="text-xs text-ink-400 mt-1">Knowledge Assistant</p>
      </div>
    </div>
  );
}
