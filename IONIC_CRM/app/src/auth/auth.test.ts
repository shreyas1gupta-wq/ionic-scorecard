import { describe, it, expect, beforeAll } from 'vitest';
import { SignJWT, generateKeyPair, type CryptoKey, type JWTVerifyGetKey } from 'jose';
import {
  AccessDeniedError,
  ACCESS_JWT_COOKIE,
  ACCESS_JWT_HEADER,
  denyResponse,
  extractAccessToken,
  jwksUrlFor,
  verifyAccessJwt,
  type AccessConfig,
} from './access';
import { ConfigError, loadConfig } from './config';
import { authenticate } from './identity';
import { createMemoryRepository } from '../repo/memory';

const TEAM = 'ionic.cloudflareaccess.com';
const ISSUER = `https://${TEAM}`;
const AUD = 'aud-tag-for-this-application';
const CFG: AccessConfig = { teamDomain: TEAM, audience: AUD };

let privateKey: CryptoKey;
let getKey: JWTVerifyGetKey;
/** A different key pair, for the "signed by someone else" case. */
let attackerKey: CryptoKey;

beforeAll(async () => {
  const pair = await generateKeyPair('RS256');
  privateKey = pair.privateKey;
  getKey = (async () => pair.publicKey) as unknown as JWTVerifyGetKey;
  attackerKey = (await generateKeyPair('RS256')).privateKey;
});

interface TokenOpts {
  email?: string | undefined;
  issuer?: string;
  audience?: string;
  expiresIn?: string;
  notBefore?: string;
  key?: CryptoKey;
  alg?: string;
  omitEmail?: boolean;
}

async function makeToken(o: TokenOpts = {}): Promise<string> {
  const claims: Record<string, unknown> = { sub: 'cf-subject-1' };
  if (!o.omitEmail) claims.email = o.email ?? 'alice@ionic.in';

  return new SignJWT(claims)
    .setProtectedHeader({ alg: o.alg ?? 'RS256' })
    .setIssuedAt()
    .setIssuer(o.issuer ?? ISSUER)
    .setAudience(o.audience ?? AUD)
    .setExpirationTime(o.expiresIn ?? '5m')
    .setNotBefore(o.notBefore ?? '0s')
    .sign(o.key ?? privateKey);
}

// =============================================================================
describe('jwksUrlFor', () => {
  it('builds the documented certs endpoint', () => {
    expect(jwksUrlFor(TEAM).toString()).toBe(`${ISSUER}/cdn-cgi/access/certs`);
  });

  it('tolerates a scheme or trailing slash in configuration', () => {
    expect(jwksUrlFor('https://ionic.cloudflareaccess.com/').toString()).toBe(
      `${ISSUER}/cdn-cgi/access/certs`,
    );
  });

  it('rejects an empty team domain rather than building a nonsense URL', () => {
    expect(() => jwksUrlFor('')).toThrow(/teamDomain is required/);
  });
});

// =============================================================================
describe('verifyAccessJwt — accepts only what it should', () => {
  it('accepts a well-formed assertion and returns the identity', async () => {
    const id = await verifyAccessJwt(await makeToken(), CFG, { getKey });
    expect(id.email).toBe('alice@ionic.in');
    expect(id.subject).toBe('cf-subject-1');
  });

  it('lower-cases and trims the email, because it is a database join key', async () => {
    const id = await verifyAccessJwt(await makeToken({ email: '  Alice@Ionic.IN ' }), CFG, {
      getKey,
    });
    expect(id.email).toBe('alice@ionic.in');
  });
});

describe('verifyAccessJwt — fails closed', () => {
  it.each([
    ['null', null],
    ['undefined', undefined],
    ['empty string', ''],
    ['whitespace', '   '],
  ])('refuses a %s token', async (_label, token) => {
    await expect(verifyAccessJwt(token, CFG, { getKey })).rejects.toBeInstanceOf(AccessDeniedError);
  });

  it('refuses when the audience is not configured', async () => {
    // Without an AUD, jose skips the audience check — which would accept a valid
    // token minted for a DIFFERENT application in the same Cloudflare team.
    const token = await makeToken();
    await expect(
      verifyAccessJwt(token, { teamDomain: TEAM, audience: '' }, { getKey }),
    ).rejects.toThrow(/audience is not configured/);
  });

  it('refuses a token minted for another application', async () => {
    const token = await makeToken({ audience: 'aud-tag-for-some-other-app' });
    await expect(verifyAccessJwt(token, CFG, { getKey })).rejects.toBeInstanceOf(AccessDeniedError);
  });

  it('refuses a token from another Cloudflare team', async () => {
    const token = await makeToken({ issuer: 'https://someone-else.cloudflareaccess.com' });
    await expect(verifyAccessJwt(token, CFG, { getKey })).rejects.toBeInstanceOf(AccessDeniedError);
  });

  it('refuses an expired token', async () => {
    const token = await makeToken({ expiresIn: '-1m' });
    await expect(verifyAccessJwt(token, CFG, { getKey })).rejects.toBeInstanceOf(AccessDeniedError);
  });

  it('refuses a token that is not yet valid', async () => {
    const token = await makeToken({ notBefore: '10m' });
    await expect(verifyAccessJwt(token, CFG, { getKey })).rejects.toBeInstanceOf(AccessDeniedError);
  });

  it('refuses a token signed by a different key', async () => {
    const token = await makeToken({ key: attackerKey });
    await expect(verifyAccessJwt(token, CFG, { getKey })).rejects.toBeInstanceOf(AccessDeniedError);
  });

  it('refuses a tampered payload', async () => {
    const token = await makeToken();
    const [h, p, s] = token.split('.');
    const forged = JSON.parse(Buffer.from(p!, 'base64url').toString());
    forged.email = 'admin@ionic.in';
    const swapped = `${h}.${Buffer.from(JSON.stringify(forged)).toString('base64url')}.${s}`;
    await expect(verifyAccessJwt(swapped, CFG, { getKey })).rejects.toBeInstanceOf(
      AccessDeniedError,
    );
  });

  // The two classic JWT forgeries. Both must be refused by the pinned algorithm.
  it('refuses an unsecured token claiming alg: none', async () => {
    const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url');
    const payload = Buffer.from(
      JSON.stringify({
        email: 'admin@ionic.in',
        sub: 'x',
        iss: ISSUER,
        aud: AUD,
        exp: Math.floor(Date.now() / 1000) + 600,
      }),
    ).toString('base64url');
    await expect(verifyAccessJwt(`${header}.${payload}.`, CFG, { getKey })).rejects.toBeInstanceOf(
      AccessDeniedError,
    );
  });

  it('refuses a symmetric-algorithm token — the algorithm-confusion attack', async () => {
    const hs = await new SignJWT({ email: 'admin@ionic.in', sub: 'x' })
      .setProtectedHeader({ alg: 'HS256' })
      .setIssuedAt()
      .setIssuer(ISSUER)
      .setAudience(AUD)
      .setExpirationTime('5m')
      .sign(new Uint8Array(32));
    await expect(verifyAccessJwt(hs, CFG, { getKey })).rejects.toBeInstanceOf(AccessDeniedError);
  });

  it('refuses a verified token that carries no email claim', async () => {
    const token = await makeToken({ omitEmail: true });
    await expect(verifyAccessJwt(token, CFG, { getKey })).rejects.toThrow(/no email claim/);
  });

  it('never leaks the reason into the message the caller would surface', async () => {
    const token = await makeToken({ key: attackerKey });
    const err = await verifyAccessJwt(token, CFG, { getKey }).then(
      () => {
        throw new Error('expected the assertion to be refused');
      },
      (e: unknown) => e as AccessDeniedError,
    );
    expect(err.message).toBe('Access assertion failed verification');
    // The specifics are available for the server log, and only there.
    expect(err.detail).toBeTruthy();
  });
});

// =============================================================================
describe('extractAccessToken', () => {
  it('reads the header', () => {
    const h = new Headers({ [ACCESS_JWT_HEADER]: 'tok' });
    expect(extractAccessToken(h)).toBe('tok');
  });

  it('falls back to the Access cookie', () => {
    const h = new Headers({ cookie: `${ACCESS_JWT_COOKIE}=cookietok` });
    expect(extractAccessToken(h)).toBe('cookietok');
  });

  it('finds the cookie among others', () => {
    const h = new Headers({ cookie: `a=1; ${ACCESS_JWT_COOKIE}=cookietok; b=2` });
    expect(extractAccessToken(h)).toBe('cookietok');
  });

  it('prefers the header when both are present', () => {
    const h = new Headers({
      [ACCESS_JWT_HEADER]: 'headertok',
      cookie: `${ACCESS_JWT_COOKIE}=cookietok`,
    });
    expect(extractAccessToken(h)).toBe('headertok');
  });

  it('handles a JWT value containing = padding', () => {
    const h = new Headers({ cookie: `${ACCESS_JWT_COOKIE}=a=b=c` });
    expect(extractAccessToken(h)).toBe('a=b=c');
  });

  it('returns null when there is nothing', () => {
    expect(extractAccessToken(new Headers())).toBeNull();
    expect(extractAccessToken(new Headers({ cookie: 'other=1' }))).toBeNull();
    expect(extractAccessToken(new Headers({ [ACCESS_JWT_HEADER]: '  ' }))).toBeNull();
  });
});

describe('denyResponse', () => {
  it('is a bare 403 with no body and no caching', async () => {
    const r = denyResponse();
    expect(r.status).toBe(403);
    expect(await r.text()).toBe('');
    expect(r.headers.get('cache-control')).toBe('no-store');
  });
});

// =============================================================================
describe('loadConfig — the production guards', () => {
  const prod = { NODE_ENV: 'production', CRM_ACCESS_TEAM_DOMAIN: TEAM, CRM_ACCESS_AUD: AUD };

  it('accepts a well-formed production config', () => {
    const c = loadConfig(prod);
    expect(c.isProduction).toBe(true);
    expect(c.devIdentityEmail).toBeNull();
    expect(c.access).toEqual({ teamDomain: TEAM, audience: AUD });
  });

  it('REFUSES TO BOOT if the dev identity email is set in production', () => {
    expect(() => loadConfig({ ...prod, CRM_DEV_IDENTITY_EMAIL: 'alice@ionic.in' })).toThrow(
      ConfigError,
    );
  });

  it('REFUSES TO BOOT if only the dev opt-in flag is set in production', () => {
    expect(() => loadConfig({ ...prod, CRM_ALLOW_DEV_IDENTITY: '1' })).toThrow(ConfigError);
  });

  it('requires the team domain in production', () => {
    expect(() => loadConfig({ NODE_ENV: 'production', CRM_ACCESS_AUD: AUD })).toThrow(
      /CRM_ACCESS_TEAM_DOMAIN is required/,
    );
  });

  it('requires the audience, and says why', () => {
    expect(() =>
      loadConfig({ NODE_ENV: 'production', CRM_ACCESS_TEAM_DOMAIN: TEAM }),
    ).toThrow(/audience check is skipped/);
  });

  it('enables the dev shim only with BOTH the flag and the email', () => {
    const c = loadConfig({
      NODE_ENV: 'development',
      CRM_ALLOW_DEV_IDENTITY: '1',
      CRM_DEV_IDENTITY_EMAIL: 'Alice@Ionic.in',
    });
    expect(c.devIdentityEmail).toBe('alice@ionic.in');
  });

  it('ignores the email without the explicit opt-in flag', () => {
    // A stray variable must not be enough on its own.
    expect(() =>
      loadConfig({ NODE_ENV: 'development', CRM_DEV_IDENTITY_EMAIL: 'alice@ionic.in' }),
    ).toThrow(/CRM_ACCESS_TEAM_DOMAIN is required/);
  });

  it('ignores a flag value other than exactly 1', () => {
    expect(() =>
      loadConfig({
        NODE_ENV: 'development',
        CRM_ALLOW_DEV_IDENTITY: 'true',
        CRM_DEV_IDENTITY_EMAIL: 'alice@ionic.in',
      }),
    ).toThrow(/CRM_ACCESS_TEAM_DOMAIN is required/);
  });
});

// =============================================================================
describe('authenticate — email to actor', () => {
  const buildRepos = () =>
    createMemoryRepository({
      employees: [
        { workEmail: 'alice@ionic.in', displayName: 'Alice', role: 'EMPLOYEE' },
        { workEmail: 'gone@ionic.in', displayName: 'Gone', role: 'EMPLOYEE', status: 'DEACTIVATED' },
      ],
    });

  const prodConfig = loadConfig({
    NODE_ENV: 'production',
    CRM_ACCESS_TEAM_DOMAIN: TEAM,
    CRM_ACCESS_AUD: AUD,
  });

  it('resolves a verified email to an actor', async () => {
    const repositories = buildRepos();
    const headers = new Headers({ [ACCESS_JWT_HEADER]: await makeToken() });
    const user = await authenticate(headers, { config: prodConfig, repositories, getKey });
    expect(user.employee.workEmail).toBe('alice@ionic.in');
    expect(user.actor.employeeId).toBe(user.employee.id);
    expect(user.viaDevShim).toBe(false);
  });

  it('refuses an email that is verified but not an employee', async () => {
    const repositories = buildRepos();
    const headers = new Headers({
      [ACCESS_JWT_HEADER]: await makeToken({ email: 'contractor@ionic.in' }),
    });
    await expect(
      authenticate(headers, { config: prodConfig, repositories, getKey }),
    ).rejects.toBeInstanceOf(AccessDeniedError);
  });

  it('refuses a deactivated employee immediately — no session to expire', async () => {
    const repositories = buildRepos();
    const headers = new Headers({ [ACCESS_JWT_HEADER]: await makeToken({ email: 'gone@ionic.in' }) });
    await expect(
      authenticate(headers, { config: prodConfig, repositories, getKey }),
    ).rejects.toBeInstanceOf(AccessDeniedError);
  });

  it('gives the same error for unknown and deactivated — no enumeration', async () => {
    const repositories = buildRepos();
    const a = await authenticate(
      new Headers({ [ACCESS_JWT_HEADER]: await makeToken({ email: 'nobody@ionic.in' }) }),
      { config: prodConfig, repositories, getKey },
    ).catch((e) => (e as Error).message);
    const b = await authenticate(
      new Headers({ [ACCESS_JWT_HEADER]: await makeToken({ email: 'gone@ionic.in' }) }),
      { config: prodConfig, repositories, getKey },
    ).catch((e) => (e as Error).message);
    expect(a).toBe(b);
  });

  it('refuses a request with no assertion at all', async () => {
    const repositories = buildRepos();
    await expect(
      authenticate(new Headers(), { config: prodConfig, repositories, getKey }),
    ).rejects.toBeInstanceOf(AccessDeniedError);
  });

  it('uses the dev shim when legitimately enabled, without any token', async () => {
    const repositories = buildRepos();
    const config = loadConfig({
      NODE_ENV: 'development',
      CRM_ALLOW_DEV_IDENTITY: '1',
      CRM_DEV_IDENTITY_EMAIL: 'alice@ionic.in',
    });
    const user = await authenticate(new Headers(), { config, repositories });
    expect(user.employee.workEmail).toBe('alice@ionic.in');
    expect(user.viaDevShim).toBe(true);
  });

  it('still enforces the allow-list under the dev shim', async () => {
    const repositories = buildRepos();
    const config = loadConfig({
      NODE_ENV: 'development',
      CRM_ALLOW_DEV_IDENTITY: '1',
      CRM_DEV_IDENTITY_EMAIL: 'stranger@ionic.in',
    });
    await expect(authenticate(new Headers(), { config, repositories })).rejects.toBeInstanceOf(
      AccessDeniedError,
    );
  });
});
