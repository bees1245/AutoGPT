import securityHeaderConfig from "./security-headers.config.json";
import { type NextResponse } from "next/server";

export type SecurityHeader = readonly [key: string, value: string];

interface RawSecurityHeaderConfig {
  readonly contentSecurityPolicy: readonly string[];
  readonly baseSecurityHeaders: readonly [string, string][];
  readonly strictTransportSecurity: readonly [string, string];
}

const rawConfig = securityHeaderConfig as RawSecurityHeaderConfig;

const CONTENT_SECURITY_POLICY = rawConfig.contentSecurityPolicy.join("; ");

const BASE_SECURITY_HEADERS: readonly SecurityHeader[] = Object.freeze([
  Object.freeze(["Content-Security-Policy", CONTENT_SECURITY_POLICY]) as SecurityHeader,
  ...rawConfig.baseSecurityHeaders.map(
    ([key, value]) => Object.freeze([key, value]) as SecurityHeader,
  ),
]);

const STRICT_TRANSPORT_SECURITY = Object.freeze([
  ...rawConfig.strictTransportSecurity,
]) as SecurityHeader;

export const SECURITY_HEADERS: readonly SecurityHeader[] = Object.freeze([
  ...BASE_SECURITY_HEADERS,
  STRICT_TRANSPORT_SECURITY,
]);

export interface SecurityHeaderOptions {
  readonly includeStrictTransportSecurity?: boolean;
}

function normalizeOptions(
  options?: SecurityHeaderOptions,
): Required<SecurityHeaderOptions> {
  return {
    includeStrictTransportSecurity:
      options?.includeStrictTransportSecurity ??
      process.env.NODE_ENV === "production",
  };
}

export function resolveSecurityHeaders(
  options?: SecurityHeaderOptions,
): readonly SecurityHeader[] {
  const normalized = normalizeOptions(options);

  return normalized.includeStrictTransportSecurity
    ? SECURITY_HEADERS
    : BASE_SECURITY_HEADERS;
}

export function applySecurityHeaders<
  ResponseType extends NextResponse | Response,
>(response: ResponseType, options?: SecurityHeaderOptions): ResponseType {
  const normalized = normalizeOptions(options);
  const headersToApply = resolveSecurityHeaders(normalized);

  if (!normalized.includeStrictTransportSecurity) {
    response.headers.delete(STRICT_TRANSPORT_SECURITY[0]);
  }

  for (const [key, value] of headersToApply) {
    response.headers.set(key, value);
  }

  return response;
}

export { BASE_SECURITY_HEADERS, CONTENT_SECURITY_POLICY };
