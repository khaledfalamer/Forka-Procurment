/**
 * Forka Procurement Planner — Google Sheet backend.
 * Paste this into Extensions → Apps Script of a new Google Sheet, then Deploy → New deployment → Web app
 * (Execute as: Me · Who has access: Anyone). Copy the web app URL into config.js.
 * Team PIN (required): Project Settings → Script properties → add PIN = your code. Without it nobody can save.
 */
const SHEET_NAME = 'Planner';
const HEAD = ['Ref', 'Item', 'Concept', 'Category', 'Supplier', 'Payment', 'Use / month', 'PAR', 'Stock now',
  'Unit price', 'Price per', 'Pack qty', 'Pack unit', 'To buy', 'Budget AED', 'Status', 'Filled by', 'Updated', 'data (do not edit)'];

function sheet_() {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) sh = ss.insertSheet(SHEET_NAME);
  if (sh.getLastRow() === 0) {
    sh.appendRow(HEAD);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, HEAD.length).setFontWeight('bold');
  }
  return sh;
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  const sh = sheet_();
  const n = sh.getLastRow() - 1;
  const lines = {};
  if (n > 0) {
    const v = sh.getRange(2, 1, n, HEAD.length).getValues();
    v.forEach(r => {
      if (!r[0]) return;
      try { lines[r[0]] = JSON.parse(r[HEAD.length - 1] || '{}'); } catch (e) {}
    });
  }
  return out_({ ok: true, lines: lines });
}

function writeRow_(sh, id, d, v) {
  const row = [id, v.n || '', v.con || '', v.cat || '', v.sup || '', v.pay || '', v.use, v.par, v.st, v.p, v.u || '',
    v.pkN, v.pkU || '', v.q, v.v, v.status || '', d.who || '', d.at ? new Date(d.at) : new Date(), JSON.stringify(d)];
  const f = sh.getRange('A:A').createTextFinder(id).matchEntireCell(true).findNext();
  if (f && f.getRow() > 1) sh.getRange(f.getRow(), 1, 1, row.length).setValues([row]);
  else sh.appendRow(row);
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
    const sh = sheet_();
    items.forEach(it => writeRow_(sh, String(it.id), it.data || {}, it.view || {}));
  } finally {
    lock.releaseLock();
  }
  return out_({ ok: true, saved: items.length });
}
