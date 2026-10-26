import { describe, expect, it } from "vitest";

import type { Status } from "./bifrost";
import { elapsed, fleetPulse } from "./fleet";

const base = { paused: false, agents: [{ agent: "claude" }], known: ["claude", "user"], signals: {}, halted: {} } as unknown as Status;

describe("fleetPulse", () => {
  it("is amber before status is read, never green", () => {
    expect(fleetPulse(null).tone).toBe("amber");
  });
  it("is green when everyone known is online", () => {
    expect(fleetPulse(base)).toEqual({ tone: "green", reason: "all clear" });
  });
  it("names offline seats in amber and goes red on pause or an error", () => {
    expect(fleetPulse({ ...base, known: ["claude", "deepseek"] }).reason).toBe("offline: deepseek");
    expect(fleetPulse({ ...base, paused: true }).tone).toBe("red");
    expect(fleetPulse({ ...base, signals: { claude: { crashed: true } } } as unknown as Status).tone).toBe("red");
  });
});

describe("elapsed", () => {
  it("reads short and long spans", () => {
    const t = Date.parse("2026-10-26T12:00:00Z");
    expect(elapsed("2026-10-26T11:59:55Z", t)).toBe("just now");
    expect(elapsed("2026-10-26T11:58:00Z", t)).toBe("2.0m");
    expect(elapsed(undefined, t)).toBe("");
  });
});
