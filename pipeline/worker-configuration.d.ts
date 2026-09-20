declare namespace Cloudflare {
  interface Exports {
    default: {
      fetch(request: Request, env?: unknown): Promise<Response>;
    };
  }

  interface Env {
    LOADER: WorkerLoader;
    EXTRACTION: Workflow;
    DOMAIN_QUEUE: DurableObjectNamespace;
    JOB_INDEX: DurableObjectNamespace;

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
