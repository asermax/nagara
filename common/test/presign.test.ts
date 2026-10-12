import { describe, expect, it } from "vitest";
import { presign } from "../src/presign.ts";

const encoder = new TextEncoder();

const hex = (bytes: ArrayBuffer) =>
  [...new Uint8Array(bytes)].map((byte) => byte.toString(16).padStart(2, "0")).join("");

const hmac = async (key: ArrayBuffer | Uint8Array, data: string) =>
  crypto.subtle.sign(
    "HMAC",
    await crypto.subtle.importKey("raw", key, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]),
    encoder.encode(data),
  );

const encodeRfc3986 = (value: string) =>
  encodeURIComponent(value).replace(
    /[!'()*]/g,
    (char) => `%${char.charCodeAt(0).toString(16).toUpperCase()}`,
  );

// An independent SigV4 query-signature check, so the test does not trust aws4fetch to verify itself.
const expectedSignature = async (signed: URL, method: string, secretAccessKey: string) => {
  const query = [...signed.searchParams.entries()]
    .filter(([name]) => name !== "X-Amz-Signature")
    .map(([name, value]) => `${encodeRfc3986(name)}=${encodeRfc3986(value)}`)
    .sort()
    .join("&");
  const canonicalRequest = [
    method,
    signed.pathname,
    query,
    `host:${signed.host}\n`,
    "host",
    "UNSIGNED-PAYLOAD",
  ].join("\n");
  const amzDate = signed.searchParams.get("X-Amz-Date") ?? "";
  const scope = (signed.searchParams.get("X-Amz-Credential") ?? "").split("/").slice(1).join("/");
  const stringToSign = [
    "AWS4-HMAC-SHA256",
    amzDate,
    scope,
    hex(await crypto.subtle.digest("SHA-256", encoder.encode(canonicalRequest))),
  ].join("\n");

  const dateKey = await hmac(encoder.encode(`AWS4${secretAccessKey}`), amzDate.slice(0, 8));
  const signingKey = await hmac(await hmac(await hmac(dateKey, "auto"), "s3"), "aws4_request");

  return hex(await hmac(signingKey, stringToSign));
};

describe("presign", () => {
  it("signs a PUT for the local S3 endpoint and a GET for R2 with the same code", async () => {
    const put = new URL(
      await presign({
        endpoint: "http://localhost:5173/cdn-cgi/local/r2/s3",
        bucket: "nagara",
        key: "audio/itm_0a1b2c3d",
        method: "PUT",
        accessKeyId: "local-key",
        secretAccessKey: "local-secret",
        expiresIn: 3600,
      }),
    );

    expect(put.origin).toBe("http://localhost:5173");
    expect(put.pathname).toBe("/cdn-cgi/local/r2/s3/nagara/audio/itm_0a1b2c3d");
    expect(put.searchParams.get("X-Amz-Expires")).toBe("3600");
    expect(put.searchParams.get("X-Amz-Credential")).toMatch(
      /^local-key\/\d{8}\/auto\/s3\/aws4_request$/,
    );
    expect(put.searchParams.get("X-Amz-Signature")).toBe(
      await expectedSignature(put, "PUT", "local-secret"),
    );
    expect(put.searchParams.get("X-Amz-Signature")).not.toBe(
      await expectedSignature(put, "GET", "local-secret"),
    );

    const get = new URL(
      await presign({
        endpoint: "https://account.r2.cloudflarestorage.com",
        bucket: "nagara",
        key: "images/5f2b",
        method: "GET",
        accessKeyId: "r2-key",
        secretAccessKey: "r2-secret",
        expiresIn: 3600,
      }),
    );

    expect(get.pathname).toBe("/nagara/images/5f2b");
    expect(get.searchParams.get("X-Amz-Signature")).toBe(
      await expectedSignature(get, "GET", "r2-secret"),
    );
  });
});
