/**
 * Counts arrivals from links we tagged (YouTube descriptions, posts) by
 * recording one row when a page is requested with utm_source. Writes to
 * `arrivals` in D1 `authorkit_arrivals` (schema: authorkit-resources/migrations/0001_arrivals.sql); the hub's
 * fetch-authorkit.mjs reads it. Copy of authorkit-resources/functions/_middleware.js;
 * change both together.
 *
 * Stores no IP, no user agent and no visit id. Untagged requests are not
 * recorded. Runs after the response is ready, so a failed write never
 * blocks the page.
 */
const TAG = /^[a-z0-9._-]{1,64}$/;
const BOT = /bot|crawl|spider|headless|lighthouse|preview|facebookexternalhit/i;

const tag = (v) => {
  const s = (v || '').toLowerCase();
  return TAG.test(s) ? s : null;
};

/** The row to store for this request, or null to store nothing. Exported for the test. */
export function arrivalRow(url, userAgent, country) {
  const source = tag(url.searchParams.get('utm_source'));
  if (!source || BOT.test(userAgent || '')) return null;
  return {
    host: url.hostname.slice(0, 100),
    source,
    campaign: tag(url.searchParams.get('utm_campaign')),
    content: tag(url.searchParams.get('utm_content')),
    path: url.pathname.slice(0, 200),
    country: /^[A-Z]{2}$/.test(country || '') ? country : null,
  };
}

export async function onRequest(context) {
  const { request, env, next } = context;
  // ponytail: a reload of a tagged URL counts again; add a visit id if exact uniques matter.
  if (request.method === 'GET' && env.DB) {
    const row = arrivalRow(new URL(request.url), request.headers.get('user-agent'), request.cf?.country);
    if (row) {
      context.waitUntil(
        env.DB.prepare('INSERT INTO arrivals (ts, host, source, campaign, content, path, country) VALUES (?, ?, ?, ?, ?, ?, ?)')
          .bind(Math.floor(Date.now() / 1000), row.host, row.source, row.campaign, row.content, row.path, row.country)
          .run()
          .catch((err) => console.error('arrival:', err))
      );
    }
  }
  return next();
}
