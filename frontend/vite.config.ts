// @lovable.dev/vite-tanstack-config already includes standard plugins
import { defineConfig } from "@lovable.dev/vite-tanstack-config";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  vite: {
    resolve: {
      alias: {
        "lucide-react": path.resolve(__dirname, "node_modules/lucide-react/dist/esm/lucide-react.mjs"),
      },
    },
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
