import type { CheerioAPI } from "cheerio/slim";
import type { AnyNode, Element } from "domhandler";

// A path segment carries the element's position among all of its parent's
// element children: per-tag indices cannot express document order across
// different tags at the same position, and the validator's checks are all
// about order and containment.
export interface PathSegment {
  tag: string;
  position: number;
}

export type ElementPath = PathSegment[];

export function pathOf(element: Element): ElementPath {
  const path: ElementPath = [];
  let current: AnyNode = element;
  while (current != null && current.type === "tag") {
    const tag = current.name;
    let position = 0;
    let sibling = current.prev;
    while (sibling != null) {
      if (sibling.type === "tag") {
        position += 1;
      }
      sibling = sibling.prev;
    }
    path.unshift({ tag, position });
    current = current.parent as AnyNode;
  }
  return path;
}

export function resolvePath($: CheerioAPI, path: ElementPath): Element | null {
  if (path.length === 0 || path[0].tag !== "html") {
    return null;
  }
  const root = $.root().get(0);
  const html = root?.children.find(
    (child): child is Element => child.type === "tag" && child.name === "html",
  );
  if (html == null) {
    return null;
  }
  let node: Element = html;
  for (let i = 1; i < path.length; i += 1) {
    const segment = path[i];
    const child = childAtPosition(node, segment.position);
    if (child == null || child.name !== segment.tag) {
      return null;
    }
    node = child;
  }
  return node;
}

function childAtPosition(node: Element, position: number): Element | null {
  let seen = 0;
  for (const child of node.children) {
    if (child.type === "tag") {
      if (seen === position) {
        return child;
      }
      seen += 1;
    }
  }
  return null;
}

export function isPathInside(path: ElementPath, ancestor: ElementPath): boolean {
  if (path.length <= ancestor.length) {
    return false;
  }
  for (let i = 0; i < ancestor.length; i += 1) {
    if (path[i].tag !== ancestor[i].tag || path[i].position !== ancestor[i].position) {
      return false;
    }
  }
  return true;
}

export function comparePaths(a: ElementPath, b: ElementPath): number {
  const depth = Math.min(a.length, b.length);
  for (let i = 0; i < depth; i += 1) {
    if (a[i].position !== b[i].position) {
      return a[i].position < b[i].position ? -1 : 1;
    }
  }
  return a.length - b.length;
}
