import { describe, expect, it } from "vitest";

import { buildFeed, chapters, isBookkeeping, msgKey, reasoning } from "./bifrost";
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

describe("chapters and reasoning", () => {
  const at = (min: number) => new Date(Date.UTC(2026, 9, 26, 10, min)).toISOString();
  const msgs = [
    { id: "1", from: "claude", kind: "chat", content: "first", ts: at(0) },
    { id: "2", from: "claude", kind: "chat", content: "same speaker", ts: at(1) },
    { id: "3", from: "deepseek", kind: "chat", content: "speaker change", ts: at(2) },
    { id: "4", from: "deepseek", kind: "chat", content: "after a gap", ts: at(20) },
    { id: "5", from: "claude", kind: "trace", content: "\u{1f4ad} weighing the pool size", ts: at(21) },
    { id: "6", from: "claude", kind: "trace", content: "🔧 Bash ls", ts: at(22) },
  ];
  it("starts a chapter on a speaker change or an 8-minute gap", () => {
    expect(chapters(buildFeed(msgs)).map((c) => c.text)).toEqual(["first", "speaker change", "after a gap"]);
  });
  it("keeps only 💭 traces, newest first, without the glyph", () => {
    expect(reasoning(msgs, "claude")).toEqual([{ text: "weighing the pool size", ts: at(21) }]);
    expect(reasoning(msgs, "deepseek")).toEqual([]);
  });
});
