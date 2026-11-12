/* Forka suite: shared header, app switcher, module menu with "More", phone drawer and bottom bar, line icons.
   Used by Forka Apps (launcher), Hire, Boards and Procurement. Plain JS, no framework: each app calls FS.header(...)
   and FS.menu(...) inside its own render() and FS.after() once the HTML is on the page.
   The same file lives in the Procurement repo (kept identical by a test). No emojis: line icons only. */
(function () {
  'use strict';
  const ERP = 'https://erp.forka.com/';
  const SAME = /(^|\.)erp\.forka\.com$/.test(location.hostname) || location.hostname === 'localhost' || location.hostname === '127.0.0.1' || location.protocol === 'file:';

  // ---------- line icons (24px grid, 1.8 stroke) ----------
  const P = {
    apps: '<rect x="4" y="4" width="6" height="6" rx="1.5"/><rect x="14" y="4" width="6" height="6" rx="1.5"/><rect x="4" y="14" width="6" height="6" rx="1.5"/><rect x="14" y="14" width="6" height="6" rx="1.5"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>', down: '<path d="m6 9 6 6 6-6"/>', x: '<path d="M6 6l12 12M18 6 6 18"/>',
    search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>', bell: '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15Z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    home: '<path d="M4 11 12 4l8 7"/><path d="M6 10v9h12v-9"/>', user: '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 20c0-3.6 3.1-6 7-6s7 2.4 7 6"/>',
    out: '<path d="M14 5h4a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1h-4"/><path d="M10 16l-4-4 4-4M6 12h9"/>', check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    plus: '<path d="M12 5v14M5 12h14"/>', more: '<circle cx="6" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="18" cy="12" r="1.4"/>',
    lock: '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>', cal: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/>',
    clock: '<circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/>', alert: '<path d="M12 4 3 20h18Z"/><path d="M12 10v4M12 17h.01"/>',
    info: '<circle cx="12" cy="12" r="8"/><path d="M12 11v5M12 8h.01"/>', ok: '<circle cx="12" cy="12" r="8"/><path d="m8.5 12.5 2.5 2.5 4.5-5"/>',
    left: '<path d="M15 6l-6 6 6 6"/>', right: '<path d="M9 6l6 6-6 6"/>', ext: '<path d="M14 5h5v5M19 5l-8 8"/><path d="M18 14v5H5V6h5"/>',
    hire: '<circle cx="9" cy="9" r="3"/><path d="M3 19c0-3 3-5 6-5s6 2 6 5"/><path d="M17 8v6M14 11h6"/>',
    boards: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 4v16M15 4v10"/>',
    proc: '<path d="M4 7h16l-1.5 11a2 2 0 0 1-2 1.7H7.5a2 2 0 0 1-2-1.7Z"/><path d="M9 7a3 3 0 0 1 6 0"/>',
    chat: '<path d="M5 5h14v10H9l-4 4z"/><path d="M9 9h6M9 12h4"/>', folder: '<path d="M4 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z"/>',
    box: '<path d="M4 8l8-4 8 4v8l-8 4-8-4Z"/><path d="M4 8l8 4 8-4M12 12v8"/>', truck: '<path d="M3 7h11v9H3zM14 10h4l3 3v3h-7"/><circle cx="7" cy="17.5" r="1.6"/><circle cx="17" cy="17.5" r="1.6"/>',
    receipt: '<path d="M6 3h12v18l-3-2-3 2-3-2-3 2Z"/><path d="M9 8h6M9 12h6"/>', wallet: '<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M16 12.5h2M3 9h18"/>',
    doc: '<path d="M6 3h8l4 4v14H6Z"/><path d="M14 3v4h4M9 12h6M9 16h4"/>', chart: '<path d="M4 20h16M7 16v-5M12 16V7M17 16v-8"/>',
    people: '<circle cx="9" cy="9" r="3"/><path d="M3 19c0-3 3-5 6-5s6 2 6 5"/><circle cx="17" cy="8" r="2.4"/><path d="M16 13.5c2.8 0 5 1.6 5 4.5"/>',
  };
  const icon = (n, s = 20) => `<svg class="fs-ic" width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${P[n] || P.more}</svg>`;

  // ---------- words (English / Arabic) ----------
  const W = {
    en: { apps: 'Switch app', home: 'Forka App home', homeName: 'App', hire: 'Hire', boards: 'Board', proc: 'Procurement', menu: 'Menu', more: 'More', close: 'Close', signout: 'Sign out',
      alerts: 'Alerts', lang: 'Language', account: 'Your account', ceo: 'CEO', manager: 'Manager', staff: 'Staff', d_hire: 'Roles, candidates, approvals',
      d_boards: 'Tasks, projects, chat', d_proc: 'Requests, orders, stock', d_home: 'All your apps', noaccess: 'Ask the CEO for access' },
    ar: { apps: 'تبديل التطبيق', home: 'الصفحة الرئيسية لتطبيقات فوركا', homeName: 'التطبيقات', hire: 'التوظيف', boards: 'اللوحات', proc: 'المشتريات', menu: 'القائمة', more: 'المزيد', close: 'إغلاق',
      signout: 'تسجيل الخروج', alerts: 'التنبيهات', lang: 'اللغة', account: 'حسابك', ceo: 'الرئيس التنفيذي', manager: 'مدير', staff: 'موظف',
      d_hire: 'الوظائف والمرشحون والموافقات', d_boards: 'المهام والمشاريع والمحادثة', d_proc: 'الطلبات وأوامر الشراء والمخزون', d_home: 'كل تطبيقاتك',
      noaccess: 'اطلب الصلاحية من الرئيس التنفيذي' },
  };
  let lang = 'en';
  const w = k => (W[lang] && W[lang][k]) || W.en[k] || k;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  // ---------- who is signed in (shared by the apps on erp.forka.com) ----------
  function me() {
    if (!SAME) return null;
    try { const c = JSON.parse(localStorage.getItem('fa-cache') || 'null'); return c && c.me ? c.me : null; } catch (e) { return null; }
  }
  function token() { try { return localStorage.getItem('fa-token') || ''; } catch (e) { return ''; } }
  const APPS = [
    { id: 'home', color: '#896B45', url: () => ERP },
    { id: 'hire', color: '#E0A037', url: () => ERP + 'hiring/', need: 'hire' },
    { id: 'boards', color: '#397F8F', url: () => ERP + 'boards/' },
    { id: 'proc', color: '#BD5038', url: () => 'https://procurement.forka.com/' + (SAME && token() ? '#erp=' + encodeURIComponent(token()) : ''), need: 'proc' },
  ];
  const allowed = (a, p) => !a.need || !p || (p.level === 'ceo' && p.status !== 'blocked') || !!(p.apps && p.apps[a.need]);
  const initials = n => String(n || '').split(/[\s@._-]+/).filter(Boolean).map(x => x[0]).join('').slice(0, 2).toUpperCase() || '?';

  // ---------- header ----------
  // opts: { app: 'home'|'hire'|'boards'|'proc', lang: 'en'|'ar', user: {name, role}, search: html, alerts: html, extra: html, menu: bool (show burger) }
  function header(o) {
    lang = o.lang === 'ar' ? 'ar' : 'en';
    const p = me(), u = o.user || (p ? { name: p.name, role: w(p.level) } : null);
    const appsList = APPS.map(a => {
      const ok = allowed(a, p), cur = a.id === o.app;
      return ok ? `<a href="${esc(a.url())}" class="${cur ? 'fs-cur' : ''}" ${cur ? 'aria-current="page"' : ''} data-fs-app="${a.id}"><span class="fs-appic">${mark(a.id, 32)}</span><span>${esc(w(a.id))}<small>${esc(w('d_' + a.id))}</small></span></a>`
        : `<span style="display:flex;gap:10px;padding:8px 10px;opacity:.6"><span class="fs-appic" style="background:#A8A29A">${icon('lock', 18)}</span><span>${esc(w(a.id))}<small>${esc(w('noaccess'))}</small></span></span>`;
    }).join('');
    return `<header class="fs-head" role="banner">
  ${o.menu ? `<button class="fs-iconbtn fs-burger" data-fs="burger" aria-label="${esc(w('menu'))}">${icon('menu', 22)}</button>` : ''}
  <a class="fs-lock" href="${esc(o.homeHref || (APPS.find(a => a.id === o.app) || APPS[0]).url())}" aria-label="Forka ${esc(w(o.app === 'home' ? 'homeName' : o.app))}">${mark(o.app, 34)}<span class="fs-lockt"><span class="fs-k">FORKA</span><span class="fs-n">${esc(w(o.app === 'home' ? 'homeName' : o.app))}</span></span></a>
  <span style="position:relative"><button class="fs-switch" data-fs="apps" aria-haspopup="true" aria-expanded="false" aria-label="${esc(w('apps'))}">${icon('apps', 16)}<span class="fs-switch-label">${esc(w('apps'))}</span>${icon('down', 14)}</button>
    <div class="fs-pop" data-fs-pop="apps" hidden role="menu" style="top:44px;inset-inline-start:0">${appsList}</div></span>
  <span class="fs-grow"></span>
  ${o.search ? `<span class="fs-slot fs-hide-sm">${o.search}</span>` : ''}
  ${o.extra ? `<span class="fs-slot">${o.extra}</span>` : ''}
  <span class="fs-lang" role="group" aria-label="${esc(w('lang'))}"><button data-fs-lang="en" aria-pressed="${lang === 'en'}">EN</button><button data-fs-lang="ar" aria-pressed="${lang === 'ar'}" lang="ar">ع</button></span>
  ${o.alerts || ''}
  ${u ? `<span style="position:relative"><button class="fs-user" data-fs="user" aria-haspopup="true" aria-expanded="false" aria-label="${esc(w('account'))}"><span class="fs-av">${esc(initials(u.name))}</span><span class="fs-who"><span>${esc(u.name)}</span><small>${esc(u.role || '')}</small></span></button>
    <div class="fs-pop" data-fs-pop="user" hidden role="menu" style="top:46px;inset-inline-end:0"><div class="fs-head-info"><b>${esc(u.name)}</b><small>${esc(u.role || '')}${u.email ? ' · ' + esc(u.email) : ''}</small></div><hr>
      ${(o.userItems || []).map(x => `<button type="button" ${x.attrs || ''}>${icon(x.icon || 'user', 18)}${esc(x.label)}</button>`).join('')}${(o.userItems || []).length ? '<hr>' : ''}<a href="${esc(ERP)}">${icon('home', 18)}${esc(w('home'))}</a>${o.app === 'home' && o.signout !== false ? `<button data-fs="signout">${icon('out', 18)}${esc(w('signout'))}</button>` : `<a href="${esc(ERP)}#signout">${icon('out', 18)}${esc(w('signout'))}</a>`}</div></span>` : ''}
</header>`;
  }
  // The Forka four-petal mark: the App mark has the four brand colours; each app's mark is its own colour.
  let mk = 0;
  function mark(app, size = 34) {
    const c = { home: null, hire: '#E0A037', boards: '#397F8F', proc: '#BD5038' }[app] || null, id = 'fsm' + (++mk);
    const sq = c ? [[7, 7, c, 1], [63, 7, c, .85], [7, 63, c, .68], [63, 63, c, .95]] : [[7, 7, '#397F8F', 1], [63, 7, '#E0A037', 1], [7, 63, '#77987D', 1], [63, 63, '#BD5038', 1]];
    return `<svg width="${size}" height="${size}" viewBox="0 0 118 118" aria-hidden="true" focusable="false"><defs><mask id="${id}"><rect width="118" height="118" fill="#fff"/><circle cx="59" cy="59" r="22" fill="#000"/></mask></defs><g mask="url(#${id})">${sq.map(q => `<rect x="${q[0]}" y="${q[1]}" width="48" height="48" rx="12" fill="${q[2]}"${q[3] < 1 ? ` fill-opacity="${q[3]}"` : ''}/>`).join('')}</g><circle cx="59" cy="59" r="15.8" fill="${c || '#896B45'}"/></svg>`;
  }

  // ---------- module menu ----------
  // items: [{ html: '<a ...>Label</a>' }] or [{ label, on, badge, attrs }] (attrs = the app's own click attributes, e.g. onclick="go('x')")
  function menu(items, o = {}) {
    const it = items.map(x => x.html || `<${x.href ? 'a' : 'button'} ${x.href ? `href="${esc(x.href)}"` : 'type="button"'} class="${x.on ? 'fs-on' : ''}" ${x.on ? 'aria-current="page"' : ''} ${x.attrs || ''}>${x.icon ? icon(x.icon, 18) : ''}<span>${esc(x.label)}</span>${x.badge ? `<span class="fs-badge-n">${esc(x.badge)}</span>` : ''}</${x.href ? 'a' : 'button'}>`).join('');
    return `<nav class="fs-menu" aria-label="${esc(o.label || w('menu'))}" ${o.id ? `id="${esc(o.id)}"` : ''}>${it}<span style="position:relative;flex:none"><button type="button" class="fs-more-btn" data-fs="more" aria-haspopup="true" aria-expanded="false" hidden>${esc(w('more'))} ${icon('down', 14)}</button><div class="fs-pop" data-fs-pop="more" hidden role="menu" style="top:44px;inset-inline-end:0"></div></span></nav>`;
  }
  // Fit every module menu: items that do not fit move into "More" (never a hidden sideways scrollbar).
  function fitMenus() {
    document.querySelectorAll('.fs-menu').forEach(nav => {
      const items = [...nav.children].filter(c => c.matches('a,button'));
      const moreBtn = nav.querySelector('.fs-more-btn'), pop = nav.querySelector('[data-fs-pop="more"]');
      if (!moreBtn) return;
      items.forEach(i => i.classList.remove('fs-hide')); moreBtn.hidden = true; pop.innerHTML = '';
      if (nav.scrollWidth <= nav.clientWidth + 1) return;
      moreBtn.hidden = false;
      const moved = [];
      // keep the current item visible: hide from the end, skipping it
      for (let k = items.length - 1; k >= 0 && nav.scrollWidth > nav.clientWidth + 1; k--) {
        if (items[k].classList.contains('fs-on')) continue;
        items[k].classList.add('fs-hide'); moved.unshift(items[k]);
      }
      pop.innerHTML = moved.map(i => { const c = i.cloneNode(true); c.classList.remove('fs-hide'); c.setAttribute('role', 'menuitem'); return c.outerHTML; }).join('');
    });
  }

  // ---------- drawer (phones) ----------
  // The drawer shows the app's menu items (copied from its .fs-menu, or given by the app) plus the app switcher.
  function openDrawer(extraHTML) {
    closeAll();
    const p = me();
    const menuItems = [...document.querySelectorAll('.fs-menu > a, .fs-menu > button:not(.fs-more-btn)')]
      .map(i => { const c = i.cloneNode(true); c.classList.remove('fs-hide'); if (c.tagName === 'BUTTON') c.classList.add('fs-item'); return c.outerHTML; }).join('');
    const apps = APPS.filter(a => allowed(a, p)).map(a => `<a href="${esc(a.url())}">${icon(a.id === 'home' ? 'apps' : a.id, 18)}${esc(w(a.id === 'home' ? 'home' : a.id))}</a>`).join('');
    let d = document.querySelector('.fs-drawer');
    if (!d) {
      document.body.insertAdjacentHTML('beforeend', '<div class="fs-scrim" data-fs="close" hidden></div><aside class="fs-drawer fs-focus" role="dialog" aria-modal="true" hidden></aside>');
      d = document.querySelector('.fs-drawer');
    }
    d.innerHTML = `<div style="display:flex;align-items:center;justify-content:space-between"><h2>${esc(w(FS._app === 'home' ? 'homeName' : FS._app || 'menu'))}</h2><button class="fs-iconbtn" data-fs="close" aria-label="${esc(w('close'))}" style="color:var(--fs-ink)">${icon('x', 22)}</button></div>
      ${extraHTML || menuItems}${FS.drawerAppend ? FS.drawerAppend() : ''}<div class="fs-sec">${esc(w('apps'))}</div>${apps}`;
    d.hidden = false; document.querySelector('.fs-scrim').hidden = false;
    const f = d.querySelector('a,button'); if (f) f.focus();
  }
  function closeAll() {
    document.querySelectorAll('.fs-pop').forEach(p => { p.hidden = true; });
    document.querySelectorAll('[data-fs][aria-expanded="true"]').forEach(b => b.setAttribute('aria-expanded', 'false'));
    const d = document.querySelector('.fs-drawer'); if (d) d.hidden = true;
    const s = document.querySelector('.fs-scrim'); if (s) s.hidden = true;
  }

  // ---------- bottom bar (phones) ----------
  // items: [{ label, icon, on, badge, attrs|href }]
  function bottom(items) {
    return `<nav class="fs-bottom fs-has" aria-label="${esc(w('menu'))}">${items.map(x => `<${x.href ? 'a' : 'button'} ${x.href ? `href="${esc(x.href)}"` : 'type="button"'} class="${x.on ? 'fs-on' : ''}" ${x.attrs || ''}>${icon(x.icon || 'more', 22)}<span>${esc(x.label)}</span>${x.badge ? `<span class="fs-badge-n">${esc(x.badge)}</span>` : ''}</${x.href ? 'a' : 'button'}>`).join('')}</nav>`;
  }

  // ---------- events (one listener for the whole page; apps re-render freely) ----------
  let wired = false;
  function wire() {
    if (wired) return; wired = true;
    document.addEventListener('click', e => {
      const t = e.target.closest('[data-fs],[data-fs-lang]');
      if (!t) { if (e.target.closest('.fs-drawer')) return; if (!e.target.closest('.fs-pop')) closeAll(); else if (e.target.closest('.fs-pop a,.fs-pop button')) setTimeout(closeAll, 0); return; }
      if (t.dataset.fsLang) { e.preventDefault(); closeAll(); if (FS.onLang) FS.onLang(t.dataset.fsLang); return; }
      const k = t.dataset.fs;
      if (k === 'apps' || k === 'user' || k === 'more') {
        e.preventDefault(); e.stopPropagation();
        const pop = t.parentElement.querySelector(`[data-fs-pop="${k}"]`), open = pop.hidden;
        closeAll(); if (open) { pop.hidden = false; t.setAttribute('aria-expanded', 'true'); const f = pop.querySelector('a,button'); if (f) f.focus(); }
        return;
      }
      if (k === 'burger') { e.preventDefault(); openDrawer(FS.drawerHTML ? FS.drawerHTML() : ''); return; }
      if (k === 'close') { e.preventDefault(); closeAll(); return; }
      if (k === 'signout') { e.preventDefault(); closeAll(); if (FS.onSignOut) FS.onSignOut(); return; }
    }, true);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closeAll(); });
    let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(fitMenus, 60); });
    // a click on an item inside the drawer or More menu closes them
    document.addEventListener('click', e => { if (e.target.closest('.fs-drawer a,.fs-drawer button.fs-item,.fs-pop[data-fs-pop="more"] a,.fs-pop[data-fs-pop="more"] button')) setTimeout(closeAll, 0); });
  }
  // Call after each render that drew a header or menu.
  function after(o = {}) {
    wire();
    if (o.app) FS._app = o.app;
    if (o.bottom) document.body.classList.add('fs-has-bottom'); else if (o.bottom === false) document.body.classList.remove('fs-has-bottom');
    fitMenus();
  }

  window.FS = { header, menu, bottom, after, fitMenus, openDrawer, closeAll, icon, mark, me, token, initials, ERP, onLang: null, onSignOut: null, drawerHTML: null, drawerAppend: null, _app: null };
})();
