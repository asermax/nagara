export const SVG_CONTENT_TYPE = "image/svg+xml";

export const isSvg = (bytes: Uint8Array) =>
  new TextDecoder().decode(bytes.slice(0, 500)).toLowerCase().includes("<svg");

// A client shows the SVG only through an <img>, where scripts never run, but the stored markup is
// also what the describer reads, so the scripts and event handlers go before it is stored.
export const stripScripts = (svg: string) =>
  new HTMLRewriter()
    .on("script", {
      element: (element) => {
        element.remove();
      },
    })
    .on("*", {
      element: (element) => {
        const handlers = [...element.attributes]
          .map(([name]) => name)
          .filter((name) => name.toLowerCase().startsWith("on"));

        for (const name of handlers) {
          element.removeAttribute(name);
        }
      },
    })
    .transform(new Response(svg))
    .text();
