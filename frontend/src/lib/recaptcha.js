/**
 * Google reCAPTCHA v3 (invisible). The script is loaded lazily on first use so
 * pages that never scan don't pay for it. Site key comes from /api/config.
 */
import { getConfig } from "./config";

let loading = null;

function loadScript(siteKey) {
  if (loading) return loading;
  loading = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = `https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(siteKey)}`;
    s.async = true;
    s.onload = () => window.grecaptcha.ready(() => resolve(window.grecaptcha));
    s.onerror = () => {
      loading = null;
      reject(new Error("Could not load reCAPTCHA. Disable ad/script blockers for this site and try again."));
    };
    document.head.appendChild(s);
  });
  return loading;
}

/** Fresh token for `action`, or null when no site key is configured (local dev). */
export async function getRecaptchaToken(action) {
  const siteKey = getConfig()?.recaptchaSiteKey;
  if (!siteKey) return null;
  const grecaptcha = await loadScript(siteKey);
  return grecaptcha.execute(siteKey, { action });
}
