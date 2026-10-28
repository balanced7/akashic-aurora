export interface EmailProviderStrategy {
  send: (args: {
    to: string;
    subject: string;
    text: string;
    html?: string;
  }) => Promise<void>;
}
