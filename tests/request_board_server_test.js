// "Open in Board" on the Procurement server: Code.gs run against pretend Google services (no live servers).
// node tests/request_board_server_test.js
const fs = require('fs'), vm = require('vm'), path = require('path');
class Range {
  constructor(sh, r, c, nr, nc) { Object.assign(this, { sh, r, c, nr, nc }); }
  getValues() { const o = []; for (let i = 0; i < this.nr; i++) { const row = []; for (let j = 0; j < this.nc; j++) row.push((this.sh.d[this.r - 1 + i] || [])[this.c - 1 + j] ?? ''); o.push(row); } return o; }
  getValue() { return this.getValues()[0][0]; }
  setValues(v) { v.forEach((row, i) => { const R = this.sh.d[this.r - 1 + i] = this.sh.d[this.r - 1 + i] || []; row.forEach((x, j) => R[this.c - 1 + j] = x); }); return this; }
  setValue(v) { return this.setValues([[v]]); }
  setFontWeight() { return this; } setNumberFormat() { return this; }
  createTextFinder(t) { const sh = this.sh; return { matchEntireCell() { return this; }, findNext: () => { const i = sh.d.findIndex(r => String(r[0]) === String(t)); return i < 0 ? null : { getRow: () => i + 1 }; } }; }
}
class Sheet {
  constructor(n) { this.n = n; this.d = []; }
  getName() { return this.n; } getLastRow() { return this.d.length; } getLastColumn() { return Math.max(0, ...this.d.map(r => r.length)); }
  getRange(r, c, nr, nc) { if (typeof r === 'string') return new Range(this, 1, 1, this.d.length, 1); return new Range(this, r, c, nr || 1, nc || 1); }
  appendRow(r) { this.d.push(r.slice()); } setFrozenRows() {}
  insertColumnBefore(c) { this.d.forEach(r => r.splice(c - 1, 0, '')); }
}
const sheets = {}; const ss = { getSheetByName: n => sheets[n] || null, insertSheet: n => (sheets[n] = new Sheet(n)), getSheets: () => Object.values(sheets) };
const props = { PVER: '1' }, calls = [];
const PEOPLE = { 'TOKBUYER-000000000000000': { name: 'Ali Buyer', email: 'buyer@forka.com', sides: ['plan'] },
  'TOKCHEF-0000000000000000': { name: 'Head Chef', email: 'Chef@Forka.com', sides: ['dept'] },
  'TOKBAR-00000000000000000': { name: 'Bar Lead', email: 'bar@forka.com', sides: ['dept'] },
  'TOKCEO-00000000000000000': { name: 'Khaled', email: 'khaled@forka.com', sides: ['plan', 'ops', 'dept', 'fin', 'ceo', 'oman'] } };
let boardsAnswer = null;
const ctx = {
  SpreadsheetApp: { getActive: () => ss },
  PropertiesService: { getScriptProperties: () => ({ getProperty: k => props[k] ?? null, setProperty: (k, v) => { props[k] = v; } }) },
  CacheService: { getScriptCache: () => ({ put() {}, get: () => null, remove() {} }) },
  LockService: { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) },
  ContentService: { createTextOutput: t => ({ setMimeType() { return this; }, t }), MimeType: { JSON: 1 } },
  UrlFetchApp: { fetch: (u, o) => { const b = JSON.parse(o.payload); calls.push({ u, b });
    if (/accounts$/.test(u)) { const p = PEOPLE[b.token]; return { getContentText: () => JSON.stringify(p ? { ok: true, me: Object.assign({ apps: { proc: true } }, p) } : { ok: false }) }; }
    return { getContentText: () => JSON.stringify(boardsAnswer(b)) }; } },
  MailApp: { sendEmail() {} }, Utilities: {}, console, Date, JSON, Math
};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(__dirname, '../Code.gs'), 'utf8') + ';this.doPost=doPost;', ctx);
const call = o => JSON.parse(ctx.doPost({ postData: { contents: JSON.stringify(o) } }).t);
const res = []; const ck = (n, ok, i) => { res.push(!!ok); console.log((ok ? 'PASS ' : 'FAIL ') + n + (ok ? '' : ' - ' + String(JSON.stringify(i)).slice(0, 300))); };

// the Requests tab and the Users tab (contacts, to find the buyer's email from the name on the request)
const rq = ss.insertSheet('Requests'); rq.d = [['Id', 'Updated by', 'Updated', 'data (do not edit)']];
const R1 = { no: 'PRQ-261114-01', title: 'Menu board logo', kind: 'design', dept: 'mkt', branch: 'sharjah', qty: 1, unit: 'PCS', needBy: '2026-11-20', details: 'Need the logo files', by: 'Head Chef', byEmail: 'chef@forka.com', buyer: 'Ali Buyer', status: 'review', log: [{ type: 'status', text: 'new' }] };
rq.d.push(['R-1', 'Head Chef', new Date(), JSON.stringify(R1)]);
const us = ss.insertSheet('Users'); us.d = [['Name', 'PIN', 'Can open', 'Email', 'WhatsApp', 'Alerts', 'Active'], ['Ali Buyer', '', 'plan', 'Buyer@Forka.com', '', '', true]];
ss.insertSheet('Activity').d = [['When', 'Who', 'Page', 'Record', 'Id', 'What changed']];
const recR1 = () => JSON.parse(rq.d.find(r => r[0] === 'R-1')[3]);
const ask = (tok, side, id) => call({ erp: tok, side, boardCard: id || 'R-1' });
let n0;

boardsAnswer = () => ({ ok: true, cardId: 'cXYZ1', boardId: 'bPR', url: 'https://erp.forka.com/boards/#card=cXYZ1' });
n0 = calls.length;
ck('Not set up yet (no PROC_BOARD_KEY): a clear "nosetup" answer and the Boards server is not called', ask('TOKBUYER-000000000000000', 'plan').error === 'nosetup' && !calls.slice(n0).some(c => /macros/.test(c.u)));
props.PROC_BOARD_KEY = 'test-key-0123456789-abcdefghij';
ck('Someone from another department (not Purchasing, not CEO, not the requester) is refused', ask('TOKBAR-00000000000000000', 'dept').error === 'role');
ck('A side the person does not have is refused by the sign-in check', ask('TOKBAR-00000000000000000', 'plan').error === 'side');
ck('No sign-in: refused', call({ boardCard: 'R-1' }).error === 'erp');
ck('A request that does not exist', ask('TOKBUYER-000000000000000', 'plan', 'R-404').error === 'gone');
n0 = calls.length;
let r = ask('TOKBUYER-000000000000000', 'plan');
const sent = calls.slice(n0).find(c => /script\.google\.com\/macros/.test(c.u));
ck('Purchasing presses it: the Boards server is asked with action procCard and the key from Script properties', r.ok && sent && sent.b.action === 'procCard' && sent.b.key === props.PROC_BOARD_KEY, [r, sent && sent.b]);
ck('...with the request details, the requester, the buyer (email from the Users tab), the presser and the link back',
  sent.b.req.no === 'PRQ-261114-01' && sent.b.req.title === 'Menu board logo' && sent.b.req.kind === 'Design or creative' && sent.b.req.dept === 'Marketing' && sent.b.req.branch === 'AMK Sharjah'
  && sent.b.req.needBy === '2026-11-20' && sent.b.req.url === 'https://procurement.forka.com/#rq=R-1' && sent.b.requester.email === 'chef@forka.com'
  && sent.b.buyer.email === 'buyer@forka.com' && sent.b.buyer.name === 'Ali Buyer' && sent.b.by.email === 'buyer@forka.com', sent.b);
let d = recR1();
ck('The card is kept on the request (boardCard) and a note is added: "Board card opened by ..."', d.boardCard.id === 'cXYZ1' && d.boardCard.url === 'https://erp.forka.com/boards/#card=cXYZ1' && d.log.filter(e => e.type === 'board').length === 1 && /Board card opened by Ali Buyer/.test(d.log[d.log.length - 1].text) && r.url === d.boardCard.url && r.rec.boardCard.id === 'cXYZ1', d);
ck('The Activity tab records it', sheets.Activity.d.length === 2 && /boardCard/.test(sheets.Activity.d[1][5]), sheets.Activity.d[1]);
r = ask('TOKCHEF-0000000000000000', 'dept'); d = recR1();
ck('The requester (matched by email, any letter case) may press it; pressing again adds no second note', r.ok && d.log.filter(e => e.type === 'board').length === 1, [r, d.log]);
ck('The CEO may press it', ask('TOKCEO-00000000000000000', 'ceo').ok);
// a save from the app can never set or remove the card link
const stale = Object.assign({}, R1, { title: 'Menu board logo (A3)' });
call({ erp: 'TOKBUYER-000000000000000', side: 'plan', batch: [{ id: 'R-1', kind: 'Requests', data: stale }] });
d = recR1();
ck('A normal save from the app (without boardCard) keeps the card link', d.title === 'Menu board logo (A3)' && d.boardCard && d.boardCard.id === 'cXYZ1', d);
call({ erp: 'TOKBUYER-000000000000000', side: 'plan', batch: [{ id: 'R-1', kind: 'Requests', data: Object.assign({}, stale, { boardCard: { id: 'cEVIL' } }) }] });
ck('...and a save cannot change it either', recR1().boardCard.id === 'cXYZ1');
call({ erp: 'TOKBUYER-000000000000000', side: 'plan', batch: [{ id: 'R-2', kind: 'Requests', data: Object.assign({}, R1, { no: 'PRQ-2', boardCard: { id: 'cEVIL' } }) }] });
ck('A new request saved from the app cannot bring its own card link', !JSON.parse(rq.d.find(x => x[0] === 'R-2')[3]).boardCard);
boardsAnswer = () => ({ ok: false, error: 'key' });
ck('Keys that do not match on the two servers: shown as "not set up yet"', ask('TOKBUYER-000000000000000', 'plan', 'R-2').error === 'nosetup');
boardsAnswer = () => { throw new Error('down'); };
ck('Boards server down: a clear error, nothing stored', ask('TOKBUYER-000000000000000', 'plan', 'R-2').error === 'board' && !JSON.parse(rq.d.find(x => x[0] === 'R-2')[3]).boardCard);
ck('The key is never in Code.gs', !/test-key-0123/.test(fs.readFileSync(path.join(__dirname, '../Code.gs'), 'utf8')) && /getProperty\('PROC_BOARD_KEY'\)/.test(fs.readFileSync(path.join(__dirname, '../Code.gs'), 'utf8')));

console.log(`${res.filter(Boolean).length}/${res.length} request Board server checks passed`);
process.exit(res.every(Boolean) ? 0 : 1);
