import type { ItemWorkflowParams } from "@nagara/common";

type Calls = {
  create: WorkflowInstanceCreateOptions<ItemWorkflowParams>[];
  get: string[];
  restart: { instanceId: string; options: WorkflowInstanceRestartOptions | undefined }[];
};

type Options = {
  createError?: Error;
  existingIds?: string[];
  getError?: Error;
  restartError?: Error;
  statuses?: Record<string, InstanceStatus["status"]>;
};

// Records what the API asks of the item Workflow; the real one lives in the pipeline Worker,
// which the API's tests never run.
export const workflowStandIn = ({
  createError,
  existingIds = [],
  getError,
  restartError,
  statuses = {},
}: Options = {}) => {
  const calls: Calls = { create: [], get: [], restart: [] };

  const instance = (id: string) =>
    ({
      id,
      restart: async (options?: WorkflowInstanceRestartOptions) => {
        calls.restart.push({ instanceId: id, options });

        if (restartError != null) {
          throw restartError;
        }
      },
      status: async () => ({ status: statuses[id] ?? "complete" }),
    }) as unknown as WorkflowInstance;

  const workflow = {
    create: async (options: WorkflowInstanceCreateOptions<ItemWorkflowParams>) => {
      calls.create.push(options);

      if (createError != null) {
        throw createError;
      }

      if (options.id != null && existingIds.includes(options.id)) {
        throw new Error(
          `(instance.already_exists) Workflow instance with id "${options.id}" already exists`,
        );
      }

      return instance(options.id ?? crypto.randomUUID());
    },
    get: async (id: string) => {
      calls.get.push(id);

      if (getError != null) {
        throw getError;
      }

      return instance(id);
    },
  } as unknown as Workflow<ItemWorkflowParams>;

  return { calls, workflow };
};
