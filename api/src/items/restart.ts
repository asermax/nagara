import { type ItemRow, restartPoint } from "@nagara/common";

type ItemWorkflow = Cloudflare.Env["ITEM_WORKFLOW"];

type InstanceState = InstanceStatus["status"];

type Options = {
  leaveLive: boolean;
};

const LIVE_STATES: ReadonlySet<InstanceState> = new Set(["queued", "running", "waiting", "paused"]);

const ENDED_STATES: ReadonlySet<InstanceState> = new Set(["errored", "terminated"]);

// Only `already_exists` is common to the local and deployed wording of the error.
const alreadyExists = (error: unknown) => String(error).includes("already_exists");

// A restart of an instance that errored before its first step is accepted and does nothing, so an
// ended instance is replaced by a new one under the item id's next free suffix. The new instance
// writes its id to the row in its first step, as the first one did.
const replace = async (workflow: ItemWorkflow, itemId: string) => {
  for (let suffix = 2; ; suffix++) {
    try {
      await workflow.create({ id: `${itemId}-${suffix}`, params: { itemId } });

      return;
    } catch (error) {
      if (!alreadyExists(error)) {
        throw error;
      }
    }
  }
};

const revive = async (
  workflow: ItemWorkflow,
  instanceId: string,
  { id, current_step }: ItemRow,
  { leaveLive }: Options,
) => {
  const instance = await workflow.get(instanceId);
  const { status } = await instance.status();

  if (ENDED_STATES.has(status)) {
    await replace(workflow, id);

    return;
  }

  if (leaveLive && LIVE_STATES.has(status)) {
    return;
  }

  const from = restartPoint(current_step);

  await instance.restart(from == null ? undefined : { from: { name: from } });
};

// The first instance's id is the item id, and the Workflow writes its id to the row in its first
// step. A row without it may still have an instance that has not run that step yet, so a create
// that finds the instance already there revives that instance instead.
export const restartItem = async (workflow: ItemWorkflow, row: ItemRow, options: Options) => {
  if (row.workflow_instance_id != null) {
    await revive(workflow, row.workflow_instance_id, row, options);

    return;
  }

  try {
    await workflow.create({ id: row.id, params: { itemId: row.id } });
  } catch (error) {
    if (!alreadyExists(error)) {
      throw error;
    }

    await revive(workflow, row.id, row, options);
  }
};
