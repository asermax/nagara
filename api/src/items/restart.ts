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

// A restart of an instance that errored before its first step is accepted and does nothing, so
// such an instance is replaced by a new one under the item id's next free suffix. The new instance
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

const restartFrom = async (instance: WorkflowInstance, currentStep: ItemRow["current_step"]) => {
  const from = restartPoint(currentStep);

  await instance.restart(from == null ? undefined : { from: { name: from } });
};

// The row names an instance once the fetch step has run, and a restart from a later step reuses
// the earlier steps' results, so a named instance is restarted whatever its status.
const revive = async (
  workflow: ItemWorkflow,
  instanceId: string,
  { current_step }: ItemRow,
  { leaveLive }: Options,
) => {
  const instance = await workflow.get(instanceId);
  const { status } = await instance.status();

  if (leaveLive && LIVE_STATES.has(status)) {
    return;
  }

  await restartFrom(instance, current_step);
};

// Deployed, a create on a taken id throws `already_exists`; locally it hands back the instance
// already there, so the status of whatever comes back is read either way.
const createFirst = async (workflow: ItemWorkflow, itemId: string) => {
  try {
    return {
      instance: await workflow.create({ id: itemId, params: { itemId } }),
      existed: false,
    };
  } catch (error) {
    if (!alreadyExists(error)) {
      throw error;
    }

    return { instance: await workflow.get(itemId), existed: true };
  }
};

// The first instance's id is the item id, and the Workflow writes its id to the row in its first
// step. A row without it may still have an instance that has not run that step yet: an ended one
// is replaced, and one the create found already there is revived like a named instance.
export const restartItem = async (workflow: ItemWorkflow, row: ItemRow, options: Options) => {
  if (row.workflow_instance_id != null) {
    await revive(workflow, row.workflow_instance_id, row, options);

    return;
  }

  const { instance, existed } = await createFirst(workflow, row.id);
  const { status } = await instance.status();

  if (ENDED_STATES.has(status)) {
    await replace(workflow, row.id);

    return;
  }

  if (!existed || (options.leaveLive && LIVE_STATES.has(status))) {
    return;
  }

  await restartFrom(instance, row.current_step);
};
