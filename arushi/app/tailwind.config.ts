import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
      colors: {
        cg: {
          page: "#0F0F10",
          stage: "#1A1A1B",
          ivory: "#F4F1EA",
          mist1: "#B0AAA0",
          mist2: "#9A9690",
          mist3: "#8A8478",
          mist4: "#7A746A",
          mist5: "#D8D4CC",
          peach: {
            DEFAULT: "#FFB088",
            mid: "#E87B43",
            deep: "#C2522B",
            ink: "#2A1709",
            inkHi: "#3A2410",
            ctx: "#FFE4D6",
          },
          sage: {
            DEFAULT: "#C8E4D0",
            mid: "#87A878",
            deep: "#5C7A4F",
            deepest: "#4A6B3F",
            ink: "#1F2A1A",
            ctx: "#E8F0E5",
          },
        },
      },
      backgroundImage: {
        "cg-grad-peach": "linear-gradient(140deg, #FFB088 0%, #E87B43 75%, #C2522B 100%)",
        "cg-grad-sage": "linear-gradient(140deg, #C8E4D0 0%, #87A878 70%, #5C7A4F 100%)",
        "cg-grad-logo-peach": "linear-gradient(135deg, #FFB088, #E87B43)",
        "cg-grad-logo-sage": "linear-gradient(135deg, #C8E4D0, #87A878)",
        "cg-bloom-peach": "radial-gradient(circle, #FFB088 0%, #E87B43 100%)",
        "cg-bloom-sage": "radial-gradient(circle, #C8E4D0 0%, #87A878 100%)",
        "cg-map-grid":
          "radial-gradient(circle at 30% 40%, rgba(255,176,136,0.12), transparent 40%), radial-gradient(circle at 70% 60%, rgba(135,168,120,0.10), transparent 45%), repeating-linear-gradient(0deg, rgba(255,255,255,0.025) 0 1px, transparent 1px 40px), repeating-linear-gradient(90deg, rgba(255,255,255,0.025) 0 1px, transparent 1px 40px)",
        // Legacy — preserved so doctor/NGO pages don't break.
        "hero-radial":
          "radial-gradient(circle at 0% 0%, rgba(99,102,241,0.18), transparent 35%), radial-gradient(circle at 100% 100%, rgba(16,185,129,0.16), transparent 35%)",
      },
      boxShadow: {
        "cg-peach": "0 12px 30px rgba(232, 123, 67, 0.25)",
        "cg-sage": "0 12px 30px rgba(135, 168, 120, 0.25)",
        // Legacy.
        premium: "0 0 0 1px rgba(148,163,184,0.15), 0 12px 30px rgba(2,6,23,0.45)",
      },
      borderRadius: {
        "cg-stage": "28px",
        "cg-card": "22px",
        "cg-card-sm": "18px",
        "cg-tile": "14px",
      },
      backdropBlur: {
        "cg-glass": "10px",
        "cg-sidebar": "20px",
        "cg-bloom": "70px",
      },
      letterSpacing: {
        "cg-overline": "0.10em",
        "cg-overline-wide": "0.12em",
        "cg-tight": "-0.02em",
        "cg-num": "-0.04em",
      },
      keyframes: {
        "cg-pulse-glow": {
          "0%,100%": { boxShadow: "0 0 0 4px rgba(74,107,63,0.25)" },
          "50%": { boxShadow: "0 0 0 7px rgba(74,107,63,0.15)" },
        },
      },
      animation: {
        "cg-pulse-glow": "cg-pulse-glow 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
} satisfies Config;
