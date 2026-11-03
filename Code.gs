/**
 * Forka Procurement Planner — Google Sheet backend (generic, v3).
 * Paste once into Extensions → Apps Script, then Deploy → Manage deployments → Edit → New version.
 * This version adapts by itself: new tabs and new columns are created automatically when the app
 * starts sending them, so future app updates do not need this script to change.
 * Team PIN (required): Project Settings → Script properties → PIN = your code. Without it nobody can save.
 */
const DATA_COL = 'data (do not edit)';
const SHEETS = { line: 'Planner', sup: 'Suppliers' };
const LABELS = {
  Planner: { id: 'Ref', n: 'Item', con: 'Concept', cat: 'Category', sup: 'Supplier', pay: 'Payment', use: 'Use / month', par: 'PAR',
    st: 'Stock now', p: 'Unit price', u: 'Price per', pkN: 'Pack qty', pkU: 'Pack unit', q: 'To buy', v: 'Budget AED', status: 'Status' },
  Suppliers: { id: 'Id', n: 'Supplier', contact: 'Contact person', phone: 'Phone', email: 'Email', terms: 'Payment terms', days: 'Credit days',
    deliv: 'Delivery days', lead: 'Lead time (days)', trn: 'TRN', area: 'Area / address', supplies: 'What they supply', notes: 'Notes',
    items: 'Items', v: 'Month AED' }
};
const TEXT_KEYS = ['phone', 'trn'];   // kept as text so Sheets doesn't turn them into numbers

function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

function sheetName_(kind) {
  if (!kind || kind === 'line') return SHEETS.line;
  if (SHEETS[kind]) return SHEETS[kind];
  return String(kind).replace(/[^A-Za-z0-9 _-]/g, '').slice(0, 40) || 'Other';
}

function sheet_(name) {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  if (sh.getLastRow() === 0) {
    const lab = LABELS[name] || {};
    sh.appendRow([lab.id || 'Id', 'Updated by', 'Updated', DATA_COL]);
    sh.setFrozenRows(1);
    sh.getRange(1, 1, 1, 4).setFontWeight('bold');
  }
  return sh;
}

function header_(sh) { return sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(String); }

function readAll_(sh) {
  const head = header_(sh), dc = head.indexOf(DATA_COL), n = sh.getLastRow() - 1, out = {};
  if (dc < 0 || n < 1) return out;
  sh.getRange(2, 1, n, head.length).getValues().forEach(r => {
    if (!r[0]) return;
    try { out[r[0]] = JSON.parse(r[dc] || '{}'); } catch (e) {}
  });
  return out;
}

function doGet() {
  const tabs = {};
  SpreadsheetApp.getActive().getSheets().forEach(sh => {
    if (sh.getLastRow() > 0 && header_(sh).indexOf(DATA_COL) >= 0) tabs[sh.getName()] = readAll_(sh);
  });
  return out_({ ok: true, lines: tabs[SHEETS.line] || {}, suppliers: tabs[SHEETS.sup] || {}, tabs: tabs });
}

// Finds the column for a label, adding it before the "Updated by" column when it's new.
function col_(sh, head, label) {
  let i = head.indexOf(label);
  if (i >= 0) return i;
  let at = head.findIndex(h => h === 'Updated by' || h === 'Filled by');
  if (at < 0) at = head.length;
  sh.insertColumnBefore(at + 1);
  sh.getRange(1, at + 1).setValue(label).setFontWeight('bold');
  head.splice(at, 0, label);
  return at;
}

function write_(sh, id, d, v) {
  const lab = LABELS[sh.getName()] || {};
  const head = header_(sh);
  const keys = Object.keys(v || {});
  keys.forEach(k => col_(sh, head, lab[k] || k));          // 1) make sure every column exists
  col_(sh, head, 'Updated'); col_(sh, head, DATA_COL);
  const idx = l => head.indexOf(l);                        // 2) then look positions up
  const f = sh.getRange('A:A').createTextFinder(id).matchEntireCell(true).findNext();
  const rowN = f && f.getRow() > 1 ? f.getRow() : sh.getLastRow() + 1;
  const row = rowN <= sh.getLastRow() ? sh.getRange(rowN, 1, 1, head.length).getValues()[0] : new Array(head.length).fill('');
  keys.forEach(k => {
    let x = v[k];
    if (x === null || x === undefined) x = '';
    if (typeof x === 'object') x = JSON.stringify(x);
    if (TEXT_KEYS.indexOf(k) >= 0 && x !== '') x = "'" + x;
    row[idx(lab[k] || k)] = x;
  });
  row[0] = id;
  const by = head.findIndex(h => h === 'Updated by' || h === 'Filled by');
  if (by >= 0) row[by] = d.who || '';
  row[idx('Updated')] = d.at ? new Date(d.at) : new Date();
  row[idx(DATA_COL)] = JSON.stringify(d);
  sh.getRange(rowN, 1, 1, head.length).setValues([row]);
}

function doPost(e) {
  let b;
  try { b = JSON.parse(e.postData.contents); } catch (err) { return out_({ ok: false, error: 'bad' }); }
  const pin = PropertiesService.getScriptProperties().getProperty('PIN');
  if (!pin) return out_({ ok: false, error: 'nopin' });
  if (String(b.pin || '') !== pin) return out_({ ok: false, error: 'pin' });
  if (b.check) return out_({ ok: true });
  const items = Array.isArray(b.batch) ? b.batch : [{ id: b.id, data: b.data, view: b.view, kind: b.kind }];
  const okId = /^[A-Za-z0-9_\-.~:@+]{1,60}$/;
  if (!items.length || items.length > 500 || items.some(it => !okId.test(String(it.id || '')))) return out_({ ok: false, error: 'id' });
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const cache = {};
    items.forEach(it => {
      const name = sheetName_(it.kind);
      const sh = cache[name] || (cache[name] = sheet_(name));
      write_(sh, String(it.id), it.data || {}, it.view || {});
    });
  } finally {
    lock.releaseLock();
  }
  return out_({ ok: true, saved: items.length });
}
