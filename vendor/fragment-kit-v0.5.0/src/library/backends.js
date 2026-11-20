export class LibraryError extends Error {
  constructor(code, message, detail = {}) { super(message); this.name = 'LibraryError'; Object.assign(this, { code, ...detail }); }
}
const unavailable = () => new LibraryError('unavailable', 'This browser cannot keep a local library here. Your work stays in drafts and links.');
const request = value => new Promise((resolve, reject) => { value.onsuccess = () => resolve(value.result); value.onerror = () => reject(value.error); });

/** IndexedDB backend. `work` may only await the operations it is given: other awaits let IndexedDB commit early. */
export function indexedDBBackend({ name, factory }) {
  if (typeof name !== 'string' || !name) throw new Error('A prefixed library database name is required.');
  return {
    name,
    async open(schema) {
      let idb; try { idb = factory ?? globalThis.indexedDB; } catch { idb = null; }
      if (!idb) throw unavailable();
      let db;
      try {
        const opening = idb.open(name, schema.version);
        opening.onupgradeneeded = () => {
          const database = opening.result, upgrade = opening.transaction;
          for (const [store, { key, indexes = {} }] of Object.entries(schema.stores)) {
            const target = database.objectStoreNames.contains(store) ? upgrade.objectStore(store) : database.createObjectStore(store, { keyPath: key });
            for (const [index, { path, unique = false }] of Object.entries(indexes)) if (!target.indexNames.contains(index)) target.createIndex(index, path, { unique });
          }
        };
        opening.onblocked = () => {};
        db = await request(opening);
      } catch { throw unavailable(); }
      db.onversionchange = () => db.close();
      return {
        transaction(stores, mode, work) {
          return new Promise((resolve, reject) => {
            let tx, result, failed;
            try { tx = db.transaction(stores, mode); } catch (error) { reject(error); return; }
            const ops = {
              get: (store, key) => request(tx.objectStore(store).get(key)),
              put: (store, value) => request(tx.objectStore(store).put(value)),
              delete: (store, key) => request(tx.objectStore(store).delete(key)),
              all: store => request(tx.objectStore(store).getAll()),
              keys: store => request(tx.objectStore(store).getAllKeys()),
              index: (store, index, value) => request(tx.objectStore(store).index(index).getAll(value)),
            };
            Promise.resolve().then(() => work(ops)).then(value => { result = value; }, error => { failed = error; try { tx.abort(); } catch { /* already aborting */ } });
            tx.oncomplete = () => failed ? reject(failed) : resolve(result);
            tx.onabort = () => reject(failed ?? tx.error ?? new DOMException('The library transaction was aborted.', 'AbortError'));
          });
        },
        close() { db.close(); },
      };
    },
  };
}

/** In-memory backend with IndexedDB-like semantics: serialized, atomic transactions, cloned values and unique indexes. */
export function memoryBackend() {
  const data = new Map();
  let queue = Promise.resolve(), opened = null;
  return {
    data,
    async open(schema) {
      opened = schema;
      for (const store of Object.keys(schema.stores)) if (!data.has(store)) data.set(store, new Map());
      return {
        transaction(stores, mode, work) {
          const run = async () => {
            const draft = new Map([...data].map(([store, rows]) => [store, new Map(rows)]));
            const scope = store => {
              if (!stores.includes(store)) throw new DOMException(`${store} is not in this transaction.`, 'NotFoundError');
              return draft.get(store);
            };
            const writable = () => { if (mode !== 'readwrite') throw new DOMException('Read-only transaction.', 'ReadOnlyError'); };
            const ops = {
              async get(store, key) { return structuredClone(scope(store).get(key)); },
              async put(store, value) {
                writable(); const { key, indexes = {} } = opened.stores[store], rows = scope(store), id = value[key];
                for (const { path, unique } of Object.values(indexes)) {
                  if (unique && [...rows.values()].some(row => row[key] !== id && row[path] === value[path])) throw new DOMException(`Duplicate ${path}.`, 'ConstraintError');
                }
                rows.set(id, structuredClone(value)); return id;
              },
              async delete(store, key) { writable(); scope(store).delete(key); },
              async all(store) { return [...scope(store).values()].map(row => structuredClone(row)); },
              async keys(store) { return [...scope(store).keys()]; },
              async index(store, index, value) {
                const path = opened.stores[store].indexes[index].path;
                return [...scope(store).values()].filter(row => row[path] === value).map(row => structuredClone(row));
              },
            };
            const result = await work(ops);
            if (mode === 'readwrite') for (const [store, rows] of draft) data.set(store, rows);
            return result;
          };
          const pending = queue.then(run); queue = pending.catch(() => {}); return pending;
        },
        close() {},
      };
    },
  };
}
