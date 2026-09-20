import { reset, runDurableObjectAlarm, runInDurableObject } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { afterEach, describe, expect, it } from "vitest";

function index() {
  return env.JOB_INDEX.get(env.JOB_INDEX.idFromName("nagara-job-index"));
}

afterEach(async () => {
  await reset();
});

describe("job index", () => {
  it("A18: answers the domain for a job id written at enqueue", async () => {
    const write = await index().fetch("https://index/entries", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ job_id: "itm_a18", domain: "a18.example.com" }),
    });
    expect(write.status).toBe(200);

    const read = await index().fetch("https://index/entries/itm_a18");
    expect(read.status).toBe(200);
    expect(await read.json()).toEqual({ domain: "a18.example.com" });
  });

  it("A19: the alarm sweeps entries past the cutoff, keeps younger ones, and reads and creates never delete", async () => {
    for (const jobId of ["itm_a19-old", "itm_a19-young"]) {
      await index().fetch("https://index/entries", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ job_id: jobId, domain: "a19.example.com" }),
      });
    }
    await runInDurableObject(index(), (_instance, state) => {
      state.storage.sql.exec(
        "UPDATE jobs SET created_at = ? WHERE job_id = ?",
        Date.now() - 86400000 - 60000,
        "itm_a19-old",
      );
    });

    const read = await index().fetch("https://index/entries/itm_a19-old");
    expect(read.status).toBe(200);

    const rewrite = await index().fetch("https://index/entries", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ job_id: "itm_a19-old", domain: "rewritten.example.com" }),
    });
    expect(rewrite.status).toBe(200);

    expect(await runDurableObjectAlarm(index())).toBe(true);

    const swept = await index().fetch("https://index/entries/itm_a19-old");
    expect(swept.status).toBe(404);
    const kept = await index().fetch("https://index/entries/itm_a19-young");
    expect(kept.status).toBe(200);
    expect(await kept.json()).toEqual({ domain: "a19.example.com" });
  });
});
