import { isAppURL } from '../core/config.js';
import { cid } from '../core/cid.js';

export function acceptScannedText(input, { config, registry = [], urlState }) {
  const value = String(input).trim();
  // Only a bare CID is loaded without checking which application a URL belongs to.
  const bare = cid(value, []);
  if (bare) return { kind: 'cid', cid: bare };
  if (isAppURL(value, config)) return { kind: 'app', href: value, intent: urlState.parse(value) };
  const sibling = registry.find(app => isAppURL(value, app));
  if (sibling) return { kind: 'sibling', href: value, name: sibling.name };
  return { kind: 'text', text: String(input) };
}
