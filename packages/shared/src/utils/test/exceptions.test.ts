import { describe, expect, it } from "vitest";

import { HttpStatusCode } from "../../constants";
import { HttpException, getStatusCode, isHttpStatus } from "../exceptions";

describe("isHttpStatus", () => {
  it.each([
    [200, true],
    [404, true],
    [500, true],
    [999, false],
    [1, false],
  ])("should return $expected for status $status", (status, expected) => {
    expect(isHttpStatus(status)).toBe(expected);
  });
});

describe("HttpException", () => {
  it("should create an instance with status and message", () => {
    const error = new HttpException(HttpStatusCode.BAD_REQUEST, {
      message: "Bad Request",
    });
    expect(error).toBeInstanceOf(Error);
    expect(error.status).toBe(HttpStatusCode.BAD_REQUEST);
    expect(error.message).toBe("Bad Request");
  });

  it("should create an instance with code", () => {
    const error = new HttpException(HttpStatusCode.BAD_REQUEST, {
      code: "INVALID_INPUT",
    });
    expect(error.code).toBe("INVALID_INPUT");
  });
});

describe("getStatusCode", () => {
  it.each([
    [{ status: 404 }, 404],
    [{ message: "error" }, HttpStatusCode.INTERNAL_SERVER_ERROR],
    ["error", HttpStatusCode.INTERNAL_SERVER_ERROR],
    [null, HttpStatusCode.INTERNAL_SERVER_ERROR],
  ])("should return %s for input %s", (input, expected) => {
    expect(getStatusCode(input)).toBe(expected);
  });
});
