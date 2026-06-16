import type { Config } from "tailwindcss";

// Palette adapted from CoinGecko (brand.coingecko.com): Gecko Green #4BCC00 as
// the primary accent, Moon Night #0D1217 as the dark base. The `gray`, `blue`,
// and `green` scales below are deliberately overridden so the existing utility
// classes scattered across the app (bg-gray-950, text-blue-400, bg-green-600…)
// resolve to the CoinGecko palette without touching every className. New code
// should prefer the semantic tokens (surface/accent/up/down).
const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Semantic tokens — preferred for new code.
        surface: {
          base: "#0D1217",   // Moon Night — page background
          raised: "#151C24", // cards / panels
          overlay: "#1C2530", // inputs, hovered rows
        },
        accent: {
          DEFAULT: "#4BCC00", // Gecko Green
          hover: "#5CE619",
          muted: "#1F3010",   // tinted backgrounds (badges, fills)
        },
        up: "#4BCC00",   // positive / win
        down: "#EA3943", // negative / loss (CoinGecko red)

        // Brand alias kept for any existing `brand-*` references.
        brand: {
          50: "#eefbe4",
          500: "#4BCC00",
          700: "#3da300",
          900: "#1F3010",
        },
        confidence: {
          high: "#4BCC00",
          medium: "#F0B90B",
          low: "#EA3943",
        },

        // --- Overridden Tailwind scales (CoinGecko-tuned) -------------------
        // `gray` → cool, near-black Moon Night neutrals.
        gray: {
          50: "#F7FAFC",
          100: "#EAEFF4",
          200: "#D2DAE3",
          300: "#A4B0BE",
          400: "#7E8B9B",
          500: "#6B7888",
          600: "#4A5663",
          700: "#2C3A48",
          800: "#1F2933",
          900: "#151C24",
          950: "#0D1217",
        },
        // `blue` → Gecko Green so legacy accent classes (text-blue-400, etc.)
        // render on-brand.
        blue: {
          300: "#7CE63C",
          400: "#5CE619",
          500: "#4BCC00",
          600: "#3da300",
          700: "#327f00",
          900: "#1F3010",
        },
        // `green` → align positive/up usage with Gecko Green.
        green: {
          300: "#7CE63C",
          500: "#4BCC00",
          600: "#3da300",
          900: "#1F3010",
        },
        // `red` → CoinGecko down red.
        red: {
          300: "#F4838A",
          400: "#EA3943",
          600: "#D32F38",
          700: "#B0262E",
          900: "#3A1416",
        },
        // `purple` (narrative accents) → a green-leaning teal so the palette
        // stays cohesive rather than introducing an off-brand hue.
        purple: {
          300: "#5BD6B0",
          400: "#3FC79C",
          600: "#1FA37C",
          900: "#10362B",
        },
      },
    },
  },
  plugins: [],
};
export default config;
