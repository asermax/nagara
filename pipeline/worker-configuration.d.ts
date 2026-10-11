declare namespace Cloudflare {
  interface Exports {
    default: {
      fetch(request: Request, env?: unknown): Promise<Response>;
    };
  }

  interface Env {
    LOADER: WorkerLoader;
    ITEM_WORKFLOW: Workflow<import("@nagara/common").ItemWorkflowParams>;
    DOMAIN_QUEUE: DurableObjectNamespace<import("./src/queue/domain-queue.ts").DomainQueue>;
    DB: D1Database;
    BUCKET: R2Bucket;
    IMAGES: ImagesBinding;

    agentModel: string;
    CLOUDFLARE_ACCOUNT_ID: string;
    CLOUDFLARE_GATEWAY_ID: string;
    agentMaxTurns: number;
    authoringRetries: number;
    revisionRetries: number;
    leaseAlarmMs: number;
    recipeCpuMs: number;
    maxHtmlBytes: number;
    R2_S3_ENDPOINT: string;
    R2_UPLOAD_ENDPOINT: string;
    R2_BUCKET: string;
    MODAL_START_URL: string;
    MODAL_RESULT_URL: string;
    describeMaxPerItem: number;
    imageFetchPerHost: number;
    imageFetchConcurrency: number;
    pollIntervalSeconds: number;
    firecrawlDollarsPerCredit: number;
    describerDollarsPerCall: number;
    ttsDollarsPerSecond: number;
    scriptedAgentReplies?: string;

    CLOUDFLARE_API_KEY: string;
    FIRECRAWL_API_KEY: string;
    GEMINI_API_KEY: string;
    MODAL_PROXY_KEY: string;
    MODAL_PROXY_SECRET: string;
    R2_PUT_ACCESS_KEY_ID: string;
    R2_PUT_SECRET_ACCESS_KEY: string;
  }
}
