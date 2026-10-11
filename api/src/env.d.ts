declare namespace Cloudflare {
  interface Env {
    DB: D1Database;
    ITEM_WORKFLOW: Workflow<import("@nagara/common").ItemWorkflowParams>;
    R2_S3_ENDPOINT: string;
    R2_BUCKET: string;
    RETRY_MAX: number;
    REQUEUE_AFTER_MS: number;
    API_KEY: string;
    R2_GET_ACCESS_KEY_ID: string;
    R2_GET_SECRET_ACCESS_KEY: string;
  }
}
