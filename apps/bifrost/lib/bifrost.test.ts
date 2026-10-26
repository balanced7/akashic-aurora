import { describe, expect, it } from "vitest";

import { buildFeed, isBookkeeping, msgKey } from "./bifrost";
import { renderMarkdown } from "./markdown";

describe("feed", () => {
  it("keys dual-write twins identically despite different stream ids", () => {
    const m = { from: "claude", to: "user", kind: "chat", ts: "t", content: "hi" };
    expect(msgKey({ ...m, id: "1-0" })).toBe(msgKey({ ...m, id: "2-0" }));
  });

  it("folds a stretch of interleaved traces into one card per agent; a message ends it", () => {
    const feed = buildFeed([
      { from: "claude", kind: "trace", ts: "1", content: "Bash" },
      { from: "deepseek", kind: "trace", ts: "2", content: "Grep" },
      { from: "claude", kind: "trace", ts: "3", content: "Read" },
      { from: "claude", kind: "note", ts: "4", content: "done" },
      { from: "claude", kind: "trace", ts: "5", content: "Edit" },
      { from: "system", kind: "note", ts: "6", content: "bus up" },
    ]);
    expect(feed.map((f) => (f.type === "traces" ? `${f.agent}:${f.traces.length}` : f.type))).toEqual([
      "claude:2",
      "deepseek:1",
      "message",
      "claude:1",
      "system",
    ]);
  });

  it("filters a 1:1 thread to the peer and what was said to it", () => {
    const feed = buildFeed(
      [
        { from: "claude", to: "user", content: "a" },
        { from: "deepseek", to: "user", content: "b" },
        { from: "user", to: "claude", content: "c" },
        { from: "user", to: "deepseek", content: "d" },
      ],
      "claude",
    );
    expect(feed.map((f) => (f.type === "message" ? f.m.content : ""))).toEqual(["a", "c"]);
  });

  it("treats acks and triage receipts as bookkeeping", () => {
    expect(isBookkeeping({ kind: "msg_ack" })).toBe(true);
    expect(isBookkeeping({ kind: "chat", content: "[triage-receipt] x" })).toBe(true);
    expect(isBookkeeping({ kind: "chat", content: "hello" })).toBe(false);
  });
});

describe("markdown", () => {
  it("never passes raw HTML or script URLs through", () => {
    const html = renderMarkdown('<img src=x onerror=alert(1)> [x](javascript:alert(1)) [ok](https://a.b)');
    expect(html).not.toContain("<img");
    expect(html).not.toContain('href="javascript');
    expect(html).toContain('href="https://a.b"');
  });

  it("offers Run only on command-shaped code blocks", () => {
    expect(renderMarkdown("```\npytest -q\n```")).toContain('data-act="run"');
    expect(renderMarkdown("```\nrm -rf /\n```")).not.toContain('data-act="run"');
  });
});
