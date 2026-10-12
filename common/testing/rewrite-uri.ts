export const rewriteUri = (uri: string, rewrites: Record<string, string>) => {
  const prefix = Object.keys(rewrites).find((candidate) => uri.startsWith(candidate));

  return prefix == null ? uri : `${rewrites[prefix]}${uri.slice(prefix.length)}`;
};
