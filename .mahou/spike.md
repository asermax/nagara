# Spike

- Any audio a spike plays in a browser plays muted (the element's `muted`, or Chromium's `--mute-audio`). Close the browser session when the spike is done with it.
- Every Cloudflare or Modal resource a spike creates is named with the prefix `nagara-spike-`. A spike never changes the production `nagara` and `nagara-api` Workers, the `nagara` Worker's Workflows and Durable Objects, the `nagara` AI Gateway's settings or the `nagara-tts` Modal app. The spike deletes every resource it created before it finishes, and lists those resources in its findings.
