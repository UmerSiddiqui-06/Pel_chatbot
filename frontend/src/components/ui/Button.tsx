import type { ButtonHTMLAttributes, ReactNode } from "react";
import clsx from "clsx";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost" | "icon";
  children?: ReactNode;
}

export function Button({ variant = "primary", className, children, ...props }: ButtonProps) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed",
        variant === "primary" && "bg-pel-600 text-white px-3 py-2 hover:bg-pel-700",
        variant === "ghost" && "text-slate-600 px-3 py-2 hover:bg-slate-100",
        variant === "icon" && "h-9 w-9 text-slate-500 hover:bg-slate-100 hover:text-slate-700",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
