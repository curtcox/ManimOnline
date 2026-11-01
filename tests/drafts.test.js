const test = require('node:test'), assert = require('node:assert/strict');
const LocalDrafts = require('../src/local-drafts.js');
const document = src => ({ src, files: { 'data.txt': 'input' }, settings: { enabled: false } });
const memory = () => { const values = new Map(); return { getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value) }; };
test('opening and running a link leaves saved work intact; editing retains previous documents', () => {
 const storage = memory(), drafts = new LocalDrafts({ storage, key: 'work' });
 drafts.save(document('original'), true); drafts.opened(); drafts.save(document('link'));
 assert.deepEqual(drafts.list(), [document('original')]);
 drafts.save(document('edited link'), true); drafts.save(document('continued edit'));
 assert.deepEqual(new LocalDrafts({ storage, key: 'work' }).list(), [document('continued edit'), document('original')]);
});
test('quota and unavailable storage cannot destroy prior drafts', () => {
 const storage = memory(), drafts = new LocalDrafts({ storage, key: 'work' }); drafts.save(document('original'), true); drafts.opened();
 storage.setItem = () => { throw Error('Quota'); };
 assert.throws(() => drafts.save(document('new'), true), /Quota/); assert.deepEqual(drafts.list(), [document('original')]);
 assert.throws(() => new LocalDrafts({ key: 'work' }).save(document('new'), true), /unavailable/);
});
