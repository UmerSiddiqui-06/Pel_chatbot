import type { ReactNode } from "react";
import pelLogo from "../assets/pel-logo.png";
import { ThemeToggle } from "../components/ui/ThemeToggle";
import { AmbientGlow } from "../components/branding/AmbientGlow";
import { useTheme } from "../hooks/useTheme";

export function UserLayout({ children }: { children: ReactNode }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="h-screen w-full flex flex-col bg-porcelain dark:bg-ink-950 font-sans transition-colors duration-300 animate-rise-in">
      <AmbientGlow />

      <header className="h-16 shrink-0 border-b border-ink-100 dark:border-ink-800 bg-white/80 dark:bg-ink-900/80 backdrop-blur-md flex items-center justify-between px-6 relative">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-pel-500 to-pel-800 rotate-45 shadow-sm shadow-pel-900/20">
            <img src={pelLogo} alt="PEL" className="h-4 w-4 -rotate-45" />
          </div>
          <div className="leading-tight">
            <p className="font-display font-semibold text-sm text-ink-900 dark:text-white tracking-tight">
              PEL AI
            </p>
            <p className="text-[11px] font-mono uppercase tracking-wide text-ink-400 dark:text-ink-400">
              Knowledge Assistant
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
          <div className="h-8 w-8 rounded-full bg-pel-100 dark:bg-pel-900 text-pel-700 dark:text-pel-200 text-xs font-semibold flex items-center justify-center ring-1 ring-pel-200 dark:ring-pel-800">
            U
          </div>
        </div>
      </header>

      <div className="flex-1 min-h-0 relative">{children}</div>
    </div>
  );
}
