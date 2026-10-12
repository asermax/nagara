import { cloudflare } from "@cloudflare/vite-plugin";
import { flue, flueWorkerConfig } from "@flue/vite";
import { defineConfig } from "vite";

// Dummy keys for the local S3 endpoint the dev server serves at /cdn-cgi/local/r2/s3, which checks
// presigned URLs against them. They protect nothing and are the same values .dev.vars.example
// gives both Workers' R2 keys.
const LOCAL_S3_CREDENTIALS = {
  accessKeyId: "nagaralocalaccesskey",
  secretAccessKey: "nagaralocalsecretkey",
};

type R2Binding = { binding: string; local_dev?: { experimental_s3_credentials: object } };

// The API Worker's wrangler dev persists to the same folder, so both Workers see one D1 database
// and one bucket. The local S3 credentials are added only when serving, so the built deploy config
// never carries them.
export default defineConfig(({ command }) => {
  // flueWorkerConfig binds to the flue() instance created before it in the same evaluation.
  const fluePlugins = flue();
  const flueConfig = flueWorkerConfig();

  return {
    server: { port: 5173, strictPort: true },
    plugins: [
      fluePlugins,
      cloudflare({
        persistState: { path: "../.wrangler-state" },
        config: (config) => {
          flueConfig(config);

          if (command !== "serve") {
            return;
          }

          for (const bucket of (config as { r2_buckets?: R2Binding[] }).r2_buckets ?? []) {
            bucket.local_dev = { experimental_s3_credentials: LOCAL_S3_CREDENTIALS };
          }
        },
      }),
    ],
  };
});
