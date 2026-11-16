/**
 * A statement waiting to be scanned, kept in this browser's IndexedDB:
 *  - dropped on the marketing site's upload box (written by marketing/src/lib/fileHandoff.ts), or
 *  - a guest's scan, kept while they sign up to use chat (written by handOffFile below).
 * Same origin via the Vercel proxy, so both sides share this database. Deleted when taken or expired.
 */
const DB = "bss-handoff";
const STORE = "files";
const KEY = "pending";
// Long enough to confirm a signup email; short enough that a statement doesn't linger.
const MAX_AGE_MS = 30 * 60 * 1000;

function open() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/** Store a file for a later scan. Resolves false if storage is unavailable. */
export async function handOffFile(file) {
  try {
    const db = await open();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put({ file, at: Date.now() }, KEY);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db.close();
    return true;
  } catch {
    return false;
  }
}

/** Name of the pending file without taking it, or null if none (or expired). */
export async function peekHandedOffFileName() {
  try {
    const db = await open();
    const record = await new Promise((resolve, reject) => {
      const req = db.transaction(STORE, "readonly").objectStore(STORE).get(KEY);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
    db.close();
    if (!record?.file || Date.now() - (record.at || 0) > MAX_AGE_MS) return null;
    return record.file.name || "statement.pdf";
  } catch {
    return null;
  }
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
