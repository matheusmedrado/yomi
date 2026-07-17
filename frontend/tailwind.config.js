/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Kodansha-inspired editorial palette.
        ink: {
          DEFAULT: "#0a0a0a",
          soft: "#1a1a1a",
          muted: "#5b5b5b",
        },
        paper: {
          DEFAULT: "#fafaf7",
          warm: "#f3f1ea",
          shadow: "#e8e5dc",
        },
        vermilion: {
          DEFAULT: "#c8102e",
          deep: "#9a0a23",
        },
        kd: {
          // Kodansha smallcaps / kicker accent — used very sparingly.
          accent: "#c8102e",
        },
      },
      fontFamily: {
        serif: ['"Noto Serif JP"', '"Source Han Serif"', "Georgia", "serif"],
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      letterSpacing: {
        smallcaps: "0.18em",
      },
      boxShadow: {
        editorial: "0 1px 0 0 rgba(10, 10, 10, 0.08)",
        "editorial-lg": "0 12px 40px -16px rgba(10, 10, 10, 0.18)",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in": "fade-in 240ms ease-out both",
        "slide-up": "slide-up 320ms cubic-bezier(0.2, 0.7, 0.1, 1) both",
      },
    },
  },
  plugins: [],
};
