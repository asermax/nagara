import { DurableObject } from "cloudflare:workers";

// Write-once job id to domain map. Nothing deletes on the read or create
// path; only the alarm sweeps, past the configured cutoff.
export class JobIndex extends DurableObject<Cloudflare.Env> {
  async fetch(request: Request): Promise<Response> {
    this.ctx.storage.sql.exec(
      "CREATE TABLE IF NOT EXISTS jobs (job_id TEXT PRIMARY KEY, domain TEXT NOT NULL, created_at INTEGER NOT NULL)",
    );
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/entries") {
      const body = (await request.json()) as { job_id: string; domain: string };
      this.ctx.storage.sql.exec(
        "INSERT OR IGNORE INTO jobs (job_id, domain, created_at) VALUES (?, ?, ?)",
        body.job_id,
        body.domain,
        Date.now(),
      );
      if ((await this.ctx.storage.getAlarm()) == null) {
        await this.ctx.storage.setAlarm(Date.now() + this.env.indexSweepMs);
      }
      return Response.json({ ok: true });
    }
    if (request.method === "GET" && url.pathname.startsWith("/entries/")) {
      const jobId = decodeURIComponent(url.pathname.slice("/entries/".length));
      const cursor = this.ctx.storage.sql.exec("SELECT domain FROM jobs WHERE job_id = ?", jobId);
      for (const row of cursor) {
        return Response.json({ domain: row.domain });
      }
      return Response.json({ error: "no such job id" }, { status: 404 });
    }
    return new Response("not found", { status: 404 });
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
