// @mixmark-io/domino ships ambient `declare module "domino"` typings aimed at
// the original package name, so importing the fork by its scoped name types as
// "not a module". The fixed conversion pass uses this small surface, and the
// worker's lib carries no DOM types to borrow it from.
declare module "@mixmark-io/domino" {
  export interface DominoNode {
    nodeName: string;
    firstChild: DominoNode | null;
    appendChild(node: DominoNode): DominoNode;
  }

  export interface DominoElement extends DominoNode {
    querySelectorAll(selector: string): ArrayLike<DominoElement>;
  }

  export interface DominoDocument {
    body: DominoElement;
    createElement(tag: string): DominoElement;
  }

  export function createDocument(html?: string): DominoDocument;
  export const impl: {
    Node: unknown;
    Element: unknown;
  };
}
