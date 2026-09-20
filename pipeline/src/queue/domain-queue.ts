import { DurableObject } from "cloudflare:workers";

interface QueuedJob {
  jobId: string;
  params: { html: string; recipe?: string; domain: string };
}

interface Lease {
  jobId: string;
}

const TERMINAL_INSTANCE_STATUSES = new Set(["complete", "errored", "terminated"]);

function describeError(error: unknown): string {
  if (error instanceof Error) {
    return `${error.name}: ${error.message}`;
  }
  return String(error);
}

export class DomainQueue extends DurableObject<Cloudflare.Env> {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/enqueue") {
      return await this.enqueue(await request.json());
    }
    if (request.method === "POST" && url.pathname === "/release") {
      return await this.release(await request.json());
    }
    if (request.method === "GET" && url.pathname.startsWith("/state/")) {
      return await this.stateOf(url.pathname.slice("/state/".length));
    }
    return new Response("not found", { status: 404 });
  }

  private async enqueue(body: { job_id: string; params: QueuedJob["params"] }): Promise<Response> {
    const jobId = body.job_id;
    let created = false;
    let conflict = false;
    let failure: string | null = null;
    try {
      await this.ctx.blockConcurrencyWhile(async () => {
        const lease = await this.ctx.storage.get<Lease>("lease");
        const fifo = (await this.ctx.storage.get<QueuedJob[]>("fifo")) ?? [];
        if (lease?.jobId === jobId || fifo.some((entry) => entry.jobId === jobId)) {
          conflict = true;
          return;
        }
        // The platform's create() does not reliably reject an existing id
        // locally, so the write-once index is the duplicate check: every id
        // ever enqueued lands there before the create runs.
        if ((await this.readIndexEntry(jobId)) != null) {
          conflict = true;
          return;
        }
        if (lease == null) {
          // The instance is created before the lease is persisted, both inside
          // this single-threaded window, so a create that throws leaves no
          // lease behind for the alarm to sweep.
          await this.env.EXTRACTION.create({ id: jobId, params: body.params });
          await this.ctx.storage.put("lease", { jobId });
          await this.ctx.storage.setAlarm(Date.now() + this.env.leaseAlarmMs);
          created = true;
        } else {
          fifo.push({ jobId, params: body.params });
          await this.ctx.storage.put("fifo", fifo);
        }
        // The index entry is awaited before the enqueue replies: an id that
        // has no instance yet stays reachable for the read path.
        await this.writeIndexEntry(jobId, body.params.domain);
      });
    } catch (error) {
      failure = describeError(error);
    }
    if (failure != null) {
      return Response.json({ error: `creating the workflow failed: ${failure}` }, { status: 500 });
    }
    if (conflict) {
      return Response.json({ error: "the job id already exists" }, { status: 409 });
    }
    return Response.json({ created });
  }

  private async readIndexEntry(jobId: string): Promise<string | null> {
    const id = this.env.JOB_INDEX.idFromName("nagara-job-index");
    const response = await this.env.JOB_INDEX.get(id).fetch(
      `https://index/entries/${encodeURIComponent(jobId)}`,
    );
    if (response.status === 404) {
      return null;
    }
    const { domain } = (await response.json()) as { domain: string };
    return domain;
  }

  private async writeIndexEntry(jobId: string, domain: string): Promise<void> {
    const id = this.env.JOB_INDEX.idFromName("nagara-job-index");
    const response = await this.env.JOB_INDEX.get(id).fetch("https://index/entries", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ job_id: jobId, domain }),
    });
    if (!response.ok) {
      throw new Error(`the job index rejected the entry: ${response.status}`);
    }
  }

  private async release(body: { job_id: string }): Promise<Response> {
    await this.ctx.blockConcurrencyWhile(async () => {
      const lease = await this.ctx.storage.get<Lease>("lease");
      if (lease?.jobId !== body.job_id) {
        return;
      }
      await this.ctx.storage.delete("lease");
      await this.advance();
    });
    return Response.json({ released: true });
  }

  private async stateOf(jobId: string): Promise<Response> {
    const lease = await this.ctx.storage.get<Lease>("lease");
    const fifo = (await this.ctx.storage.get<QueuedJob[]>("fifo")) ?? [];
    if (fifo.some((entry) => entry.jobId === jobId)) {
      return Response.json({ state: "queued" });
    }
    if (lease?.jobId === jobId) {
      return Response.json({ state: "running" });
    }
    return Response.json({ state: "unknown" });
  }

  private async advance(): Promise<void> {
    const fifo = (await this.ctx.storage.get<QueuedJob[]>("fifo")) ?? [];
    while (fifo.length > 0) {
      const next = fifo.shift() as QueuedJob;
      try {
        await this.env.EXTRACTION.create({ id: next.jobId, params: next.params });
      } catch {
        // A fifo entry that cannot create must not wedge the queue behind
        // it: drop it and try the next, exactly as a sweep would.
        continue;
      }
      await this.ctx.storage.put("fifo", fifo);
      await this.ctx.storage.put("lease", { jobId: next.jobId });
      await this.ctx.storage.setAlarm(Date.now() + this.env.leaseAlarmMs);
      return;
    }
    await this.ctx.storage.put("fifo", fifo);
    await this.ctx.storage.deleteAlarm();
  }

  async alarm(): Promise<void> {
    const lease = await this.ctx.storage.get<Lease>("lease");
    if (lease == null) {
      return;
    }
    let ended = false;
    try {
      const instance = await this.env.EXTRACTION.get(lease.jobId);
      const status = await instance.status();
      ended = TERMINAL_INSTANCE_STATUSES.has(status.status);
    } catch {
      // An unaddressable instance sweeps like an ended one: the lease
      // cannot be verified, and the queue must move on.
      ended = true;
    }
    if (ended) {
      await this.ctx.storage.delete("lease");
      await this.advance();
      return;
    }
    await this.ctx.storage.setAlarm(Date.now() + this.env.leaseAlarmMs);
  }
}
