import { DurableObject } from "cloudflare:workers";
import { describeError } from "../errors.ts";
import type { ExtractionParams } from "../workflow/extraction.ts";
import { jobIndexStub } from "./job-index.ts";

interface WaitingRef {
  jobId: string;
  key: string;
}

interface Lease {
  jobId: string;
}

export type EnqueueResult = { created: boolean } | { conflict: true };

const TERMINAL_INSTANCE_STATUSES = new Set(["complete", "errored", "terminated"]);

function waitingKey(seq: number): string {
  return `job:${String(seq).padStart(8, "0")}`;
}

export function domainQueueStub(env: Cloudflare.Env, domain: string) {
  return env.DOMAIN_QUEUE.get(env.DOMAIN_QUEUE.idFromName(domain));
}

// One instance per domain, the only creator of its domain's workflow
// instances: a lease names the running job and waiting jobs sit one storage
// key each (their params carry whole articles, so the FIFO is never rewritten
// as a single value).
export class DomainQueue extends DurableObject<Cloudflare.Env> {
  async enqueue(jobId: string, params: ExtractionParams): Promise<EnqueueResult> {
    let result: EnqueueResult = { created: false };
    let failure: string | null = null;
    try {
      await this.ctx.blockConcurrencyWhile(async () => {
        const stored = await this.ctx.storage.get<unknown>(["lease", "waiting", "seq"]);
        const lease = stored.get("lease") as Lease | undefined;
        const waiting = (stored.get("waiting") as WaitingRef[] | undefined) ?? [];
        if (lease?.jobId === jobId || waiting.some((entry) => entry.jobId === jobId)) {
          result = { conflict: true };
          return;
        }
        // The platform's create() does not reliably reject an existing id
        // locally, so the write-once index is the duplicate check: every id
        // ever enqueued lands there before the create runs.
        if ((await jobIndexStub(this.env).domainOf(jobId)) != null) {
          result = { conflict: true };
          return;
        }
        if (lease == null) {
          // The instance is created before the lease is persisted, both inside
          // this single-threaded window, so a create that throws leaves no
          // lease behind for the alarm to sweep.
          try {
            await this.env.EXTRACTION.create({ id: jobId, params });
          } catch (error) {
            failure = describeError(error);
            return;
          }
          await this.ctx.storage.put("lease", { jobId });
          await this.ctx.storage.setAlarm(Date.now() + this.env.leaseAlarmMs);
          result = { created: true };
        } else {
          const seq = ((stored.get("seq") as number | undefined) ?? 0) + 1;
          const key = waitingKey(seq);
          waiting.push({ jobId, key });
          await this.ctx.storage.put({ [key]: params, seq, waiting });
        }
        // The index entry is awaited before the enqueue replies: an id that
        // has no instance yet stays reachable for the read path.
        await jobIndexStub(this.env).recordEntry(jobId, params.domain);
      });
    } catch (error) {
      failure = describeError(error);
    }
    // Captured inside the critical section (a throw out of it would reset the
    // object), rethrown outside it so the caller sees one failure channel.
    if (failure != null) {
      throw new Error(`creating the workflow failed: ${failure}`);
    }
    return result;
  }

  async release(jobId: string): Promise<void> {
    await this.ctx.blockConcurrencyWhile(async () => {
      const lease = await this.ctx.storage.get<Lease>("lease");
      if (lease?.jobId !== jobId) {
        return;
      }
      await this.ctx.storage.delete("lease");
      await this.advance();
    });
  }

  async stateOf(jobId: string): Promise<"queued" | "running" | "unknown"> {
    const stored = await this.ctx.storage.get<unknown>(["lease", "waiting"]);
    const lease = stored.get("lease") as Lease | undefined;
    if (lease?.jobId === jobId) {
      return "running";
    }
    const waiting = (stored.get("waiting") as WaitingRef[] | undefined) ?? [];
    if (waiting.some((entry) => entry.jobId === jobId)) {
      return "queued";
    }
    return "unknown";
  }

  private async advance(): Promise<void> {
    const waiting = (await this.ctx.storage.get<WaitingRef[]>("waiting")) ?? [];
    while (waiting.length > 0) {
      const next = waiting.shift() as WaitingRef;
      const params = await this.ctx.storage.get<ExtractionParams>(next.key);
      if (params == null) {
        continue;
      }
      try {
        await this.env.EXTRACTION.create({ id: next.jobId, params });
      } catch {
        // A waiting entry that cannot create must not wedge the queue behind
        // it: drop it and try the next, exactly as a sweep would.
        continue;
      }
      await this.ctx.storage.delete(next.key);
      await this.ctx.storage.put({ waiting, lease: { jobId: next.jobId } });
      await this.ctx.storage.setAlarm(Date.now() + this.env.leaseAlarmMs);
      return;
    }
    await this.ctx.storage.put("waiting", waiting);
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
