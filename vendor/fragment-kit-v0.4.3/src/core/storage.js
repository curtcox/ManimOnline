/** Storage-shaped facade. Reads degrade to null; failed writes throw for draft recovery. */
export function createStorage({ prefix, storage, kind = 'localStorage', onError = () => {} }) {
  if (typeof prefix !== 'string' || !/^[\w.-]+:?$/.test(prefix)) throw new Error('An app storage prefix is required.');
  const namespace = prefix.replace(/:$/, '') + ':';
  function backend() {
    try { return storage ?? globalThis[kind]; } catch (error) { onError(error); return null; }
  }
  return Object.freeze({
    prefix: namespace,
    getItem(key) { try { return backend()?.getItem(namespace + key) ?? null; } catch (error) { onError(error); return null; } },
    setItem(key, value) {
      try { const target = backend(); if (!target) throw new Error('Browser storage is unavailable.'); target.setItem(namespace + key, String(value)); }
      catch (error) { onError(error); throw error; }
    },
    removeItem(key) { try { backend()?.removeItem(namespace + key); } catch (error) { onError(error); } },
  });
}
