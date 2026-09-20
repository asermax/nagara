declare namespace Cloudflare {
  interface Exports {
    default: {
      fetch(request: Request, env?: unknown): Promise<Response>;
    };
  }

  interface Env {
    LOADER: WorkerLoader;
    EXTRACTION: Workflow;
    DOMAIN_QUEUE: DurableObjectNamespace<import("./src/queue/domain-queue.ts").DomainQueue>;
    JOB_INDEX: DurableObjectNamespace<import("./src/queue/job-index.ts").JobIndex>;

    agentModel: string;
    agentMaxTurns: number;
    authoringRetries: number;
    revisionRetries: number;
    leaseAlarmMs: number;
    indexSweepMs: number;
    recipeCpuMs: number;
    maxHtmlBytes: number;
  }
}
