/** Decap CMS / Github login on Cloudflare Pages Functions.
 * Requires environment variables: GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET.
 * No secrets belong in repository. GitHub OAuth users need repository write access.
 */
export async function onRequestGet({request, env}) {
  if (!env.GITHUB_CLIENT_ID || !env.GITHUB_CLIENT_SECRET) {
    return new Response('CMS OAuth is not configured yet: Cloudflare secrets are missing.', {status:503,headers:{'Cache-Control':'no-store'}});
  }
  const origin = new URL(request.url).origin;
  // Keep OAuth tied to the canonical staging host. Preview deployment links are not OAuth endpoints.
  if (origin !== 'https://expteam-staging.pages.dev') {
    return new Response('Use the canonical staging domain for CMS login.', {status:403});
  }
  const state = crypto.randomUUID().replace(/-/g,'') + crypto.randomUUID().replace(/-/g,'');
  const authorize = new URL('https://github.com/login/oauth/authorize');
  authorize.searchParams.set('client_id', env.GITHUB_CLIENT_ID);
  authorize.searchParams.set('redirect_uri', origin + '/api/callback');
  authorize.searchParams.set('scope', 'repo');
  authorize.searchParams.set('state', state);
  const headers = new Headers({
    'Location':authorize.href,
    'Cache-Control':'no-store',
    'Referrer-Policy':'no-referrer',
    'Set-Cookie': `et_cms_oauth_state=${state}; Max-Age=600; Path=/api; HttpOnly; Secure; SameSite=Lax`
  });
  return new Response(null,{status:302,headers});
}
