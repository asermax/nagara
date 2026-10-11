import { fileURLToPath } from "node:url";
import { cloudflareTest, readD1Migrations } from "@cloudflare/vitest-plugin";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const migrations = await readD1Migrations("../common/migrations");

const CONVERSATION = fileURLToPath(new URL("./src/agents/conversation.ts", import.meta.url).href);
const SCRIPTED_AGENTS = fileURLToPath(
  new URL("./test/helpers/scripted-agents.ts", import.meta.url).href,
);

// The pool never builds the Flue agents' Durable Objects, so every import of the agent
// conversation resolves to the test stand-in instead; the production bundle never carries it.
const scriptedAgents: Plugin = {
  name: "nagara-scripted-agents",
  enforce: "pre",
  resolveId: async function (source, importer, options) {
    if (importer == null || importer === SCRIPTED_AGENTS || !source.endsWith("conversation.ts")) {
      return null;
    }

    const resolved = await this.resolve(source, importer, { ...options, skipSelf: true });

    return resolved?.id === CONVERSATION ? SCRIPTED_AGENTS : null;
  },
};

export default defineConfig({
  plugins: [
    scriptedAgents,
    cloudflareTest({
      main: "./src/index.ts",
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        compatibilityDate: "2026-09-01",
        compatibilityFlags: ["nodejs_compat"],
        bindings: {
          TEST_MIGRATIONS: migrations,
          R2_UPLOAD_ENDPOINT: "https://tunnel.test/s3",
          pollIntervalSeconds: 0,
          MODAL_START_URL: "https://modal.test/start",
          MODAL_RESULT_URL: "https://modal.test/result",
          CLOUDFLARE_API_KEY: "test-gateway-token",
          FIRECRAWL_API_KEY: "test-firecrawl-key",
          GEMINI_API_KEY: "test-gemini-key",
          MODAL_PROXY_KEY: "test-modal-key",
          MODAL_PROXY_SECRET: "test-modal-secret",
          R2_PUT_ACCESS_KEY_ID: "test-access-key",
          R2_PUT_SECRET_ACCESS_KEY: "test-secret-key",
        },
      },
    }),
  ],
  test: {
    include: ["test/**/*.test.ts"],
    setupFiles: ["./test/setup.ts"],
  },
});
