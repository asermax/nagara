import { AwsClient } from "aws4fetch";

export type PresignRequest = {
  endpoint: string;
  bucket: string;
  key: string;
  method: "GET" | "PUT";
  accessKeyId: string;
  secretAccessKey: string;
  expiresIn: number;
};

export const presign = async ({
  endpoint,
  bucket,
  key,
  method,
  accessKeyId,
  secretAccessKey,
  expiresIn,
}: PresignRequest) => {
  const client = new AwsClient({ accessKeyId, secretAccessKey, service: "s3", region: "auto" });
  const url = new URL(`${endpoint.replace(/\/$/, "")}/${bucket}/${key}`);

  url.searchParams.set("X-Amz-Expires", String(expiresIn));

  return (await client.sign(new Request(url, { method }), { aws: { signQuery: true } })).url;
};
