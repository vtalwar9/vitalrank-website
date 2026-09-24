// Decap CMS GitHub OAuth: step 2 — exchange the code for a token and hand it
// to the CMS popup via postMessage. Mapped to /api/callback via netlify.toml.
function parseCookies(header) {
  const out = {};
  for (const part of (header || '').split(';')) {
    const idx = part.indexOf('=');
    if (idx > 0) out[part.slice(0, idx).trim()] = decodeURIComponent(part.slice(idx + 1).trim());
  }
  return out;
}

function page(message) {
  return `<!doctype html><html><head><meta charset="utf-8"><title>Finishing sign in…</title></head>
<body><p>Finishing sign in…</p>
<script>
(function () {
  try {
    window.opener.postMessage(${JSON.stringify(message)}, window.location.origin);
  } catch (e) { /* popup may already be closed */ }
  setTimeout(function () { window.close(); }, 300);
})();
<\/script></body></html>`;
}

exports.handler = async (event) => {
  const noStore = { 'Cache-Control': 'no-store', 'Content-Type': 'text/html; charset=utf-8' };
  try {
    const clientId = process.env.GITHUB_CLIENT_ID;
    const clientSecret = process.env.GITHUB_CLIENT_SECRET;
    if (!clientId || !clientSecret) {
      return { statusCode: 500, headers: noStore, body: page('authorization:github:error:{"message":"OAuth not configured"}') };
    }
    const params = event.queryStringParameters || {};
    if (params.error) {
      return { statusCode: 200, headers: noStore, body: page(`authorization:github:error:${JSON.stringify({ message: params.error_description || params.error })}`) };
    }
    const cookies = parseCookies(event.headers && (event.headers.cookie || event.headers.Cookie));
    if (!params.code || !params.state || !cookies.gh_oauth_state || params.state !== cookies.gh_oauth_state) {
      return { statusCode: 400, headers: noStore, body: page('authorization:github:error:{"message":"Invalid OAuth state. Please try signing in again."}') };
    }
    const tokenRes = await fetch('https://github.com/login/oauth/access_token', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: clientId,
        client_secret: clientSecret,
        code: params.code,
      }),
    });
    const tokenData = await tokenRes.json();
    if (!tokenData.access_token) {
      const msg = tokenData.error_description || tokenData.error || 'Token exchange failed';
      return { statusCode: 200, headers: noStore, body: page(`authorization:github:error:${JSON.stringify({ message: msg })}`) };
    }
    const payload = JSON.stringify({ token: tokenData.access_token, provider: 'github' });
    return { statusCode: 200, headers: noStore, body: page(`authorization:github:success:${payload}`) };
  } catch (err) {
    return { statusCode: 200, headers: noStore, body: page(`authorization:github:error:${JSON.stringify({ message: 'Sign in failed. Please try again.' })}`) };
  }
};
