/**
 * Forka Procurement — Google Sheet backend v5
 * Personal PINs · activity log · email (and optional WhatsApp) alerts · files saved to Google Drive.
 *
 * HOW TO INSTALL (5 minutes, do it on a COPY of the Sheet first):
 *  1. Extensions → Apps Script → replace all code with this file → Save.
 *  2. Run the function  setup  once (Run ▸ setup). Approve the Google permissions it asks for
 *     (Sheets, Drive, Gmail-send, triggers). It creates the "Users" and "Activity" tabs,
 *     a Drive folder "Forka Procurement Files", and a daily 8:00 payment alert.
 *  3. Fill the "Users" tab — one row per person:
 *        Name | PIN | Can open | Email | WhatsApp | Alerts | Active
 *     Can open: any of  plan, ops, dept, fin, ceo   (comma separated)
 *     Alerts:   any of  request, approval, decision, payments, reply
 *     Active:   TRUE / FALSE
 *     PINs: 4–6 digits, every person different. The app never receives anyone's PIN back.
 *  4. Deploy → Manage deployments → Edit → New version → Deploy (same web-app URL, no change in config.js).
 *
 * Until the Users tab has at least one active row, the old team PIN (Script property PIN) still works,
 * so nothing breaks during the switch.
 *
 * Optional WhatsApp (Meta WhatsApp Cloud API — needs a Meta Business account and an approved template):
 *   Script properties: WA_TOKEN, WA_PHONE_ID, WA_TEMPLATE (template with one {{1}} body variable), WA_LANG (e.g. en)
 *   If these are empty, alerts go by email only.
 */
const DATA_COL = 'data (do not edit)';
const SHEETS = { line: 'Planner', sup: 'Suppliers' };
const PRIVATE_TABS = ['Users', 'Activity'];
const LABELS = {
  Planner: { id: 'Ref', n: 'Item', con: 'Concept', cat: 'Category', sup: 'Supplier', pay: 'Payment', use: 'Use / month', par: 'PAR',
    st: 'Stock now', p: 'Unit price', u: 'Price per', pkN: 'Pack qty', pkU: 'Pack unit', q: 'To buy', v: 'Budget AED', status: 'Status' },
  Suppliers: { id: 'Id', n: 'Supplier', contact: 'Contact person', phone: 'Phone', email: 'Email', terms: 'Payment terms', days: 'Credit days',
    deliv: 'Delivery days', lead: 'Lead time (days)', trn: 'TRN', area: 'Area / address', supplies: 'What they supply', notes: 'Notes',
    items: 'Items', v: 'Month AED' }
};
const TEXT_KEYS = ['phone', 'trn'];
const SIDES = ['plan', 'ops', 'dept', 'fin', 'ceo'];
const MAX_TRIES = 15;            // wrong PINs in a row → logins locked 10 minutes

function out_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
function props_() { return PropertiesService.getScriptProperties(); }

/* ---------------- setup ---------------- */
function setup() {
  const ss = SpreadsheetApp.getActive();
  let u = ss.getSheetByName('Users');
  if (!u) {
    u = ss.insertSheet('Users');
    u.appendRow(['Name', 'PIN', 'Can open', 'Email', 'WhatsApp', 'Alerts', 'Active']);
    u.appendRow(['Khaled', '', 'plan, ops, dept, fin, ceo', 'ceo@forka.com', '', 'approval, payments', true]);
    u.setFrozenRows(1); u.getRange(1, 1, 1, 7).setFontWeight('bold');
    u.getRange('B:B').setNumberFormat('@');
  }
  let a = ss.getSheetByName('Activity');
  if (!a) { a = ss.insertSheet('Activity'); a.appendRow(['When', 'Who', 'Page', 'Record', 'Id', 'What changed']); a.setFrozenRows(1); a.getRange(1, 1, 1, 6).setFontWeight('bold'); }
  folder_();
  ScriptApp.getProjectTriggers().filter(t => t.getHandlerFunction() === 'dailyPayments').forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('dailyPayments').timeBased().everyDays(1).atHour(8).inTimezone('Asia/Dubai').create();
  return 'Done. Now fill the Users tab (PIN column) and deploy a new version.';
}

/* ---------------- people ---------------- */
function contacts_() {          // everyone listed in the Users tab (for alerts), PIN or not
  const sh = SpreadsheetApp.getActive().getSheetByName('Users');
  if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, 7).getValues().map(r => ({
    name: String(r[0]).trim(), sides: String(r[2]).toLowerCase().split(/[,\s]+/).filter(Boolean),
    email: String(r[3]).trim(), wa: String(r[4]).replace(/[^\d+]/g, ''),
    alerts: String(r[5]).toLowerCase().split(/[,\s]+/).filter(Boolean)
  })).filter(x => x.name);
}
function users_() {
  const sh = SpreadsheetApp.getActive().getSheetByName('Users');
  if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, 7).getValues().map(r => ({
    name: String(r[0]).trim(), pin: String(r[1]).trim(),
    sides: String(r[2]).toLowerCase().split(/[,\s]+/).filter(Boolean),
    email: String(r[3]).trim(), wa: String(r[4]).replace(/[^\d+]/g, ''),
    alerts: String(r[5]).toLowerCase().split(/[,\s]+/).filter(Boolean),
    active: r[6] === true || String(r[6]).toUpperCase() === 'TRUE'
  })).filter(x => x.name && x.pin && x.active);
}
function locked_() { const until = +props_().getProperty('LOCK_UNTIL') || 0; return Date.now() < until; }
function fail_() {
  const p = props_(); const n = (+p.getProperty('FAILS') || 0) + 1;
  if (n >= MAX_TRIES) { p.setProperty('LOCK_UNTIL', String(Date.now() + 10 * 60000)); p.setProperty('FAILS', '0'); }
  else p.setProperty('FAILS', String(n));
}
// Returns {name, sides} or an error code.
/* ---------------- sign-in through erp.forka.com ---------------- */
// People sign in once at erp.forka.com (Google email or Forka Apps PIN). The app passes that sign-in here,
// and this server asks the Forka Apps accounts server who it is and which Procurement sections they may open.
const ERP_ACCOUNTS_URL = 'https://script.google.com/macros/s/AKfycbwUO5mC1oZrKiSJfF-kpeIFUPjfzB5VToNVn9EH-ecmDadFs9xsU1oDFHTgJ2FSg6vP/exec';
const ERP_ONLY = true;           // true = Procurement PINs are switched off; sign-in only through erp.forka.com
function erpWho_(tok) {
  tok = String(tok || '');
  if (!/^[A-Za-z0-9-]{20,120}$/.test(tok)) return { error: 'erp' };
  const cache = CacheService.getScriptCache(), k = 'erp:' + tok, hit = cache.get(k);
  let me = hit ? JSON.parse(hit) : null;
  if (!me) {
    const r = UrlFetchApp.fetch(ERP_ACCOUNTS_URL, { method: 'post', contentType: 'text/plain', payload: JSON.stringify({ action: 'me', token: tok }), muteHttpExceptions: true, followRedirects: true });
    let j = {}; try { j = JSON.parse(r.getContentText()); } catch (e) { return { error: 'erp' }; }
    if (!j.ok || !j.me) return { error: 'erp' };
    if (!(j.me.apps && j.me.apps.proc)) return { error: 'noproc' };
    me = { name: j.me.name, email: j.me.email, sides: (j.me.sides || []).filter(x => SIDES.indexOf(x) >= 0) };
    cache.put(k, JSON.stringify(me), 300);          // re-checked with Forka Apps every 5 minutes
  }
  return me;
}

function who_(pin, side, erp) {
  if (erp) {
    const me = erpWho_(erp);
    if (me.error) return me;
    if (side && me.sides.indexOf(side) < 0) return { error: 'side' };
    return me;
  }
  if (ERP_ONLY) return { error: 'erp' };
  if (locked_()) return { error: 'locked' };
  const U = users_();
  if (!U.length) {                                    // transition: old team PIN
    const team = props_().getProperty('PIN');
    if (!team) return { error: 'nopin' };
    if (String(pin || '') !== team) { fail_(); return { error: 'pin' }; }
    return { name: '', sides: SIDES.slice(), team: true };
  }
  const u = U.find(x => x.pin === String(pin || ''));
  if (!u) { fail_(); return { error: 'pin' }; }
  props_().setProperty('FAILS', '0');
  if (side && u.sides.indexOf(side) < 0) return { error: 'side' };
  return { name: u.name, sides: u.sides };
}

/* ---------------- sheets ---------------- */
function sheetName_(kind) {
  if (!kind || kind === 'line') return SHEETS.line;
  if (SHEETS[kind]) return SHEETS[kind];
  const n = String(kind).replace(/[^A-Za-z0-9 _-]/g, '').slice(0, 40) || 'Other';
  return PRIVATE_TABS.indexOf(n) >= 0 ? 'Other' : n;
}
function sheet_(name) {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  if (sh.getLastRow() === 0) {
    const lab = LABELS[name] || {};
    sh.appendRow([lab.id || 'Id', 'Updated by', 'Updated', DATA_COL]);
    sh.setFrozenRows(1); sh.getRange(1, 1, 1, 4).setFontWeight('bold');
  }
  return sh;
}
function header_(sh) { return sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(String); }
function readAll_(sh) {
  const head = header_(sh), dc = head.indexOf(DATA_COL), n = sh.getLastRow() - 1, out = {};
  if (dc < 0 || n < 1) return out;
  sh.getRange(2, 1, n, head.length).getValues().forEach(r => { if (!r[0]) return; try { out[r[0]] = JSON.parse(r[dc] || '{}'); } catch (e) {} });
  return out;
}
function readOne_(sh, id) {
  const head = header_(sh), dc = head.indexOf(DATA_COL);
  const f = sh.getRange('A:A').createTextFinder(id).matchEntireCell(true).findNext();
  if (!f || f.getRow() < 2 || dc < 0) return null;
  try { return JSON.parse(sh.getRange(f.getRow(), dc + 1).getValue() || '{}'); } catch (e) { return null; }
}
function loadAll_(me) {
  const tabs = {};
  SpreadsheetApp.getActive().getSheets().forEach(sh => {
    const n = sh.getName();
    if (n === 'Users') return;
    if (n === 'Activity') { if (me.sides.indexOf('ceo') >= 0) tabs.Activity = activity_(); return; }
    if (sh.getLastRow() > 0 && header_(sh).indexOf(DATA_COL) >= 0) tabs[n] = readAll_(sh);
  });
  if (me.sides.indexOf('ceo') >= 0) tabs.People = (ERP_ONLY ? contacts_() : users_()).map(u => ({ name: u.name, sides: u.sides, email: u.email, wa: u.wa, alerts: u.alerts }));
  return { ok: true, me: me, lines: tabs[SHEETS.line] || {}, suppliers: tabs[SHEETS.sup] || {}, tabs: tabs };
}
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
  keys.forEach(k => col_(sh, head, lab[k] || k));
  col_(sh, head, 'Updated'); col_(sh, head, DATA_COL);
  const idx = l => head.indexOf(l);
  const f = sh.getRange('A:A').createTextFinder(id).matchEntireCell(true).findNext();
  const rowN = f && f.getRow() > 1 ? f.getRow() : sh.getLastRow() + 1;
  const row = rowN <= sh.getLastRow() ? sh.getRange(rowN, 1, 1, head.length).getValues()[0] : new Array(head.length).fill('');
  keys.forEach(k => {
    let x = v[k];
    if (x === null || x === undefined) x = '';
    if (typeof x === 'object') x = JSON.stringify(x);
    if (TEXT_KEYS.indexOf(k) >= 0 && x !== '') x = "'" + x;
    let s = String(x); if (s.length > 45000) x = s.slice(0, 45000);
    row[idx(lab[k] || k)] = x;
  });
  row[0] = id;
  const by = head.findIndex(h => h === 'Updated by' || h === 'Filled by');
  if (by >= 0) row[by] = d.who || '';
  row[idx('Updated')] = d.at ? new Date(d.at) : new Date();
  row[idx(DATA_COL)] = JSON.stringify(d);
  sh.getRange(rowN, 1, 1, head.length).setValues([row]);
}

/* Batch save: one read and one write per tab, however many rows.
   Keeps "Filled by" when a save only confirms/unconfirms (adds "Confirmed by"). */
const META_KEYS = ['who', 'at', 'log', 'uid', 'ok', 'stAt'];
function onlyConfirm_(oldD, d) {
  if (!oldD) return false;
  const keys = {}; Object.keys(oldD).concat(Object.keys(d)).forEach(k => keys[k] = 1);
  return Object.keys(keys).every(k => META_KEYS.indexOf(k) >= 0 || JSON.stringify(oldD[k]) === JSON.stringify(d[k]));
}
function writeMany_(sh, list) {           // list: [{id, d, v}]  ->  returns [{id, old, d}]
  const lab = LABELS[sh.getName()] || {};
  const head = header_(sh);
  const need = {}; list.forEach(x => Object.keys(x.v || {}).forEach(k => need[lab[k] || k] = 1));
  Object.keys(need).forEach(l => col_(sh, head, l));
  col_(sh, head, 'Updated'); col_(sh, head, DATA_COL);
  if (lab.ok !== undefined || sh.getName() === 'Planner') col_(sh, head, 'Confirmed by');
  const idx = l => head.indexOf(l), W = head.length, dc = idx(DATA_COL);
  const by = head.findIndex(h => h === 'Updated by' || h === 'Filled by'), cb = idx('Confirmed by');
  const n = Math.max(0, sh.getLastRow() - 1);
  const rows = n ? sh.getRange(2, 1, n, W).getValues() : [];
  const at = {}; rows.forEach((r, i) => { if (r[0] !== '' && at[r[0]] === undefined) at[String(r[0])] = i; });
  const out = [];
  list.forEach(x => {
    let i = at[x.id], row, old = null;
    if (i === undefined) { row = new Array(W).fill(''); rows.push(row); i = rows.length - 1; at[x.id] = i; }
    else { row = rows[i]; try { old = JSON.parse(row[dc] || '{}'); } catch (e) { old = null; } }
    Object.keys(x.v || {}).forEach(k => {
      let y = x.v[k];
      if (y === null || y === undefined) y = '';
      if (typeof y === 'object') y = JSON.stringify(y);
      if (TEXT_KEYS.indexOf(k) >= 0 && y !== '') y = "'" + y;
      const str = String(y); if (str.length > 45000) y = str.slice(0, 45000);
      row[idx(lab[k] || k)] = y;
    });
    row[0] = x.id;
    const confirmOnly = onlyConfirm_(old, x.d);
    if (by >= 0 && !(confirmOnly && row[by])) row[by] = x.d.who || '';
    if (cb >= 0 && old && !!old.ok !== !!x.d.ok) row[cb] = x.d.ok ? (x.d.who || '') : '';
    if (confirmOnly && old && old.who) x.d.who0 = old.who0 || old.who;   // remember who filled it
    row[idx('Updated')] = x.d.at ? new Date(x.d.at) : new Date();
    row[dc] = JSON.stringify(x.d);
    out.push({ id: x.id, old: old, d: x.d });
  });
  if (rows.length) sh.getRange(2, 1, rows.length, W).setValues(rows.map(r => r.length < W ? r.concat(new Array(W - r.length).fill('')) : r.slice(0, W)));
  return out;
}

/* ---------------- activity ---------------- */
function actRow_(me, side, sheetName, id, oldD, newD) {
  const changed = Object.keys(newD || {}).filter(k => ['who', 'at', 'log', 'uid'].indexOf(k) < 0 && JSON.stringify((oldD || {})[k]) !== JSON.stringify(newD[k]));
  let what = changed.slice(0, 10).join(', ');
  if (newD && newD.status && (!oldD || oldD.status !== newD.status)) what = 'status → ' + newD.status + (what ? ' · ' + what : '');
  const label = (newD && (newD.no || newD.n || newD.title)) || '';
  return [new Date(), me.name || '(team PIN)', side || '', sheetName, id + (label ? ' · ' + label : ''), what || 'saved'];
}
function logAct_(me, side, sheetName, id, oldD, newD) {
  const a = SpreadsheetApp.getActive().getSheetByName('Activity'); if (!a) return;
  a.appendRow(actRow_(me, side, sheetName, id, oldD, newD));
}
function activity_() {
  const a = SpreadsheetApp.getActive().getSheetByName('Activity'); if (!a || a.getLastRow() < 2) return [];
  const n = Math.min(300, a.getLastRow() - 1);
  return a.getRange(a.getLastRow() - n + 1, 1, n, 6).getValues().reverse()
    .map(r => ({ at: new Date(r[0]).toISOString(), by: r[1], side: r[2], kind: r[3], label: r[4], fields: [String(r[5])] }));
}

/* ---------------- alerts ---------------- */
function alert_(ev, subject, body, onlyName) {
  const to = (ERP_ONLY ? contacts_() : users_()).filter(u => u.alerts.indexOf(ev) >= 0 && (!onlyName || u.name.toLowerCase() === String(onlyName).toLowerCase()));
  const url = props_().getProperty('APP_URL') || '';
  to.forEach(u => {
    if (u.email) { try { MailApp.sendEmail({ to: u.email, subject: 'Forka Procurement — ' + subject, body: body + (url ? '\n\nOpen the app: ' + url : ''), name: 'Forka Procurement' }); } catch (e) {} }
    if (u.wa) whatsapp_(u.wa, subject + ' — ' + body);
  });
}
function whatsapp_(phone, text) {
  const p = props_(), token = p.getProperty('WA_TOKEN'), pid = p.getProperty('WA_PHONE_ID'), tpl = p.getProperty('WA_TEMPLATE');
  if (!token || !pid || !tpl) return;
  try {
    UrlFetchApp.fetch('https://graph.facebook.com/v20.0/' + pid + '/messages', {
      method: 'post', contentType: 'application/json', muteHttpExceptions: true, headers: { Authorization: 'Bearer ' + token },
      payload: JSON.stringify({ messaging_product: 'whatsapp', to: phone.replace(/^\+/, ''), type: 'template',
        template: { name: tpl, language: { code: p.getProperty('WA_LANG') || 'en' }, components: [{ type: 'body', parameters: [{ type: 'text', text: text.slice(0, 900) }] }] } })
    });
  } catch (e) {}
}
// Called after a Requests record is saved: compares old and new status and alerts the right people.
function requestAlerts_(oldD, d, me) {
  const st = d.status, was = oldD ? oldD.status : null;
  if (st === was) {
    const L = d.log || [], O = (oldD && oldD.log) || [];
    if (L.length > O.length && L[L.length - 1].type === 'msg') alert_('reply', 'Update on your request: ' + (d.title || ''), L[L.length - 1].text || '', d.by);
    return;
  }
  const pick = (d.opts || []).filter(o => o.pick)[0] || {};
  const amt = (+pick.price || 0) * (+d.qty || 1);
  if (st === 'new') alert_('request', 'New request: ' + (d.title || ''), (d.by || '') + ' (' + (d.dept || '') + ') asked for: ' + (d.title || '') + '\n\n' + (d.details || ''));
  if (st === 'approval') alert_('approval', 'Waiting for your approval: ' + (d.title || ''), (d.title || '') + '\nChosen supplier: ' + (pick.sup || '-') + '\nEstimated total: AED ' + amt.toFixed(2) + '\nHandled by: ' + (d.buyer || ''));
  if (st === 'approved') alert_('decision', 'CEO approved: ' + (d.title || ''), 'You can place the order with ' + (pick.sup || 'the chosen supplier') + '.');
  if (was === 'approval' && st === 'quotes') alert_('decision', 'CEO sent back: ' + (d.title || ''), (d.ceo && d.ceo.note) || '');
}
// Daily 8:00 — bills received and not paid, grouped by supplier.
function dailyPayments() {
  const sh = SpreadsheetApp.getActive().getSheetByName('GRN'); if (!sh) return;
  const G = readAll_(sh), by = {};
  Object.keys(G).forEach(id => {
    const g = G[id]; if (g.off || g.status !== 'received') return;
    let v = 0; (g.lines || []).forEach(l => { v += Math.max(0, (+l.recv || 0) - (+l.rej || 0)) * (+l.price || 0); });
    const k = g.sup || '-'; by[k] = by[k] || { n: 0, v: 0 }; by[k].n++; by[k].v += v;
  });
  const keys = Object.keys(by); if (!keys.length) return;
  const total = keys.reduce((s, k) => s + by[k].v, 0);
  const body = keys.sort((a, b) => by[b].v - by[a].v).map(k => '• ' + k + ': ' + by[k].n + ' bill(s), AED ' + by[k].v.toFixed(2)).join('\n');
  alert_('payments', 'Bills received and not paid: AED ' + total.toFixed(2), body + '\n\nOpen Payments → Statements to see the due dates.');
}

/* ---------------- Drive files ---------------- */
function folder_() {
  const p = props_(); let id = p.getProperty('DRIVE_FOLDER_ID');
  if (id) { try { return DriveApp.getFolderById(id); } catch (e) {} }
  const f = DriveApp.createFolder('Forka Procurement Files'); p.setProperty('DRIVE_FOLDER_ID', f.getId()); return f;
}
function upload_(me, u) {
  const okType = /^(image\/(jpeg|png|webp)|application\/pdf)$/.test(String(u.type || ''));
  if (!okType || !u.data) return { ok: false, error: 'type' };
  const bytes = Utilities.base64Decode(u.data);
  if (bytes.length > 4 * 1048576) return { ok: false, error: 'big' };
  const root = folder_(), month = Utilities.formatDate(new Date(), 'Asia/Dubai', 'yyyy-MM');
  const it = root.getFoldersByName(month); const sub = it.hasNext() ? it.next() : root.createFolder(month);
  const name = Utilities.formatDate(new Date(), 'Asia/Dubai', 'yyyyMMdd-HHmm') + ' ' + (me.name || 'team') + ' - ' + String(u.name || 'file').replace(/[\\/:*?"<>|]/g, '').slice(0, 80);
  const file = sub.createFile(Utilities.newBlob(bytes, u.type, name));
  // Anyone with the link can view, so team members without Google accounts can open quotations.
  // To keep files inside your Google Workspace only, set Script property SHARE_DOMAIN_ONLY = true.
  try {
    if (props_().getProperty('SHARE_DOMAIN_ONLY') === 'true') file.setSharing(DriveApp.Access.DOMAIN_WITH_LINK, DriveApp.Permission.VIEW);
    else file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
  } catch (e) {}
  const id = file.getId();
  return { ok: true, id: id, url: 'https://drive.google.com/file/d/' + id + '/view', thumb: 'https://drive.google.com/thumbnail?id=' + id + '&sz=w1200' };
}

/* ---------------- web app ---------------- */
function doGet() {
  if (ERP_ONLY || users_().length) return out_({ ok: false, error: 'login' });   // data only after sign-in
  const tabs = {};
  SpreadsheetApp.getActive().getSheets().forEach(sh => {
    if (PRIVATE_TABS.indexOf(sh.getName()) >= 0) return;
    if (sh.getLastRow() > 0 && header_(sh).indexOf(DATA_COL) >= 0) tabs[sh.getName()] = readAll_(sh);
  });
  return out_({ ok: true, lines: tabs[SHEETS.line] || {}, suppliers: tabs[SHEETS.sup] || {}, tabs: tabs });
}

function doPost(e) {
  let b;
  try { b = JSON.parse(e.postData.contents); } catch (err) { return out_({ ok: false, error: 'bad' }); }
  const me = who_(b.pin, b.side, b.erp);
  if (me.error) return out_({ ok: false, error: me.error });
  if (b.check) return out_({ ok: true, me: { name: me.name, sides: me.sides, role: me.team ? 'team' : 'admin' } });
  if (b.load) return out_(loadAll_(me));
  if (b.upload) return out_(upload_(me, b.upload));

  const items = Array.isArray(b.batch) ? b.batch : [{ id: b.id, data: b.data, view: b.view, kind: b.kind }];
  const okId = /^[A-Za-z0-9_\-.~:@+]{1,60}$/;
  if (!items.length || items.length > 500 || items.some(it => !okId.test(String(it.id || '')))) return out_({ ok: false, error: 'id' });
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  const after = [];
  try {
    const groups = {};
    items.forEach(it => {
      const name = sheetName_(it.kind);
      const d = it.data || {};
      if (!me.team) d.who = me.name;                       // the server decides who saved it
      (groups[name] = groups[name] || []).push({ id: String(it.id), d: d, v: it.view || {} });
    });
    const acts = [];
    Object.keys(groups).forEach(name => {
      writeMany_(sheet_(name), groups[name]).forEach(r => {
        acts.push(actRow_(me, b.side, name, r.id, r.old, r.d));
        if (name === 'Requests') after.push([r.old, r.d]);
      });
    });
    const a = SpreadsheetApp.getActive().getSheetByName('Activity');
    if (a && acts.length) a.getRange(a.getLastRow() + 1, 1, acts.length, 6).setValues(acts);
  } finally {
    lock.releaseLock();
  }
  after.forEach(x => { try { requestAlerts_(x[0], x[1], me); } catch (e) {} });
  return out_({ ok: true, saved: items.length });
}
