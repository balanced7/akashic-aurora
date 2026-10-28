import {
  DeleteObjectCommand,
  GetObjectCommand,
  PutObjectCommand,
} from "@aws-sdk/client-s3";
import { getSignedUrl as getSignedUrlCommand } from "@aws-sdk/s3-request-presigner";

import { getClient } from "./client";

import type { StorageProviderStrategy } from "../types";

const getUploadUrl: StorageProviderStrategy["getUploadUrl"] = async ({
  path,
  bucket,
}) => {
  const client = getClient();

  const url = await getSignedUrlCommand(
    client,
    new PutObjectCommand({
      Bucket: bucket,
      Key: path,
    }),
    {
      expiresIn: 60,
    },
  );

  return { url };
};

const getSignedUrl: StorageProviderStrategy["getSignedUrl"] = async ({
  path,
  bucket,
}) => {
  const client = getClient();

  const url = await getSignedUrlCommand(
    client,
    new GetObjectCommand({
      Bucket: bucket,
      Key: path,
    }),
    {
      expiresIn: 3600,
    },
  );

  return { url };
};

const getPublicUrl: StorageProviderStrategy["getPublicUrl"] = async ({
  path,
  bucket,
}) => {
  const client = getClient();
  const endpoint = await client.config.endpoint?.();

  if (endpoint?.hostname.includes("supabase.co")) {
    return {
      url: `${endpoint.protocol}//${endpoint.hostname}/storage/v1/object/public/${bucket}/${path}`,
    };
  }

  return {
    url: `${endpoint?.protocol}//${bucket}.${endpoint?.hostname}/${path}`,
  };
};

const getDeleteUrl: StorageProviderStrategy["getDeleteUrl"] = async ({
  path,
  bucket,
}) => {
  const client = getClient();

  const url = await getSignedUrlCommand(
    client,
    new DeleteObjectCommand({
      Bucket: bucket,
      Key: path,
    }),
    {
      expiresIn: 60,
    },
  );

  return { url };
};

export { getUploadUrl, getSignedUrl, getPublicUrl, getDeleteUrl };
