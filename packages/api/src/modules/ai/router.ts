import { openai } from "@ai-sdk/openai";
import { convertToModelMessages, streamText } from "ai";
import { Hono } from "hono";

export const aiRouter = new Hono().post("/chat", async (c) =>
  streamText({
    model: openai.responses("gpt-4.1-nano"),
    // eslint-disable-next-line @typescript-eslint/no-unsafe-argument, @typescript-eslint/no-unsafe-member-access
    messages: convertToModelMessages((await c.req.json()).messages),
  }).toUIMessageStreamResponse(),
);
