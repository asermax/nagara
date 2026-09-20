// @mixmark-io/domino ships ambient `declare module "domino"` typings aimed at
// the original package name, so importing the fork by its scoped name types as
// "not a module". The fixed conversion pass uses this small surface.
declare module "@mixmark-io/domino" {
  export function createDocument(html?: string): Document;
  export const impl: {
    Node: unknown;
    Element: unknown;
  };
}
