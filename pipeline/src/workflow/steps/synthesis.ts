import { NonRetryableError } from "cloudflare:workflows";
import { audioKey, encodeJson, presign, STEP } from "@nagara/common";
import { type SynthesisResult, startSynthesis, synthesisResult } from "../../tts/modal.ts";
import { ledgerInsert } from "../ledger.ts";
import { requireItem } from "../require-item.ts";
import { runStep, type StepContext } from "../wrapper.ts";

// The URL is signed for R2_S3_ENDPOINT and Modal is handed R2_UPLOAD_ENDPOINT in its place: the
// same endpoint in production, and locally the tunnel whose proxy forwards to the local bucket.
const uploadUrl = async (env: Cloudflare.Env, itemId: string) => {
  const endpoint = env.R2_S3_ENDPOINT.replace(/\/$/, "");
  const signed = await presign({
    endpoint,
    bucket: env.R2_BUCKET,
    key: audioKey(itemId),
    method: "PUT",
    accessKeyId: env.R2_PUT_ACCESS_KEY_ID,
    secretAccessKey: env.R2_PUT_SECRET_ACCESS_KEY,
    expiresIn: 3600,
  });

  return env.R2_UPLOAD_ENDPOINT.replace(/\/$/, "") + signed.slice(endpoint.length);
};

// Modal takes no idempotency key, so an attempt that runs again synthesizes again; both uploads
// land on the item's one audio key.
export const startSynthesisStep = (ctx: StepContext) =>
  runStep(ctx, STEP.startSynthesis, "generating", "2 minutes", async () => {
    const { env, itemId } = ctx;
    const item = await requireItem(env.DB, itemId);
    const callId = await startSynthesis(env, {
      paragraphs: (item.units ?? []).map((unit) => unit.spoken),
      voice: item.voice,
      destination: await uploadUrl(env, itemId),
    });

    return { callId };
  });

// One step asking until the result is ready, so current_step keeps one name and a retry asks again
// instead of starting a second synthesis.
export const waitForSynthesisStep = (ctx: StepContext, callId: string) =>
  runStep(ctx, STEP.waitForSynthesis, "generating", "15 minutes", async () => {
    for (;;) {
      const result = await synthesisResult(ctx.env, callId);

      if (result.ready) {
        return result;
      }

      await new Promise((resolve) => setTimeout(resolve, ctx.env.pollIntervalSeconds * 1000));
    }
  });

// Display, spoken and timing ride on one unit, so a window count that differs from the unit count
// is a broken item rather than something to align by text. The item turns ready in the same write
// that makes it readable.
export const storeStep = (ctx: StepContext, result: SynthesisResult) =>
  runStep(ctx, STEP.store, "generating", "1 minute", async () => {
    const { env, itemId } = ctx;
    const units = (await requireItem(env.DB, itemId)).units ?? [];

    if (result.timings.length !== units.length) {
      throw new NonRetryableError(
        `the synthesis returned ${result.timings.length} timing windows for ${units.length} units`,
      );
    }

    await env.DB.batch([
      env.DB.prepare(
        `UPDATE items SET status = 'ready', current_step = NULL, error = NULL, units = ?, duration = ?,
         audio_format = ?, updated_at = ? WHERE id = ?`,
      ).bind(
        encodeJson(units.map((unit, index) => ({ ...unit, ...result.timings[index] }))),
        result.duration,
        result.format,
        new Date().toISOString(),
        itemId,
      ),
      ledgerInsert(env.DB, {
        item_id: itemId,
        type: "tts",
        quantity: result.duration,
        unit: "seconds",
        dollars: result.duration * env.ttsDollarsPerSecond,
        detail: { duration: result.duration },
      }),
    ]);
  });
