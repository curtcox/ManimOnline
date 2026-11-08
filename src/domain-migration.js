/* eslint-env browser */
const MAX_BYTES = 12 * 1024 * 1024;
const KEYS = { gripeline: ['gripeline:draft', 'gripeline:draft:history'], pages: ['pagesonline:project'], python: ['pythononline:work'], gnuplot: ['gnuplotonline:document'], audio: ['audioonline:document'], upload: ['hashbin:ghpages:registered-app-client-id'], textpad: ['hashbin:textpad:migrated-text'] };

/** Validate an inert draft handoff; credentials and persistence permissions are never transferred. */
export function validateMigration(payload, slug, app) {
  if (!payload || payload.format !== 'hashbin-origin-migration' || payload.version !== 1 || payload.app !== slug || typeof payload.href !== 'string' || !payload.storage || typeof payload.storage !== 'object' || Array.isArray(payload.storage)) throw new Error('This backup belongs to a different app or has an invalid format.');
  if (JSON.stringify(payload).length > MAX_BYTES) throw new Error('This backup exceeds the 12 MiB migration limit.');
  const source = new URL(payload.href), legacy = new URL(app.legacy);
  const aliases = [legacy.origin, ...(slug === 'textpad' ? ['https://www.hashbin.org'] : [])];
  if (!aliases.includes(source.origin)) throw new Error('Unexpected original app address.');
  const allowed = KEYS[slug] || [];
  for (const [key, value] of Object.entries(payload.storage)) {
    if (!allowed.includes(key) || typeof value !== 'string') throw new Error('Only this app’s drafts and public settings can be restored.');
    if (key !== 'hashbin:textpad:migrated-text' && key !== 'hashbin:ghpages:registered-app-client-id') {
      const document = JSON.parse(value);
      if (slug === 'gripeline') {
        const drafts = key.endsWith(':history') ? document : [value];
        if (!Array.isArray(drafts) || drafts.length > 50) throw new Error('Invalid draft history.');
        for (const draft of drafts) {
          if (typeof draft !== 'string') throw new Error('Invalid draft history.');
          const item = JSON.parse(draft);
          if (!item || typeof item.src !== 'string' || Object.keys(item).some(key => !['src', 'pos'].includes(key))) throw new Error('Only diagram source and positions can be moved.');
          if (item.pos && (typeof item.pos !== 'object' || Array.isArray(item.pos) || Object.values(item.pos).some(pair => !Array.isArray(pair) || pair.length !== 2 || pair.some(n => typeof n !== 'number' || !Number.isFinite(n))))) throw new Error('Invalid diagram positions.');
        }
        continue;
      }
      if (!document || typeof document !== 'object' || Array.isArray(document)) throw new Error('A saved document is invalid.');
    }
  }
  return payload;
}

/** Preserve document links without forwarding an old OAuth or Publish callback. */
export function migrationTarget(payload, origin) {
  const source = new URL(payload.href), target = new URL(origin);
  target.search = source.search; target.hash = source.hash;
  for (const key of ['code', 'state', 'error', 'error_description', 'api', 'content', 'client_id', 'dev']) target.searchParams.delete(key);
  if (new URLSearchParams(target.hash.slice(1)).has('hashbin_publish')) target.hash = '';
  if (Object.hasOwn(payload.storage, 'hashbin:textpad:migrated-text')) target.hash = '';
  return target.href;
}

function download(payload) {
  const link = document.createElement('a');
  const url = URL.createObjectURL(new Blob([JSON.stringify(payload)], { type: 'application/json' }));
  link.href = url; link.download = `${payload.app}-work-backup.json`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Offer old-origin transfers in More, or receive an explicitly requested handoff. */
export function bootMigration(apps) {
  const slug = document.body.dataset.migrationApp;
  if (slug) {
    const app = apps[slug], status = document.getElementById('migration-status'), restore = document.getElementById('migration-restore');
    if (!app || location.origin !== app.origin) { status.textContent = 'Open this recovery page on the app’s new address.'; return; }
    const nonce = location.hash.slice(1), opener = window.opener;
    history.replaceState(null, '', location.pathname);
    const old = document.getElementById('migration-old'); old.href = app.legacy;
    document.getElementById('migration-app').textContent = app.origin;
    let payload = null;
    const accept = value => {
      try { payload = validateMigration(value, slug, app); status.textContent = `Ready to restore ${Object.keys(payload.storage).length} saved document or setting(s). The old copy is kept. This replaces saved work at the new address.`; restore.disabled = false; }
      catch (error) { payload = null; restore.disabled = true; status.textContent = error.message; }
    };
    const receive = event => {
      const allowed = [new URL(app.legacy).origin, ...(slug === 'textpad' ? ['https://www.hashbin.org'] : [])];
      if (event.source !== opener || !allowed.includes(event.origin) || event.data?.type !== 'hashbin:migration' || event.data.nonce !== nonce) return;
      removeEventListener('message', receive); accept(event.data.payload);
    };
    addEventListener('message', receive);
    if (opener && /^[a-f0-9-]{36}$/.test(nonce)) {
      const message = { type: 'hashbin:migration-ready', nonce };
      opener.postMessage(message, new URL(app.legacy).origin);
      if (slug === 'textpad') opener.postMessage(message, 'https://www.hashbin.org');
    }
    document.getElementById('migration-file').onchange = async event => {
      try { const file = event.target.files[0]; if (!file) return; if (file.size > MAX_BYTES) throw new Error('Backup exceeds 12 MiB.'); accept(JSON.parse(await file.text())); }
      catch (error) { payload = null; restore.disabled = true; status.textContent = error.message; }
    };
    document.getElementById('migration-download').onclick = () => { if (payload) download(payload); };
    restore.onclick = () => {
      if (!payload) return;
      try {
        for (const [key, value] of Object.entries(payload.storage)) (slug === 'textpad' ? sessionStorage : localStorage).setItem(key, value);
        // Imported Python never inherits permission to open its saved filesystem.
        if (slug === 'python') localStorage.setItem('pythononline:persistent-home', 'false');
        window.opener = null; location.replace(migrationTarget(payload, app.origin));
      } catch (_) { status.textContent = 'Browser storage is unavailable or full. Download the backup, then try in a browser with storage available.'; }
    };
    return;
  }
  const match = Object.entries(apps).find(([, app]) => {
    const legacy = new URL(app.legacy);
    const origin = location.origin === legacy.origin || (legacy.hostname === 'hashbin.org' && location.origin === 'https://www.hashbin.org');
    const path = legacy.pathname.endsWith('/') ? location.pathname.startsWith(legacy.pathname) : location.pathname.replace(/\.html$/, '') === legacy.pathname.replace(/\.html$/, '');
    return origin && path;
  });
  if (!match) return;
  const [name, app] = match;
  const snapshot = () => {
    const storage = {};
    for (const key of KEYS[name] || []) {
      const value = name === 'textpad' ? document.getElementById('editor')?.value : localStorage.getItem(key);
      if (typeof value === 'string') storage[key] = value;
    }
    return validateMigration({ format: 'hashbin-origin-migration', version: 1, app: name, href: location.href, storage }, name, app);
  };
  const notice = document.createElement('details');
  const summary = document.createElement('summary'); summary.textContent = 'Move saved work'; notice.append(summary);
  const destination = document.createElement('p'); destination.textContent = `Copy drafts to ${new URL(app.origin).hostname}, or keep a backup file.`; notice.append(destination);
  const move = document.createElement('button'); move.textContent = 'Move saved work'; notice.append(move);
  const backup = document.createElement('button'); backup.textContent = 'Download backup'; backup.style.marginLeft = '8px'; notice.append(backup);
  const problem = document.createElement('p'); problem.setAttribute('role', 'status'); notice.append(problem);
  backup.onclick = () => { try { download(snapshot()); } catch (error) { problem.textContent = error.message; } };
  move.onclick = () => {
    let payload; try { payload = snapshot(); } catch (error) { problem.textContent = error.message; return; }
    const nonce = crypto.randomUUID(), popup = window.open(`${app.origin}/migration.html#${nonce}`, '_blank');
    if (!popup) { problem.textContent = 'Allow popups to move saved work, or download a backup and open the new address.'; return; }
    const receive = event => {
      if (event.source !== popup || event.origin !== app.origin || event.data?.type !== 'hashbin:migration-ready' || event.data.nonce !== nonce) return;
      removeEventListener('message', receive); popup.postMessage({ type: 'hashbin:migration', nonce, payload }, app.origin);
    };
    addEventListener('message', receive);
    setTimeout(() => removeEventListener('message', receive), 120000);
  };
  // Recovery remains available on demand; working editors get no migration overlay.
  const mount = () => {
    const menu = document.querySelector('#fk-more-drawer .fk-dialog-body');
    if (!menu) return;
    menu.append(notice); document.removeEventListener('click', mount, true);
  };
  mount();
  if (!notice.isConnected) document.addEventListener('click', mount, true);
}

bootMigration({"pages":{"legacy":"https://curtcox.github.io/pages/","origin":"https://pages.hashbin.page"},"python":{"legacy":"https://curtcox.github.io/PythonOnline/","origin":"https://python.hashbin.page"},"manim":{"legacy":"https://curtcox.github.io/ManimOnline/","origin":"https://manim.hashbin.page"},"gnuplot":{"legacy":"https://curtcox.github.io/GnuplotOnline/","origin":"https://gnuplot.hashbin.page"},"sheets":{"legacy":"https://curtcox.github.io/sheets/index.html","origin":"https://sheets.hashbin.page"},"gripeline":{"legacy":"https://curtcox.github.io/gripeline/editor/","origin":"https://gripeline.hashbin.page"},"modl":{"legacy":"https://curtcox.github.io/modl/","origin":"https://modl.hashbin.page"},"diagram":{"legacy":"https://curtcox.github.io/hashbin.org/diagram-oauth.html","origin":"https://diagram.hashbin.page"},"upload":{"legacy":"https://curtcox.github.io/hashbin.org/upload-via-registered-app.html","origin":"https://upload.hashbin.page"},"textpad":{"legacy":"https://hashbin.org/docs/textpad/app","origin":"https://textpad.hashbin.page"},"r":{"legacy":"https://curtcox.github.io/R/","origin":"https://r.hashbin.page"},"livelier":{"legacy":"https://curtcox.github.io/livelier/","origin":"https://livelier.hashbin.page"},"apptron":{"legacy":"https://curtcox.github.io/apptron/","origin":"https://apptron.hashbin.page"},"audio":{"legacy":"https://curtcox.github.io/AudioOnline/","origin":"https://audio.hashbin.page"}});
