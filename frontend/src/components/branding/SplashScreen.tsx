import { useEffect, useState } from "react";
import { PelMark } from "./PelMark";

interface Props {
  theme: "light" | "dark";
  onFinished: () => void;
}

/**
 * Orchestrated load sequence: mark scales/fades in over a breathing glow,
 * holds briefly, then the whole scrim fades to transparent (not a wipe —
 * a wipe reads as a "loading complete" transition; a fade reads as the
 * mark settling into the interface, which is the effect we want here).
 * Colors follow the live theme so it never shows dark-on-dark or
 * light-on-light regardless of what the user last picked.
 */
export function SplashScreen({ theme, onFinished }: Props) {
  const [visible, setVisible] = useState(true);
  const isDark = theme === "dark";

  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), 1200);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      onTransitionEnd={(e) => {
        if (e.propertyName === "opacity" && !visible) onFinished();
      }}
      className={`fixed inset-0 z-50 flex items-center justify-center transition-opacity duration-700 ease-out ${
        visible ? "opacity-100" : "opacity-0 pointer-events-none"
      } ${isDark ? "bg-ink-950" : "bg-porcelain"}`}
    >
      <div className="relative flex items-center justify-center">
        <div
          className={`absolute h-56 w-56 rounded-full blur-3xl animate-glow-breathe ${
            isDark ? "bg-pel-500/40" : "bg-pel-400/25"
          }`}
        />
        <PelMark size={88} animated className="relative" />
      </div>
      <div className="absolute bottom-16 left-1/2 -translate-x-1/2 text-center">
        <p
          className={`font-display text-sm tracking-[0.3em] uppercase ${
            isDark ? "text-ink-200" : "text-ink-700"
          }`}
        >
          PEL AI
        </p>
        <p className={`text-xs mt-1 ${isDark ? "text-ink-400" : "text-ink-500"}`}>Knowledge Assistant</p>
      </div>
    </div>
  );
}
