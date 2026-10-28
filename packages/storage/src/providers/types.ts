import type { GetObjectUrlInput } from "../lib/schema";

export interface StorageProviderStrategy {
  getUploadUrl: (data: GetObjectUrlInput) => Promise<{ url: string }>;
  getSignedUrl: (data: GetObjectUrlInput) => Promise<{ url: string }>;
  getPublicUrl: (data: GetObjectUrlInput) => Promise<{ url: string }>;
  getDeleteUrl: (data: GetObjectUrlInput) => Promise<{ url: string }>;
}
