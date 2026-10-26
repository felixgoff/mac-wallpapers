// Felix's Cloudflare Worker: fetches any URL and adds the CORS headers the page needs (…workers.dev/<url>)
const PROXY = 'https://dry-dawn-9e3c.felixmgoff.workers.dev/';
const SAFARI = /Safari\//.test(navigator.userAgent) && !/Chrome|Chromium|CriOS|FxiOS|Edg|OPR|Firefox/.test(navigator.userAgent);

// For <video>: only Safari trusts the certificate of Apple's aerial server
export const playable = u => !SAFARI && u.startsWith('https://sylvan.apple.com/') ? PROXY + u : u;

// For fetch: Apple's catalog and GitHub Release files don't allow in-page downloads in any browser
export const fetchable = u => /^https:\/\/(updates\.cdn-apple\.com|github\.com)\//.test(u) ? PROXY + u : playable(u);
