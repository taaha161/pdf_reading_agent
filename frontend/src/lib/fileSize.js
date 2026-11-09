/**
 * Upload size limits by tier. The server is the source of truth (it enforces these
 * and reports the caller's limit as /api/usage `max_file_bytes`); these are the
 * fallbacks used before usage has loaded. Keep in sync with backend/main.py.
 */
export const MB = 1024 * 1024;
export const MAX_FILE_BYTES_ANON = 20 * MB;
export const MAX_FILE_BYTES_SIGNED_IN = 30 * MB;
export const MAX_FILE_BYTES_PAID = 50 * MB;

export const formatMB = (bytes) => `${Math.round(bytes / MB)} MB`;

/** The caller's upload limit. Ignores usage fetched for a different auth state (e.g. right after login). */
export function maxFileBytes(usage, isLoggedIn) {
  if (usage?.max_file_bytes && usage.authenticated === isLoggedIn) return usage.max_file_bytes;
  if (!isLoggedIn) return MAX_FILE_BYTES_ANON;
  return usage?.subscription_active ? MAX_FILE_BYTES_PAID : MAX_FILE_BYTES_SIGNED_IN;
}

/**
 * What to tell a user whose file is over their limit, and what would raise it.
 * upgrade: "signup" | "subscribe" | null (already at the top tier).
 */
export function fileTooLarge(sizeBytes, maxBytes) {
  const intro = `This PDF is ${(sizeBytes / MB).toFixed(1)} MB. The maximum file size is ${formatMB(maxBytes)}.`;
  if (maxBytes < MAX_FILE_BYTES_SIGNED_IN) {
    return { upgrade: "signup", message: `${intro} Create a free account to upload up to ${formatMB(MAX_FILE_BYTES_SIGNED_IN)}.` };
  }
  if (maxBytes < MAX_FILE_BYTES_PAID) {
    return { upgrade: "subscribe", message: `${intro} Subscribe to upload up to ${formatMB(MAX_FILE_BYTES_PAID)}.` };
  }
  return { upgrade: null, message: `${intro} Try splitting it into smaller PDFs.` };
}
