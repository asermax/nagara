# Local pipeline

`pipeline/` runs locally under `pnpm dev` next to the API Worker, and an item reaches it only through the local API: `POST /items` on port 8788 with the key from `api/.dev.vars`, then `GET /items/<id>` until the status is `ready` or `failed`. `docs/technical-design/local-development.md` gives the launch order and explains the tunnel and the shared state folder. The first item of a domain runs the author agent; an item whose recipe fails validation runs the revision agent.

- The agents reach Workers AI through the real `nagara` AI Gateway on the real account, so a local item spends real usage and shows in the gateway's logs. Keep local items to what the check needs. D1, R2, Durable Object and Workflow state stays local, in the shared `.wrangler-state/` at the repository root.
- The key goes in `pipeline/.dev.vars` as `CLOUDFLARE_API_KEY=<token>`, next to the other secrets `pipeline/.dev.vars.example` names. Git ignores `.dev.vars`.
- The token is a Cloudflare API token with Workers AI Read and AI Gateway Run. The Wrangler login token does not work. The gateway answers 401, code 2009 "Unauthorized", even though the login token carries `ai (write)`.
- The user writes the key into `.dev.vars`, for example with `! $EDITOR pipeline/.dev.vars`. Auto mode stops an agent from copying a credential.
- Run this call from `pipeline/` to check the key before a run. `<account>` is the `CLOUDFLARE_ACCOUNT_ID` in `pipeline/wrangler.jsonc`:
  `curl -s -w "\nHTTP %{http_code}\n" -X POST https://gateway.ai.cloudflare.com/v1/<account>/nagara/workers-ai/v1/chat/completions -H "Authorization: Bearer $(grep '^CLOUDFLARE_API_KEY=' .dev.vars | cut -d= -f2-)" -H content-type:application/json -d '{"model":"@cf/zai-org/glm-5.3-flash","messages":[{"role":"user","content":"Say ok"}],"max_tokens":5}'`
- `pnpm dev` does not enforce the recipe CPU cap.
