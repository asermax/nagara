import { DurableObject } from "cloudflare:workers";

export const LEASE_GRANTED = "lease-granted";

const TERMINAL_INSTANCE_STATUSES = new Set(["complete", "errored", "terminated"]);

export const domainQueueStub = (env: Cloudflare.Env, domain: string) =>
  env.DOMAIN_QUEUE.get(env.DOMAIN_QUEUE.idFromName(domain));

// One instance per domain: a lease naming the item Workflow instance that may extract now, and a
// FIFO of the instance ids waiting for it. The instance waits for its grant on its own, through
// waitForEvent, so the queue never creates anything.
export class DomainQueue extends DurableObject<Cloudflare.Env> {
  private lease() {
    return this.ctx.storage.kv.get<string>("lease");
  }

  private waiting() {
    return this.ctx.storage.kv.get<string[]>("waiting") ?? [];
  }

  private grant(instanceId: string) {
    this.ctx.storage.kv.put("lease", instanceId);
    void this.ctx.storage.setAlarm(Date.now() + this.env.leaseAlarmMs);
  }

  // Synchronous storage and no await, so no other call interleaves between the read and the write.
  // A restart from the lease step asks again with the same id: the holder is granted again, and a
  // waiter keeps its place rather than going to the back.
  acquire(instanceId: string) {
    const lease = this.lease();

    if (lease === instanceId) {
      return { granted: true };
    }

    const waiting = this.waiting();

    if (lease == null && (waiting.length === 0 || waiting[0] === instanceId)) {
      this.ctx.storage.kv.put(
        "waiting",
        waiting.filter((waiter) => waiter !== instanceId),
      );
      this.grant(instanceId);

      return { granted: true };
    }

    if (!waiting.includes(instanceId)) {
      this.ctx.storage.kv.put("waiting", [...waiting, instanceId]);
    }

    return { granted: false };
  }

  async release(instanceId: string) {
    await this.ctx.blockConcurrencyWhile(async () => {
      const waiting = this.waiting();

      if (waiting.includes(instanceId)) {
        this.ctx.storage.kv.put(
          "waiting",
          waiting.filter((waiter) => waiter !== instanceId),
        );
      }

      if (this.lease() !== instanceId) {
        return;
      }

      this.ctx.storage.kv.delete("lease");
      await this.advance();
    });
  }

  // A waiter that ended, or whose instance cannot be reached, would hold the lease with nobody to
  // release it, so it is skipped on the way to the next one.
  private async advance() {
    const waiting = this.waiting();

    while (waiting.length > 0) {
      const next = waiting.shift() as string;

      this.ctx.storage.kv.put("waiting", waiting);

      try {
        const instance = await this.env.ITEM_WORKFLOW.get(next);
        const { status } = await instance.status();

        if (TERMINAL_INSTANCE_STATUSES.has(status)) {
          continue;
        }

        this.grant(next);
        await instance.sendEvent({ type: LEASE_GRANTED, payload: {} });

        return;
      } catch {
        this.ctx.storage.kv.delete("lease");
      }
    }

    await this.ctx.storage.deleteAlarm();
  }

  async alarm() {
    await this.ctx.blockConcurrencyWhile(async () => {
      const lease = this.lease();

      if (lease == null) {
        return;
      }

      let ended: boolean;

      try {
        const { status } = await (await this.env.ITEM_WORKFLOW.get(lease)).status();

        ended = TERMINAL_INSTANCE_STATUSES.has(status);
      } catch {
        ended = true;
      }

      if (!ended) {
        await this.ctx.storage.setAlarm(Date.now() + this.env.leaseAlarmMs);

        return;
      }

      this.ctx.storage.kv.delete("lease");
      await this.advance();
    });
  }
}
