import test, { expect } from "@playwright/test";
import { NextResponse } from "next/server";

import {
  applySecurityHeaders,
  BASE_SECURITY_HEADERS,
  resolveSecurityHeaders,
  SECURITY_HEADERS,
} from "../lib/security/headers";

const STRICT_TRANSPORT_SECURITY_HEADER = new Map(SECURITY_HEADERS).get(
  "Strict-Transport-Security",
)!;

const ORIGINAL_NODE_ENV = process.env.NODE_ENV;

test.afterEach(() => {
  process.env.NODE_ENV = ORIGINAL_NODE_ENV;
});

test.describe("applySecurityHeaders", () => {
  test("sets the baseline security header set", () => {
    process.env.NODE_ENV = "development";

    const response = NextResponse.next();

    applySecurityHeaders(response);

    for (const [key, value] of BASE_SECURITY_HEADERS) {
      expect(response.headers.get(key)).toBe(value);
    }

    expect(response.headers.has("Strict-Transport-Security")).toBe(false);
  });

  test("overrides conflicting header values", () => {
    process.env.NODE_ENV = "production";

    const response = NextResponse.next();

    response.headers.set("Content-Security-Policy", "default-src *");
    response.headers.set("Strict-Transport-Security", "legacy-value");

    applySecurityHeaders(response);

    const expected = new Map(SECURITY_HEADERS);

    for (const [key, value] of expected.entries()) {
      expect(response.headers.get(key)).toBe(value);
    }
  });

  test("omits Strict-Transport-Security outside production by default", () => {
    process.env.NODE_ENV = "development";

    const response = NextResponse.next();
    response.headers.set("Strict-Transport-Security", "legacy-value");

    applySecurityHeaders(response);

    expect(response.headers.get("Strict-Transport-Security")).toBeNull();
  });

  test("enables Strict-Transport-Security by default in production", () => {
    process.env.NODE_ENV = "production";

    const response = NextResponse.next();

    applySecurityHeaders(response);

    expect(response.headers.get("Strict-Transport-Security")).toBe(
      STRICT_TRANSPORT_SECURITY_HEADER,
    );
  });

  test("allows opting into Strict-Transport-Security explicitly", () => {
    process.env.NODE_ENV = "development";

    const response = NextResponse.next();

    applySecurityHeaders(response, { includeStrictTransportSecurity: true });

    expect(response.headers.get("Strict-Transport-Security")).toBe(
      "max-age=63072000; includeSubDomains; preload",
    );
  });
});

test.describe("resolveSecurityHeaders", () => {
  test("returns the full security header set when requested", () => {
    const headers = resolveSecurityHeaders({
      includeStrictTransportSecurity: true,
    });

    expect(headers).toEqual(SECURITY_HEADERS);
  });

  test("omits Strict-Transport-Security when disabled", () => {
    const headers = resolveSecurityHeaders({
      includeStrictTransportSecurity: false,
    });

    for (const [key] of headers) {
      expect(key).not.toBe("Strict-Transport-Security");
    }
  });

  test("defaults to the baseline headers outside production", () => {
    process.env.NODE_ENV = "development";

    const headers = resolveSecurityHeaders();

    expect(headers).toEqual(BASE_SECURITY_HEADERS);
  });

  test("defaults to the full header set in production", () => {
    process.env.NODE_ENV = "production";

    const headers = resolveSecurityHeaders();

    expect(headers).toEqual(SECURITY_HEADERS);
  });
});
