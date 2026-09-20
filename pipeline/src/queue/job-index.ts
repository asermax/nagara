import { DurableObject } from "cloudflare:workers";

export const JOB_INDEX_NAME = "nagara-job-index";

export function jobIndexStub(env: Cloudflare.Env) {
  return env.JOB_INDEX.get(env.JOB_INDEX.idFromName(JOB_INDEX_NAME));
}

// Write-once job id to domain map. Nothing deletes on the read or create
// path; only the alarm sweeps, past the configured cutoff.
export class JobIndex extends DurableObject<Cloudflare.Env> {
  constructor(ctx: DurableObjectState, env: Cloudflare.Env) {
    super(ctx, env);
    this.ctx.storage.sql.exec(
      "CREATE TABLE IF NOT EXISTS jobs (job_id TEXT PRIMARY KEY, domain TEXT NOT NULL, created_at INTEGER NOT NULL)",
    );
  }

  async recordEntry(jobId: string, domain: string): Promise<void> {
    this.ctx.storage.sql.exec(
      "INSERT OR IGNORE INTO jobs (job_id, domain, created_at) VALUES (?, ?, ?)",
      jobId,
      domain,
      Date.now(),
    );
    if ((await this.ctx.storage.getAlarm()) == null) {
      await this.ctx.storage.setAlarm(Date.now() + this.env.indexSweepMs);
    }
  }

  async domainOf(jobId: string): Promise<string | null> {
    const cursor = this.ctx.storage.sql.exec<{ domain: string }>(
      "SELECT domain FROM jobs WHERE job_id = ?",
      jobId,
    );
    for (const row of cursor) {
      return row.domain;
    }
    return null;
  }

  async alarm(): Promise<void> {
    const cutoff = Date.now() - this.env.indexSweepMs;
    this.ctx.storage.sql.exec("DELETE FROM jobs WHERE created_at < ?", cutoff);
    const cursor = this.ctx.storage.sql.exec("SELECT COUNT(*) AS remaining FROM jobs");
    let remaining = 0;
    for (const row of cursor) {
      remaining = row.remaining as number;
    }
    if (remaining > 0) {
      await this.ctx.storage.setAlarm(Date.now() + this.env.indexSweepMs);
    } else {
      await this.ctx.storage.deleteAlarm();
    }
  }
}
