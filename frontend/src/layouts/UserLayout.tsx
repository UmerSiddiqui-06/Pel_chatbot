import type { ReactNode } from "react";
import pelLogo from "../assets/pel-logo.png";

export function UserLayout({ children }: { children: ReactNode }) {
  return (
    <div className="h-screen w-full flex flex-col bg-slate-50 font-sans">
      <header className="h-14 shrink-0 border-b border-slate-200 bg-white flex items-center justify-between px-5">
        <div className="flex items-center gap-2.5">
          <img src={pelLogo} alt="PEL" className="h-7 w-7" />
          <span className="text-sm font-semibold text-slate-800 tracking-tight">PEL AI — Knowledge Assistant</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-full bg-pel-100 text-pel-700 text-xs font-semibold flex items-center justify-center">
            U
          </div>
        </div>
      </header>
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  );
}
