/**
 * Read a file handed off from the marketing site's upload box (marketing/src/lib/fileHandoff.ts).
 * Same origin via the Vercel proxy, so both sides share this IndexedDB database.
 */
const DB = "bss-handoff";
const STORE = "files";
const KEY = "pending";
const MAX_AGE_MS = 10 * 60 * 1000;

function open() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/** Take (read and delete) the pending file. Returns a File or null. */
export async function takeHandedOffFile() {
  try {
    const db = await open();
    const record = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      const store = tx.objectStore(STORE);
      const get = store.get(KEY);
      get.onsuccess = () => {
        store.delete(KEY);
        resolve(get.result || null);
      };
      tx.onerror = () => reject(tx.error);
    });
    db.close();
    if (!record?.file || Date.now() - (record.at || 0) > MAX_AGE_MS) return null;
    const f = record.file;
    return f instanceof File ? f : new File([f], f.name || "statement.pdf", { type: f.type || "application/pdf" });
  } catch {
    return null;
  }
}
