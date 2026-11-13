import { loadContent } from '../../core/content.js';
import { cid as parseCID } from '../../core/cid.js';
import { text } from '../../core/bytes.js';
import { parseSuite } from './suite.js';
import { parseReport } from './report.js';
async function load(value, options) {
  const cid = parseCID(value, options.allowedHosts ?? ['256t.us', '256t.org', 'hashbin.org']);
  if (!cid) throw new Error('Enter a valid evaluation CID or saved link.');
  return text(await loadContent(cid, { ...options, maxBytes: 1024 * 1024 }));
}
export const loadSuite = async (value, { type, ...options } = {}) => parseSuite(await load(value, options), type);
export const loadReport = async (value, options = {}) => parseReport(await load(value, options));
