import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./renderer/src/**/*.{js,ts,jsx,tsx,html}",
    "./renderer/index.html",
    "./renderer/overlay.html",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          violet: "#6C3AFF",
          "violet-dark": "#5228E8",
          "violet-light": "#8B5CF6",
          teal: "#00D4AA",
          "teal-dark": "#00B894",
          "teal-light": "#34DDB8",
        },
        surface: {
          base: "#0A0A0F",
          elevated: "#12121A",
          card: "#1A1A26",
          overlay: "rgba(10, 10, 15, 0.92)",
        },
        text: {
          primary: "#F0F0FF",
          secondary: "#A0A0C0",
          muted: "#606080",
        },
        state: {
          success: "#00D4AA",
          warning: "#F59E0B",
          error: "#EF4444",
          info: "#6C3AFF",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      backgroundImage: {
        "gradient-brand":
          "linear-gradient(135deg, #6C3AFF 0%, #00D4AA 100%)",
        "gradient-card":
          "linear-gradient(135deg, rgba(108, 58, 255, 0.1) 0%, rgba(0, 212, 170, 0.05) 100%)",
        "gradient-overlay":
          "linear-gradient(180deg, rgba(10, 10, 15, 0.0) 0%, rgba(10, 10, 15, 0.85) 100%)",
      },
      boxShadow: {
        "brand-glow": "0 0 30px rgba(108, 58, 255, 0.3)",
        "teal-glow": "0 0 20px rgba(0, 212, 170, 0.25)",
        "card-elevated": "0 8px 32px rgba(0, 0, 0, 0.4)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-up": "slideUp 0.4s ease-out",
        "stream-in": "streamIn 0.1s ease-out",
        shimmer: "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        streamIn: {
          "0%": { opacity: "0", transform: "translateX(-4px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
    },
  },
  plugins: [],
};

export default config;
