export const mintId = (prefix: string, length: number) =>
  `${prefix}_${crypto.randomUUID().replaceAll("-", "").slice(0, length)}`;
