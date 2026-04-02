import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#1A1A2E",
        accent: "#E94560",
        sub: "#0F3460",
        "bg-main": "#F8F9FA",
      },
      fontFamily: {
        sans: ["Inter", "Noto Sans JP", "sans-serif"],
      },
      minWidth: {
        app: "1024px",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
