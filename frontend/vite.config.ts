// @lovable.dev/vite-tanstack-config already includes standard plugins
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  vite: {
    ssr: {
      noExternal: ["lucide-react", "@radix-ui/*"],
    },
    optimizeDeps: {
      include: ["lucide-react"],
    },
  },
  tanstackStart: {
    // Redirect TanStack Start's bundled server entry to src/server.ts
    server: { entry: "server" },
  },
});
