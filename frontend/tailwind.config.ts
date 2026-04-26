import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f1418",
        mist: "#dce8ef",
        portal: "#5fa6c9"
      }
    }
  },
  plugins: []
};

export default config;
