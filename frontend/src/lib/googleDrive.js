/**
 * "Upload from Google Drive": Google Identity Services (OAuth token, drive.file scope)
 * + Google Picker. The chosen PDF is downloaded in the browser with the user's token
 * and handed back as a File, so it goes through the normal /api/process-pdf flow.
 * Scripts load lazily on first click. Keys come from /api/config.
 */
import { getConfig } from "./config";

const SCOPE = "https://www.googleapis.com/auth/drive.file";
const scriptPromises = {};
let accessToken = null;
let tokenExpiresAt = 0;

function loadScript(src) {
  if (!scriptPromises[src]) {
    scriptPromises[src] = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = resolve;
      s.onerror = () => {
        delete scriptPromises[src];
        reject(new Error("Could not load Google Drive. Disable ad/script blockers for this site and try again."));
      };
      document.head.appendChild(s);
    });
  }
  return scriptPromises[src];
}

export function isGoogleDriveConfigured() {
  const c = getConfig();
  return Boolean(c?.googleClientId && c?.googleApiKey);
}

async function loadPicker() {
  await Promise.all([
    loadScript("https://apis.google.com/js/api.js"),
    loadScript("https://accounts.google.com/gsi/client"),
  ]);
  if (!window.google?.picker) {
    await new Promise((resolve, reject) =>
      window.gapi.load("picker", { callback: resolve, onerror: () => reject(new Error("Could not load Google Picker.")) })
    );
  }
}

function requestToken(clientId) {
  if (accessToken && Date.now() < tokenExpiresAt) return Promise.resolve(accessToken);
  return new Promise((resolve, reject) => {
    const client = window.google.accounts.oauth2.initTokenClient({
      client_id: clientId,
      scope: SCOPE,
      callback: (resp) => {
        if (resp.error) {
          reject(new Error("Google sign-in was cancelled or failed."));
          return;
        }
        accessToken = resp.access_token;
        tokenExpiresAt = Date.now() + (Number(resp.expires_in) - 60) * 1000;
        resolve(accessToken);
      },
      error_callback: () => reject(new Error("Google sign-in was cancelled.")),
    });
    client.requestAccessToken({ prompt: accessToken ? "" : "consent" });
  });
}

function showPicker({ token, apiKey, appId }) {
  return new Promise((resolve) => {
    const gp = window.google.picker;
    const view = new gp.DocsView(gp.ViewId.DOCS).setMimeTypes("application/pdf").setIncludeFolders(true);
    let builder = new gp.PickerBuilder()
      .addView(view)
      .setOAuthToken(token)
      .setDeveloperKey(apiKey)
      .setTitle("Choose a bank statement PDF")
      .setCallback((data) => {
        const action = data[gp.Response.ACTION];
        if (action === gp.Action.PICKED) resolve(data[gp.Response.DOCUMENTS][0]);
        else if (action === gp.Action.CANCEL) resolve(null);
      });
    if (appId) builder = builder.setAppId(appId);
    builder.build().setVisible(true);
  });
}

/**
 * Open the Drive picker. Resolves to a File, or null if the user cancelled.
 * @param {number} maxBytes reject files larger than this before downloading
 */
export async function pickPdfFromGoogleDrive(maxBytes) {
  const { googleClientId, googleApiKey, googleAppId } = getConfig() || {};
  if (!googleClientId || !googleApiKey) throw new Error("Google Drive upload isn't configured.");
  await loadPicker();
  const token = await requestToken(googleClientId);
  const doc = await showPicker({ token, apiKey: googleApiKey, appId: googleAppId });
  if (!doc) return null;

  const id = doc[window.google.picker.Document.ID];
  const name = doc[window.google.picker.Document.NAME] || "statement.pdf";
  const size = Number(doc.sizeBytes || 0);
  if (maxBytes && size > maxBytes) throw new Error("That PDF is too large (max 20 MB).");

  const res = await fetch(`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(id)}?alt=media`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    if (res.status === 401) accessToken = null;
    throw new Error("Couldn't download that file from Google Drive. Please try again.");
  }
  const blob = await res.blob();
  if (maxBytes && blob.size > maxBytes) throw new Error("That PDF is too large (max 20 MB).");
  return new File([blob], name.toLowerCase().endsWith(".pdf") ? name : `${name}.pdf`, { type: "application/pdf" });
}
