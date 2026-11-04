/**
 * Hand a file from the marketing site to the scanner app (same origin, so same IndexedDB).
 * Reader lives in frontend/src/lib/fileHandoff.js — keep DB/store/key names in sync.
 */
const DB = 'bss-handoff';
const STORE = 'files';
const KEY = 'pending';

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/** Store the file for the scanner page. Resolves false if storage is unavailable. */
export async function handOffFile(file: File): Promise<boolean> {
  try {
    const db = await open();
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
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
