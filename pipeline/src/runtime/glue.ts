// The main module of every recipe Dynamic Worker: a health probe that proves
// the isolate and the bundle loaded and reports whether the recipe module
// parses, and the extract call that runs the recipe. The recipe itself
// travels as the sibling "recipe.js" module, so the dynamic import stays
// non-literal and resolves inside the loaded worker.
export const RUNTIME_MODULE = `
import { execute } from "./injection.js";

const RECIPE_SPECIFIER = "./recipe.js";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/health") {
      try {
        await import(RECIPE_SPECIFIER);
        return Response.json({ ok: true });
      } catch (error) {
        return Response.json({ ok: false, recipeError: String(error) });
      }
    }
    if (url.pathname === "/extract") {
      const { html } = await request.json();
      const payload = await execute(import(RECIPE_SPECIFIER), html);
      return Response.json(payload);
    }
    return new Response("not found", { status: 404 });
  },
};
`;
