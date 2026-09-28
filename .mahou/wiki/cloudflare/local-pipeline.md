# Local pipeline

`pipeline/` runs locally with `pnpm dev`, and a job runs through it without the API: `POST /jobs` with `{html, job_id, domain, recipe?}` in the body, then `GET /jobs/<job_id>` until the state is `complete`, `not_article` or `error`. A job with no recipe runs the author agent; a job whose recipe fails validation runs the revision agent.

- The agents reach Workers AI through the real `nagara` AI Gateway on the real account, so a local job spends real usage and shows in the gateway's logs. Keep local jobs to what the check needs. Durable Object and Workflow state stays local, in `pipeline/.wrangler/`.
- The key goes in `pipeline/.dev.vars` as `CLOUDFLARE_API_KEY=<token>`. Git ignores the file, and the repository ships no example of it.
- The token is a Cloudflare API token with Workers AI Read and AI Gateway Run. The Wrangler login token does not work. The gateway answers 401, code 2009 "Unauthorized", even though the login token carries `ai (write)`.
- The user writes the key into `.dev.vars`, for example with `! $EDITOR pipeline/.dev.vars`. Auto mode stops an agent from copying a credential.
- Run this call from `pipeline/` to check the key before a run. `<account>` is the `CLOUDFLARE_ACCOUNT_ID` in `pipeline/wrangler.jsonc`:
  `curl -s -w "\nHTTP %{http_code}\n" -X POST https://gateway.ai.cloudflare.com/v1/<account>/nagara/workers-ai/v1/chat/completions -H "Authorization: Bearer $(cut -d= -f2- .dev.vars)" -H content-type:application/json -d '{"model":"@cf/zai-org/glm-5.3-flash","messages":[{"role":"user","content":"Say ok"}],"max_tokens":5}'`
- `pnpm dev` does not enforce the recipe CPU cap.
