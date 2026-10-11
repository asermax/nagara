import { presign } from "@nagara/common";

const SIGNED_URL_SECONDS = 3600;

export const signedRedirect = async (env: Cloudflare.Env, key: string) =>
  Response.redirect(
    await presign({
      endpoint: env.R2_S3_ENDPOINT,
      bucket: env.R2_BUCKET,
      key,
      method: "GET",
      accessKeyId: env.R2_GET_ACCESS_KEY_ID,
      secretAccessKey: env.R2_GET_SECRET_ACCESS_KEY,
      expiresIn: SIGNED_URL_SECONDS,
    }),
    307,
  );
