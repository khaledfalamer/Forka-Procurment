/**
 * Forka Procurement Planner — Google Sheet backend.
 * Paste this into Extensions → Apps Script of a new Google Sheet, then Deploy → New deployment → Web app
 * (Execute as: Me · Who has access: Anyone). Copy the web app URL into config.js.
 * Team PIN (required): Project Settings → Script properties → add PIN = your code. Without it nobody can save.
 */
const SHEET_NAME = 'Planner';
const HEAD = ['Ref', 'Item', 'Concept', 'Category', 'Supplier', 'Payment', 'Use / month', 'PAR', 'Stock now',
  'Unit price', 'Price per', 'Pack qty', 'Pack unit', 'To buy', 'Budget AED', 'Status', 'Filled by', 'Updated', 'data (do not edit)'];

const SUP_NAME = 'Suppliers';
const SUP_HEAD = ['Id', 'Supplier', 'Contact person', 'Phone', 'Email', 'Payment terms', 'Credit days', 'Delivery days',
  'Lead time (days)', 'TRN', 'Area / address', 'What they supply', 'Notes', 'Items', 'Month AED', 'Updated by', 'Updated', 'data (do not edit)'];

function sheet_(name, head) {
  name = name || SHEET_NAME; head = head || HEAD;
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  if (sh.getLastRow() === 0) {
    sh.appendRow(head);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, head.length).setFontWeight('bold');
  }
  return sh;
}

function readAll_(name, head) {
  const sh = sheet_(name, head), n = sh.getLastRow() - 1, out = {};
  if (n > 0) sh.getRange(2, 1, n, head.length).getValues().forEach(r => {
    if (!r[0]) return;
    try { out[r[0]] = JSON.parse(r[head.length - 1] || '{}'); } catch (e) {}
  });
  return out;
}

function upsert_(sh, id, row) {
  const f = sh.getRange('A:A').createTextFinder(id).matchEntireCell(true).findNext();
  if (f && f.getRow() > 1) sh.getRange(f.getRow(), 1, 1, row.length).setValues([row]);
  else sh.appendRow(row);
}

function writeSup_(sh, id, d, v) {
  upsert_(sh, id, [id, v.n || d.n || '', v.contact || '', v.phone ? "'" + v.phone : '', v.email || '', v.terms || '', v.days, v.deliv || '',
    v.lead, v.trn ? "'" + v.trn : '', v.area || '', v.supplies || '', v.notes || '', v.items, v.v, d.who || '',
    d.at ? new Date(d.at) : new Date(), JSON.stringify(d)]);
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  return out_({ ok: true, lines: readAll_(SHEET_NAME, HEAD), suppliers: readAll_(SUP_NAME, SUP_HEAD) });
}

function writeRow_(sh, id, d, v) {
  const row = [id, v.n || '', v.con || '', v.cat || '', v.sup || '', v.pay || '', v.use, v.par, v.st, v.p, v.u || '',
    v.pkN, v.pkU || '', v.q, v.v, v.status || '', d.who || '', d.at ? new Date(d.at) : new Date(), JSON.stringify(d)];
  upsert_(sh, id, row);
}

function doPost(e) {
  let b;
  try { b = JSON.parse(e.postData.contents); } catch (err) { return out_({ ok: false, error: 'bad' }); }
  // The PIN is required. With no PIN set in Script properties, nobody can save.
  const pin = PropertiesService.getScriptProperties().getProperty('PIN');
  if (!pin) return out_({ ok: false, error: 'nopin' });
  if (String(b.pin || '') !== pin) return out_({ ok: false, error: 'pin' });
  if (b.check) return out_({ ok: true });
  const items = Array.isArray(b.batch) ? b.batch : [{ id: b.id, data: b.data, view: b.view }];
  const ok = /^[A-Za-z0-9_\-.~:@+]{1,60}$/;
  if (!items.length || items.length > 500 || items.some(it => !ok.test(String(it.id || '')))) return out_({ ok: false, error: 'id' });
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const sh = sheet_(), ss = sheet_(SUP_NAME, SUP_HEAD);
    items.forEach(it => it.kind === 'sup'
      ? writeSup_(ss, String(it.id), it.data || {}, it.view || {})
      : writeRow_(sh, String(it.id), it.data || {}, it.view || {}));
  } finally {
    lock.releaseLock();
  }
  return out_({ ok: true, saved: items.length });
}
