import { defineCloudflareConfig } from '@opennextjs/cloudflare';

/**
 * OpenNext turns the Next build output into a single Cloudflare Worker.
 *
 * Deliberately minimal. Incremental-cache and tag-cache backings are not
 * configured because every route in this app is `force-dynamic` — it is an
 * internal tool where a cached ticket list would be actively wrong, so there is
 * nothing to cache and no R2 or KV binding to justify.
 *
 * The number this file exists to be measured against: the Cloudflare Workers
 * FREE plan caps a Worker at 3 MiB gzipped. Exceeding it means the paid plan
 * ($5/month) rather than a broken app — see IONIC_CRM/DEPLOY_RESEARCH.md.
 */
export default defineCloudflareConfig();
