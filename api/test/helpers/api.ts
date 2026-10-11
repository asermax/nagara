import { env } from "cloudflare:workers";
import worker from "../../src/index.ts";
import { workflowStandIn } from "./workflow-stand-in.ts";

type Call = {
  method?: string;
  body?: unknown;
  key?: string | null;
  workflow?: Cloudflare.Env["ITEM_WORKFLOW"];
};

export const callApi = (
  path: string,
  { method = "GET", body, key = env.API_KEY, workflow = workflowStandIn().workflow }: Call = {},
) =>
  worker.fetch(
    new Request(`https://nagara.test${path}`, {
      method,
      headers: key == null ? {} : { "X-API-Key": key },
      body: body == null ? undefined : JSON.stringify(body),
      redirect: "manual",
    }),
    { ...env, ITEM_WORKFLOW: workflow },
  );
