import { WorkflowEntrypoint } from "cloudflare:workers";

export class ItemWorkflow extends WorkflowEntrypoint {
  async run() {}
}

export default {
  fetch: () => new Response(null, { status: 404 }),
};
