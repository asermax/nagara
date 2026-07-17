# Feature Designs

Design catalog — every durable feature design and the approach it takes.

| Feature | Approach | Status | Milestone |
|---------|----------|--------|-----------|
| [enqueue-to-audio-api](enqueue-to-audio-api.md) | Eager-generate on enqueue + async poll; zero-broker Modal synth; server-side extraction; config-selected audio storage (object storage in prod, local files in dev) | ✓ current | M1 — backend spine |
| [markdown-read-along-content](markdown-read-along-content.md) | Single markdown extraction → display[] + derived spoken[]; unchanged index-keyed TTS; join timeline onto display by index; display persisted across the async gap | ✓ current | M2 — markdown content |
