// Decap CMS GitHub OAuth: step 1 — handshake page (mapped to /api/auth).
//
// Decap opens this URL in a popup and runs a two-step handshake before it
// will accept the final token:
//   1. This page posts "authorizing:github" to the opener (the CMS).
//   2. The CMS echoes "authorizing:github" back to this popup.
//   3. Only then does this page redirect the popup to GitHub.
//
// Skipping the handshake leaves the CMS waiting forever ("stuck after login").
const SITE_URL = process.env.SITE_URL || 'https://vitalrank.netlify.app';
const CALLBACK_PATH = '/api/callback';

exports.handler = async (event) => {
  const clientId = process.env.GITHUB_CLIENT_ID;
  if (!clientId) {
    return { statusCode: 500, body: 'GitHub OAuth is not configured (missing GITHUB_CLIENT_ID).' };
  }
  const params = event.queryStringParameters || {};
  const provider = params.provider || 'github';
  const scope = params.scope || 'repo,user';
  const state = Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
  const redirectUri = `${SITE_URL}${CALLBACK_PATH}`;
  const authUrl =
    'https://github.com/login/oauth/authorize' +
    `?client_id=${encodeURIComponent(clientId)}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    `&scope=${encodeURIComponent(scope)}` +
    `&state=${encodeURIComponent(state)}`;

  const html = `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signing in…</title></head>
<body><p>Signing in with GitHub…</p>
<script>
(function () {
  var targetOrigin = ${JSON.stringify(SITE_URL)};
  var provider = ${JSON.stringify(provider)};
  var authUrl = ${JSON.stringify(authUrl)};
  var replied = false;
  function receiveMessage(e) {
    if (replied) return;
    if (e.origin !== targetOrigin) return;
    if (e.data === 'authorizing:' + provider) {
      replied = true;
      window.removeEventListener('message', receiveMessage, false);
      window.location.href = authUrl;
    }
  }
  window.addEventListener('message', receiveMessage, false);
  function ping() {
    if (replied) return;
    try { window.opener.postMessage('authorizing:' + provider, targetOrigin); }
    catch (err) { /* opener unavailable */ }
  }
  ping();
  var attempts = 0;
  var timer = setInterval(function () {
    attempts++;
    if (replied || attempts > 10) { clearInterval(timer); return; }
    ping();
  }, 400);
})();
<\/script></body></html>`;

  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'Set-Cookie': `gh_oauth_state=${state}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=600`,
    },
    body: html,
  };
};
