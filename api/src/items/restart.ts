import { type ItemRow, restartPoint } from "@nagara/common";

// The Workflow writes its own instance id in its first step, so a row without one means the
// instance never ran: creating it again is the only way to start the item.
export const restartItem = async (
  workflow: Cloudflare.Env["ITEM_WORKFLOW"],
  { id, workflow_instance_id, current_step }: ItemRow,
) => {
  if (workflow_instance_id == null) {
    await workflow.create({ params: { itemId: id } });

    return;
  }

  const from = restartPoint(current_step);
  const instance = await workflow.get(workflow_instance_id);

  await instance.restart(from == null ? undefined : { from: { name: from } });
};
