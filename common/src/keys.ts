export const R2_PREFIX = {
  audio: "audio/",
  images: "images/",
} as const;

export const audioKey = (itemId: string) => `${R2_PREFIX.audio}${itemId}`;

export const imageKey = (hash: string) => `${R2_PREFIX.images}${hash}`;
