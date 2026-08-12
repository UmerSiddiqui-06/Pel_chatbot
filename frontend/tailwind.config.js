/** @type {import('tailwindcss').Config} */
export default {
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
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
}

