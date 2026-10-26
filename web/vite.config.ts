import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run dev` serves the UI with hot reload on this PC and forwards API and socket calls to the
// Python server (which must be running). Phones always use the built app served by the Python server.
const backend = "https://localhost:8443";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: backend, secure: false },
      "/ws": { target: backend, secure: false, ws: true },
    },
  },
});
