import { S3Client } from "@aws-sdk/client-s3";

import { env } from "../../env";

let s3Client: S3Client | null = null;

export const getClient = () => {
  if (s3Client) {
    return s3Client;
  }

  s3Client = new S3Client({
    forcePathStyle: true,
    region: env.S3_REGION,
    endpoint: env.S3_ENDPOINT,
    credentials: {
      accessKeyId: env.S3_ACCESS_KEY_ID,
      secretAccessKey: env.S3_SECRET_ACCESS_KEY,
    },
  });

  return s3Client;
};
