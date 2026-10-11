// Low-grade Kokoro voices stay out of the pool so an item enqueued without a voice always sounds
// good; any voice can still be asked for by name.
const VOICE_POOL = [
  "af_heart",
  "af_bella",
  "af_sarah",
  "af_sky",
  "af_aoede",
  "af_alloy",
  "af_nova",
  "am_fenrir",
  "am_michael",
  "am_puck",
];

export const pickVoice = (voice: string | undefined) =>
  voice ?? VOICE_POOL[Math.floor(Math.random() * VOICE_POOL.length)];
