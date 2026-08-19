export function AmbientGlow() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden -z-10">
      <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full bg-pel-500/10 dark:bg-pel-500/20 blur-3xl" />
      <div className="absolute -bottom-32 -left-24 h-96 w-96 rounded-full bg-pel-700/10 dark:bg-pel-400/10 blur-3xl" />
      {/* faint geometric grid, barely-there texture rather than decoration */}
      <div
        className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05]"
        style={{
          backgroundImage:
            "linear-gradient(currentColor 1px, transparent 1px), linear-gradient(90deg, currentColor 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />
    </div>
  );
}
