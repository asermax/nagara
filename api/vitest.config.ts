import { cloudflareTest, readD1Migrations } from "@cloudflare/vitest-plugin";
import { defineConfig } from "vitest/config";

const migrations = await readD1Migrations("../common/migrations");

export default defineConfig({
  plugins: [
    cloudflareTest({
      main: "./src/index.ts",
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        // The ITEM_WORKFLOW binding names the pipeline Worker by script, and the pool refuses to
        // start while that script is missing; the tests hand the routes a recording stand-in.
        workers: [
          {
            name: "nagara",
            modules: true,
            scriptPath: "./test/fixtures/pipeline-placeholder.js",
            compatibilityDate: "2026-09-01",
          },
        ],
        // These win over a local .dev.vars, whose S3 endpoint carries a path the redirect tests
        // do not expect.
        bindings: {
          TEST_MIGRATIONS: migrations,
          API_KEY: "test-key",
          R2_S3_ENDPOINT: "https://test-account.r2.cloudflarestorage.com",
          R2_GET_ACCESS_KEY_ID: "test-access-key-id",
          R2_GET_SECRET_ACCESS_KEY: "test-secret-access-key",
        },
      },
    }),
  ],
  test: {
    include: ["test/**/*.test.ts"],
    setupFiles: ["./test/setup.ts"],
  },
});
