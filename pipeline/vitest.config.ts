import { cloudflareTest, readD1Migrations } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

const GAVE_UP =
  '```json\n{"kind": "gave-up", "reason": "no reply was scripted for this test"}\n```';

const migrations = await readD1Migrations("../common/migrations");

export default defineConfig({
  plugins: [
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
          scriptedAgentReplies: JSON.stringify({ author: GAVE_UP, revision: GAVE_UP }),
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
