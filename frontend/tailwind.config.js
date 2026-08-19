/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // PEL brand blue, sampled from the logo (#007DC6), expanded into a scale
        pel: {
          50: "#eff8ff",
          100: "#dcefff",
          200: "#b3ddff",
          300: "#7ac3ff",
          400: "#3aa4f7",
          500: "#0f88e0",
          600: "#007dc6", // brand core
          700: "#0463a0",
          800: "#095282",
          900: "#0d456c",
          950: "#082c47",
        },
        // Moderate charcoal graphite (not slate, not near-black) — used for
        // dark-mode surfaces and the splash.
        ink: {
          50: "#f4f6f8",
          100: "#e6eaef",
          200: "#ccd2da",
          300: "#a7b0bd",
          400: "#7c8798",
          500: "#556074",
          600: "#3c4658",
          700: "#2f3846",
          800: "#232a36",
          900: "#1b212b",
          950: "#14181f",
        },
        // cool off-white for light-mode ground (deliberately not cream)
        porcelain: "#f5f7fa",
      },
      fontFamily: {
        display: ['"Space Grotesk"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      keyframes: {
        "mark-in": {
          "0%": { opacity: "0", transform: "scale(0.7) rotate(45deg)" },
          "60%": { opacity: "1", transform: "scale(1.04) rotate(45deg)" },
          "100%": { opacity: "1", transform: "scale(1) rotate(45deg)" },
        },
        "glow-breathe": {
          "0%, 100%": { opacity: "0.55", transform: "scale(1)" },
          "50%": { opacity: "0.85", transform: "scale(1.08)" },
        },
        "rise-in": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "mark-in": "mark-in 700ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
        "glow-breathe": "glow-breathe 3.2s ease-in-out infinite",
        "rise-in": "rise-in 500ms cubic-bezier(0.16, 1, 0.3, 1) forwards",
      },
    },
  },
  plugins: [],
}
