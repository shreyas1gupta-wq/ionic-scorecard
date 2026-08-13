/**
 * Configuration, with the production guards that matter.
 *
 * The dangerous thing in this file is the local-development identity shim. It
 * lets you run the app without a Cloudflare account by declaring "I am
 * alice@ionic.in" in an environment variable. That is genuinely necessary — the
 * alternative is that nothing can be developed or demoed without a deployed
 * Access application — and it is also an authentication bypass if it ever ships.
 *
 * So it is guarded three ways, all of which must hold:
 *
 *   1. NODE_ENV must not be `production`;
 *   2. CRM_ALLOW_DEV_IDENTITY must be exactly `1` — a second, explicit opt-in, so
 *      a stray email variable is not enough on its own;
 *   3. loadConfig THROWS if either variable is present while NODE_ENV is
 *      production. It refuses to boot rather than booting insecurely.
 *
 * Rule 3 is the important one. Guards that merely ignore a dangerous setting
 * leave you unsure whether protection worked; a guard that refuses to start tells
 * you immediately, in the deployment logs, before a single request is served.
 */

import type { AccessConfig } from './access';

export interface AppConfig {
  readonly access: AccessConfig;
  /** Non-null ONLY in a correctly opted-in development environment. */
  readonly devIdentityEmail: string | null;
  readonly isProduction: boolean;
}

export class ConfigError extends Error {
  override readonly name = 'ConfigError';
}

export type Env = Readonly<Record<string, string | undefined>>;

const TRUE = '1';

export function loadConfig(env: Env): AppConfig {
  const isProduction = env.NODE_ENV === 'production';

  const devEmail = env.CRM_DEV_IDENTITY_EMAIL?.trim() ?? '';
  const devAllowed = env.CRM_ALLOW_DEV_IDENTITY?.trim() === TRUE;

  // Guard 3: refuse to boot rather than boot insecurely.
  if (isProduction && (devEmail.length > 0 || devAllowed)) {
    throw new ConfigError(
      'CRM_DEV_IDENTITY_EMAIL / CRM_ALLOW_DEV_IDENTITY are set with NODE_ENV=production. ' +
        'The development identity shim is an authentication bypass and must never be enabled ' +
        'in production. Unset both and redeploy.',
    );
  }

  const teamDomain = env.CRM_ACCESS_TEAM_DOMAIN?.trim() ?? '';
  const audience = env.CRM_ACCESS_AUD?.trim() ?? '';

  const devIdentityEmail =
    !isProduction && devAllowed && devEmail.length > 0 ? devEmail.toLowerCase() : null;

  // Access config is mandatory unless the dev shim is legitimately active —
  // otherwise there would be no way to authenticate anyone at all, and an app
  // that starts with no authentication is worse than one that will not start.
  if (devIdentityEmail === null) {
    if (teamDomain.length === 0) {
      throw new ConfigError('CRM_ACCESS_TEAM_DOMAIN is required (e.g. yourteam.cloudflareaccess.com)');
    }
    if (audience.length === 0) {
      throw new ConfigError(
        'CRM_ACCESS_AUD is required. Without it the audience check is skipped, and a token ' +
          'minted for a different application in the same Cloudflare team would be accepted.',
      );
    }
  }

  return {
    access: { teamDomain, audience },
    devIdentityEmail,
    isProduction,
  };
}
