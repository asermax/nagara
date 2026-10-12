declare namespace Cloudflare {
  interface Env {
    DB: D1Database;
    TEST_MIGRATIONS: import("cloudflare:test").D1Migration[];
  }
}

declare module "*.yaml?raw" {
  const text: string;
  export default text;
}
