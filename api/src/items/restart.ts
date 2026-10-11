import { type ItemRow, restartPoint, type Step } from "@nagara/common";

type ItemWorkflow = Cloudflare.Env["ITEM_WORKFLOW"];

const restartFrom = async (workflow: ItemWorkflow, id: string, currentStep: Step | null) => {
  const from = restartPoint(currentStep);
  const instance = await workflow.get(id);

  await instance.restart(from == null ? undefined : { from: { name: from } });
};

// The instance id is the item id, and the Workflow writes it to the row in its first step. A row
// without it may still have an instance that has not run that step yet, so a create that finds
// the instance already there restarts it instead. Only `already_exists` is common to the local
// and deployed wording of that error.
export const restartItem = async (
  workflow: ItemWorkflow,
  { id, workflow_instance_id, current_step }: ItemRow,
) => {
  if (workflow_instance_id != null) {
    await restartFrom(workflow, id, current_step);

    return;
  }

  try {
    await workflow.create({ id, params: { itemId: id } });
  } catch (error) {
    if (!String(error).includes("already_exists")) {
      throw error;
    }

    await restartFrom(workflow, id, current_step);
  }
};
