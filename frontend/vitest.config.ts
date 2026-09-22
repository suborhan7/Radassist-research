import { defineConfig } from "vitest/config";
import path from "node:path";

/**
 * Phase 18: this project's first frontend test runner (previously zero
 * *.test.ts files existed anywhere -- see phase18_diff_view_architecture.md
 * Step 2). Vitest, not Jest, chosen for near-zero-config native ESM/TS
 * support matching this Next.js 16 App Router stack -- confirmed with the
 * user before adding, same discipline as confirming `diff` wasn't already
 * a dependency before installing it.
 *
 * Only the `@/*` alias needs wiring here (tsconfig.json's existing path
 * mapping) -- Vitest runs on Vite, which doesn't read tsconfig `paths`
 * automatically the way Next.js's own bundler does.
 */
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    /**
     * Node stays the DEFAULT on purpose, and jsdom is opted into per file with
     * a `@vitest-environment jsdom` docblock (see the component tests under
     * src/components/report/).
     *
     * Switching the whole project to jsdom would have been one line, but it
     * would put every existing pure test -- report-diff, the label-list
     * snapshot, the consistency and disclosure rules -- inside a simulated
     * browser they have no use for. That is slower on every run, and it also
     * changes what those tests prove: code that accidentally reached for
     * `window` would start passing in a suite whose point is that it does not
     * need one. The component tests need a DOM and say so; nothing else
     * acquires one by default.
     */
    environment: "node",
  },
});
