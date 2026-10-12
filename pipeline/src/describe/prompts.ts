// Neither prompt repeats the response schema: Gemini's own docs warn that duplicating it, or JSON
// examples, in the prompt lowers output quality.

// "This" is forbidden outright: forbidding "This block" and "This example" alone left a residual
// "This is a…". The paragraph after the block is left out because it is the elaboration the
// listener is about to hear, and including it nudges the model toward describing behaviour.
export const codePrompt = (
  title: string | null,
  intro: string | null,
  code: string,
) => `You are describing a code block from a technical article for someone listening to the article who cannot see the code.

Write exactly ONE sentence that names what KIND of code the block is and what it is FOR.

Rules:
- Begin the sentence with the kind itself, for example "A Python function", "A shell command", "An HTTP request", or "The syntax for". Never begin with "This", "These", "The following", or any preamble, and never use the word "This" anywhere in the sentence.
- Name only the kind and the purpose. Do not describe what the code does, its mechanics, its return values, or the framework it uses, unless the introducing text below states them.
- Treat the introducing text as the authority for what the block is about. Do not invent details the introducing text and the block do not support.
- Do not read the code aloud, not even a one-line block.

Article title: ${title || "(untitled)"}

Introducing text: ${intro || "(none)"}

Code block:
${code}`;

// The alt rides in labelled unreliable, since most alt is empty, SEO filler or a subscribe prompt.
export const imagePrompt = (
  title: string | null,
  alt: string,
) => `You are describing an image from a technical article for someone listening to the article who cannot see it.

Write exactly ONE sentence naming what the image SHOWS.

Rules:
- Be specific, never categorical. Read a chart's axes and its trend, name a screenshot's on-screen elements and the action taken, describe a photo's subject and setting. Never write only "a chart", "a screenshot", or "a photo".
- Begin the sentence with the thing shown. Never begin with "This", "The image", "An image of", "A picture of", or any preamble, and never use the word "This" anywhere in the sentence.
- Describe only what is visibly there. Do not name any person, organization, company, brand, product, place, or region unless that exact name appears as written text inside the image.
- Do not state what the image means or its role in the article. One sentence of visible content, with no second sentence.

Article title: ${title || "(untitled)"}

The alt text below is often wrong, empty, or SEO filler; use it only where it matches what you see and ignore it otherwise.
Alt text: ${alt || "(none)"}`;
