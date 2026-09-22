import type { Model, Provider } from "@earendil-works/pi-ai";
import { createProvider } from "@earendil-works/pi-ai";
import { anthropicMessagesApi } from "@earendil-works/pi-ai/api/anthropic-messages.lazy";
import { openAICompletionsApi } from "@earendil-works/pi-ai/api/openai-completions.lazy";
import { openAIResponsesApi } from "@earendil-works/pi-ai/api/openai-responses.lazy";
import { CLOUDFLARE_AI_GATEWAY_MODELS } from "@earendil-works/pi-ai/providers/cloudflare-ai-gateway.models";
import { cloudflareAIGatewayAuth } from "@earendil-works/pi-ai/providers/cloudflare-auth";
import { cloudflareStreams } from "@earendil-works/pi-ai/providers/cloudflare-stream";

export const GLM_5_3_FLASH_ID = "workers-ai/@cf/zai-org/glm-5.3-flash";

// The shipped entry is right about everything except the two bounds the endpoint
// actually enforces and the reasoning knob it actually honours.
function withMeasuredMetadata(model: Model<"openai-completions">): Model<"openai-completions"> {
  return {
    ...model,
    // The catalog carries the window the model's docs page advertises, 1,310,720, but
    // the endpoint rejects anything past 1,048,576 for input and completion combined.
    contextWindow: 1_048_576,
    // The catalog sets this to the advertised completion cap, which only works for the
    // small-window entries. pi-ai sizes each request as min(maxTokens, contextWindow -
    // prompt - 4096), so a million-token budget has the model answering for minutes.
    maxTokens: 131_072,
    // Thinking cannot be switched off on this route and defaults to maximum effort, so
    // a turn costs minutes and thousands of tokens. `reasoning_effort` is the one lever
    // the endpoint honours, and pi-ai sends `off`'s mapping when an agent asks for no
    // particular level: mapping it to "low" is what makes the default turn cheap. The
    // higher levels map to their own names so tuning stays a change to this table.
    thinkingLevelMap: {
      off: "low",
      low: "low",
      medium: "medium",
      high: "high",
      xhigh: "xhigh",
      max: "max",
    },
    // The catalog marks the whole gateway as not supporting the parameter, which is
    // what keeps pi-ai from sending it; this route does support it.
    compat: { ...model.compat, supportsReasoningEffort: true },
  };
}

export function agentModelProvider(): Provider {
  const models = Object.values(CLOUDFLARE_AI_GATEWAY_MODELS).map((model) =>
    model.id === GLM_5_3_FLASH_ID ? withMeasuredMetadata(model) : model,
  );

  return createProvider({
    id: "cloudflare-ai-gateway",
    name: "Cloudflare AI Gateway",
    auth: { apiKey: cloudflareAIGatewayAuth() },
    models,
    api: {
      "anthropic-messages": cloudflareStreams(anthropicMessagesApi()),
      "openai-completions": cloudflareStreams(openAICompletionsApi()),
      "openai-responses": cloudflareStreams(openAIResponsesApi()),
    },
  });
}
