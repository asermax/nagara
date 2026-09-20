import { reset, runDurableObjectAlarm, runInDurableObject } from "cloudflare:test";
import { env } from "cloudflare:workers";
import { afterEach, describe, expect, it } from "vitest";
import { JOB_INDEX_NAME, type JobIndex } from "../src/queue/job-index.ts";

function index() {
  return env.JOB_INDEX.get(env.JOB_INDEX.idFromName(JOB_INDEX_NAME)) as DurableObjectStub<JobIndex>;
}

afterEach(async () => {
  await reset();
});

describe("job index", () => {
  it("answers the domain for a job id written at enqueue", async () => {
    await index().recordEntry("itm_a18", "a18.example.com");
    expect(await index().domainOf("itm_a18")).toBe("a18.example.com");
  });

  it("the alarm sweeps entries past the cutoff, keeps younger ones, and reads and creates never delete", async () => {
    await index().recordEntry("itm_a19-old", "a19.example.com");
    await index().recordEntry("itm_a19-young", "a19.example.com");
    await runInDurableObject(index(), (_instance, state) => {
      state.storage.sql.exec(
        "UPDATE jobs SET created_at = ? WHERE job_id = ?",
        Date.now() - 86400000 - 60000,
        "itm_a19-old",
      );
    });

    expect(await index().domainOf("itm_a19-old")).toBe("a19.example.com");
    await index().recordEntry("itm_a19-old", "rewritten.example.com");

    expect(await runDurableObjectAlarm(index())).toBe(true);

    expect(await index().domainOf("itm_a19-old")).toBeNull();
    expect(await index().domainOf("itm_a19-young")).toBe("a19.example.com");
  });
});
