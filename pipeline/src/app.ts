import { setProvider } from "@flue/runtime";
import { agentModelProvider } from "./agents/model-provider.ts";

// Module scope: the generated Worker entry registers pi-ai's built-ins after
// the app module evaluates and skips ids already taken, so this replaces the
// shipped cloudflare-ai-gateway provider before any agent renders.
setProvider(agentModelProvider());

export { default } from "./http/routes.ts";
