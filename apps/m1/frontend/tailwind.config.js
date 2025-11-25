/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bgDark: "#0B0C10",                  // 전체 배경 다크톤
        glassLight: "rgba(255,255,255,0.1)", // 유리 효과용 배경
      },
      boxShadow: {
        glass: "0 4px 30px rgba(0,0,0,0.3)", // 부드러운 그림자
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
