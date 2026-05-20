/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F9F5EC",
        ink: "#1D1E22",
        clay: "#D46A4C",
        forest: "#1C5B4A",
        amber: "#E8A33A",
      },
      fontFamily: {
        display: ["Sora", "sans-serif"],
        mono: ["Space Mono", "monospace"],
      },
      boxShadow: {
        card: "0 12px 30px -12px rgba(0,0,0,0.2)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: 0, transform: "translateY(10px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
      },
      animation: {
        rise: "rise 400ms ease-out both",
      },
    },
  },
  plugins: [],
};
