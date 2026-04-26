import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        premium: "0 0 0 1px rgba(148,163,184,0.15), 0 12px 30px rgba(2,6,23,0.45)",
      },
      backgroundImage: {
        "hero-radial":
          "radial-gradient(circle at 0% 0%, rgba(99,102,241,0.18), transparent 35%), radial-gradient(circle at 100% 100%, rgba(16,185,129,0.16), transparent 35%)",
      },
    },
  },
  plugins: [],
} satisfies Config;
