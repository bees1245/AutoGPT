import test, { expect } from "@playwright/test";
import { NextResponse } from "next/server";

import {
  applySecurityHeaders,
  BASE_SECURITY_HEADERS,
  resolveSecurityHeaders,
  SECURITY_HEADERS,
  strictTransportSecurityDefaultEnabled,
} from "../lib/security/headers";

const STRICT_TRANSPORT_SECURITY_HEADER = new Map(SECURITY_HEADERS).get(
  "Strict-Transport-Security",
)!;

const ORIGINAL_NODE_ENV = process.env.NODE_ENV;
const ORIGINAL_VERCEL_ENV = process.env.VERCEL_ENV;
const ORIGINAL_NEXT_PUBLIC_VERCEL_ENV = process.env.NEXT_PUBLIC_VERCEL_ENV;

function setEnv(
  key: "NODE_ENV" | "VERCEL_ENV" | "NEXT_PUBLIC_VERCEL_ENV",
  value: string | undefined,
) {
  if (typeof value === "undefined") {
    delete process.env[key];
    return;
  }

  process.env[key] = value;
}

test.afterEach(() => {
  setEnv("NODE_ENV", ORIGINAL_NODE_ENV);
  setEnv("VERCEL_ENV", ORIGINAL_VERCEL_ENV);
  setEnv("NEXT_PUBLIC_VERCEL_ENV", ORIGINAL_NEXT_PUBLIC_VERCEL_ENV);
});

test.describe("applySecurityHeaders", () => {
  test("sets the baseline security header set", () => {
    setEnv("NODE_ENV", "development");
    setEnv("VERCEL_ENV", undefined);
    setEnv("NEXT_PUBLIC_VERCEL_ENV", undefined);

    const response = NextResponse.next();

    applySecurityHeaders(response);

    for (const [key, value] of BASE_SECURITY_HEADERS) {
      expect(response.headers.get(key)).toBe(value);
    }

    expect(response.headers.has("Strict-Transport-Security")).toBe(false);
  });

  test("overrides conflicting header values", () => {
    setEnv("NODE_ENV", "production");
    setEnv("VERCEL_ENV", "production");

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
    setEnv("NODE_ENV", "development");
    setEnv("VERCEL_ENV", undefined);

    const response = NextResponse.next();
    response.headers.set("Strict-Transport-Security", "legacy-value");

    applySecurityHeaders(response);

    expect(response.headers.get("Strict-Transport-Security")).toBeNull();
  });

  test("enables Strict-Transport-Security by default in production", () => {
    setEnv("NODE_ENV", "production");
    setEnv("VERCEL_ENV", "production");

    const response = NextResponse.next();

    applySecurityHeaders(response);

    expect(response.headers.get("Strict-Transport-Security")).toBe(
      STRICT_TRANSPORT_SECURITY_HEADER,
    );
  });

  test("allows opting into Strict-Transport-Security explicitly", () => {
    setEnv("NODE_ENV", "development");
    setEnv("VERCEL_ENV", undefined);

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
    setEnv("NODE_ENV", "development");
    setEnv("VERCEL_ENV", undefined);

    const headers = resolveSecurityHeaders();

    expect(headers).toEqual(BASE_SECURITY_HEADERS);
  });

  test("defaults to the full header set in production", () => {
    setEnv("NODE_ENV", "production");
    setEnv("VERCEL_ENV", "production");

    const headers = resolveSecurityHeaders();

    expect(headers).toEqual(SECURITY_HEADERS);
  });
});

test.describe("strictTransportSecurityDefaultEnabled", () => {
  test("returns false when no production environment is configured", () => {
    setEnv("NODE_ENV", "development");
    setEnv("VERCEL_ENV", undefined);
    setEnv("NEXT_PUBLIC_VERCEL_ENV", undefined);

    expect(strictTransportSecurityDefaultEnabled()).toBe(false);
  });

  test("honours Vercel deploy target over NODE_ENV", () => {
    setEnv("NODE_ENV", "production");
    setEnv("VERCEL_ENV", "preview");

    expect(strictTransportSecurityDefaultEnabled()).toBe(false);
  });

  test("enables the flag for production deploys", () => {
    setEnv("NODE_ENV", "production");
    setEnv("VERCEL_ENV", "production");

    expect(strictTransportSecurityDefaultEnabled()).toBe(true);
  });

  test("falls back to NODE_ENV when deploy target is missing", () => {
    setEnv("NODE_ENV", "production");
    setEnv("VERCEL_ENV", undefined);
    setEnv("NEXT_PUBLIC_VERCEL_ENV", undefined);

    expect(strictTransportSecurityDefaultEnabled()).toBe(true);
  });

  test("respects NEXT_PUBLIC_VERCEL_ENV when VERCEL_ENV is undefined", () => {
    setEnv("NODE_ENV", "production");
    setEnv("VERCEL_ENV", undefined);
    setEnv("NEXT_PUBLIC_VERCEL_ENV", "preview");

    expect(strictTransportSecurityDefaultEnabled()).toBe(false);
  });
});
