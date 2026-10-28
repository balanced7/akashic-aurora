import { describe, expect, it } from "vitest";

import { createIdGenerator, generateId } from "../id";

describe("generateId", () => {
  it("should generate a string of length 32 by default", () => {
    const id = generateId();
    expect(typeof id).toBe("string");
    expect(id.length).toBe(32);
  });

  it("should generate unique ids", () => {
    const id1 = generateId();
    const id2 = generateId();
    expect(id1).not.toBe(id2);
  });

  it("should only contain allowed characters (alphanumeric)", () => {
    const id = generateId();
    expect(id).toMatch(/^[0-9a-zA-Z]+$/);
  });
});

describe("createIdGenerator", () => {
  it("should allow custom size", () => {
    const generateShortId = createIdGenerator({ size: 10 });
    const id = generateShortId();
    expect(id.length).toBe(10);
  });

  it("should allow custom alphabet", () => {
    const generateBinaryId = createIdGenerator({ alphabet: "01" });
    const id = generateBinaryId();
    expect(id).toMatch(/^[01]+$/);
  });

  it("should allow custom alphabet with special characters", () => {
    const specialChars = "!@#$%^&*";
    const generateSpecialId = createIdGenerator({ alphabet: specialChars });
    const id = generateSpecialId();
    for (const char of id) {
      expect(specialChars).toContain(char);
    }
  });

  it("should allow prefix", () => {
    const generatePrefixedId = createIdGenerator({ prefix: "user" });
    const id = generatePrefixedId();
    expect(id.startsWith("user-")).toBe(true);
    expect(id.length).toBe(32 + 5); // 32 random + 4 prefix + 1 separator
  });

  it("should allow custom separator", () => {
    const generateUnderscoreId = createIdGenerator({
      prefix: "test",
      separator: "_",
    });
    const id = generateUnderscoreId();
    expect(id.startsWith("test_")).toBe(true);
  });

  it("should throw if separator is in alphabet", () => {
    expect(() =>
      createIdGenerator({
        prefix: "fail",
        separator: "a",
        alphabet: "abc",
      }),
    ).toThrow('The separator "a" must not be part of the alphabet "abc".');
  });

  it("should allow empty prefix", () => {
    // If prefix is provided as empty string, it works like a prefix
    const generateEmptyPrefixedId = createIdGenerator({ prefix: "" });
    // prefix="" -> `${""}-${generator()}` -> `-${generator()}`
    const id = generateEmptyPrefixedId();
    expect(id.startsWith("-")).toBe(true);
  });
});
