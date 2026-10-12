// The recipe key: the host of the fetch's final URL with only a leading www dropped, so subdomains
// stay distinct domains and consolidation comes from redirects alone.
export const domainFromUrl = (url: string) => new URL(url).hostname.replace(/^www\./, "");
