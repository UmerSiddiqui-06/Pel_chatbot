import { Moon, Sun } from "lucide-react";

interface Props {
  theme: "light" | "dark";
  onToggle: () => void;
}

export function ThemeToggle({ theme, onToggle }: Props) {
  const isDark = theme === "dark";
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      aria-pressed={isDark}
      className="relative flex h-8 w-16 items-center rounded-full border border-ink-200 dark:border-ink-600 bg-ink-100 dark:bg-ink-800 px-1 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-pel-500"
    >
      <Sun className="absolute left-1.5 h-4 w-4 text-pel-600 dark:text-ink-500" />
      <Moon className="absolute right-1.5 h-4 w-4 text-ink-300 dark:text-pel-300" />
      <span
        className={`z-10 flex h-6 w-6 items-center justify-center rounded-md bg-gradient-to-br from-pel-500 to-pel-700 shadow transition-transform duration-300 rotate-45 ${
          isDark ? "translate-x-8" : "translate-x-0"
        }`}
      >
        <span className="h-1.5 w-1.5 rounded-sm bg-white/90 -rotate-45" />
      </span>
    </button>
  );
}
