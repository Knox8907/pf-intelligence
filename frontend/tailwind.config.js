/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        pf: {
          red:    "#e63946",
          dark:   "#1a1a2e",
          navy:   "#16213e",
          mid:    "#0f3460",
        },
      },
      fontFamily: {
        sans: ["'DM Sans'", "system-ui", "sans-serif"],
        display: ["'Bebas Neue'", "sans-serif"],
      },
    },
  },
  plugins: [],
};
