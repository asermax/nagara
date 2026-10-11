import { NonRetryableError } from "cloudflare:workflows";
import { type CodeUnit, encodeJson, type ParagraphUnit, STEP } from "@nagara/common";
import { acquire } from "../../images/acquire.ts";
import type { DeclaredImage } from "../../spoken/typed-units.ts";
import { requireItem } from "../require-item.ts";
import { runStep, type StepContext } from "../wrapper.ts";

export const imagesStep = (ctx: StepContext, declaredImages: DeclaredImage[]) =>
  runStep(ctx, STEP.images, "generating", "5 minutes", async () => {
    const { env, itemId } = ctx;
    const item = await requireItem(env.DB, itemId);

    // The anchors index the recipe step's text units; a run of this step that wrote its own list
    // before failing left image units among them, so they are set aside before interleaving.
    const textUnits = (item.units ?? []).filter(
      (unit): unit is ParagraphUnit | CodeUnit => unit.type !== "image",
    );
    const { units, degradations } = await acquire(env, {
      textUnits,
      declaredImages,
      itemId,
      pageUrl: item.url,
    });

    if (units.length === 0) {
      throw new NonRetryableError("no surviving units");
    }

    await env.DB.prepare(
      "UPDATE items SET units = ?, degradations = ?, updated_at = ? WHERE id = ?",
    )
      .bind(
        encodeJson(units),
        encodeJson(degradations.length === 0 ? null : degradations),
        new Date().toISOString(),
        itemId,
      )
      .run();
  });
