import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    // Bind all interfaces so both http://localhost:5173 and
    // http://127.0.0.1:5173 resolve on machines where localhost is IPv6-only.
    host: true,
  },
});
