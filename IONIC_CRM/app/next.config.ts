import type { NextConfig } from 'next';

const config: NextConfig = {
  reactStrictMode: true,

  // Type errors must fail the build. The default already does this; stating it
  // makes it obvious if anyone is ever tempted to switch it off to get a deploy
  // out. (There is no `eslint` key in Next 16 — it was removed with `next lint`.)
  typescript: { ignoreBuildErrors: false },

  // PGlite ships a WASM binary and is used as the local development database
  // (see src/server/db.ts). Leaving it external stops the bundler trying to
  // inline the .wasm asset.
  serverExternalPackages: ['@electric-sql/pglite'],

  /**
   * Security headers.
   *
   * Cloudflare Access is the front door, but these are the belt to its braces —
   * they matter for exactly the case Access is not covering, which is a request
   * that reached the origin some other way.
   */
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          // Genuinely missing, not churn: this is the one standard security
          // header the previous pass omitted. It only takes effect over HTTPS
          // (browsers ignore it on plain HTTP, so sending it unconditionally
          // here is harmless for local dev), and it matters specifically
          // because the CSP/frame/referrer headers below assume the browser
          // is already talking HTTPS to this origin — HSTS is what forces
          // that assumption to hold for the browser itself, independent of
          // whatever Cloudflare's own edge TLS settings are doing. No
          // `preload`: preload submission is an irrevocable public commitment
          // appropriate for a consumer domain, not for an internal tool
          // sitting behind Access on a hostname that may yet change.
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Cross-Origin-Opener-Policy', value: 'same-origin' },
          // An internal tool has no reason to want any of these.
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
          // No third-party origins at all: no CDN scripts, no external fonts.
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              // Next injects inline bootstrap scripts; 'unsafe-inline' is
              // required for them and is the one concession here.
              "script-src 'self' 'unsafe-inline'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data:",
              "font-src 'self'",
              "connect-src 'self'",
              "form-action 'self'",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "object-src 'none'",
            ].join('; '),
          },
        ],
      },
    ];
  },
};

export default config;
