# Forka Procurement (procurement.forka.com): notes for Claude

Owner: Khaled Alamer, CEO of Forka Collective. Read this before any change.

## Standing rules (Khaled)
- Never change the live app, and never push to main, unless Khaled says "add it" / "go live" for that change. Build and test first: open index.html in demo mode (empty SHEET_URL and ERP_URL in a local copy of config.js) with Playwright, then show him screenshots.
- No emojis. Forka brand: charcoal / paper / bronze. Headings in EB Garamond, text in Inter Tight, Arabic in IBM Plex Sans Arabic. Every screen in English and Arabic.
- The sides are Purchasing, Operations, Requests and Payments, plus CEO approvals, plus Oman. Never call any of them "Planning".
- No approval limits for now. Every purchase from a department request needs the CEO's OK before the order is placed.
- LPOs are generated automatically: from CEO-approved requests and from counted stock below reserve. "New LPO" adds a manual one.
- Required fields show red. Closing a request always needs a reason.
- Before any change or go-live: look at the live design first (header, logo, colours, fonts). If it differs from what the work was built on, change nothing and show Khaled side-by-side screenshots; he decides. Every change keeps the current colours and logo design (Khaled, 12 Nov 2026).

## How it works
- The month's item list (items, suppliers, prices, use) is in the Sheet tab "Base" and is sent only after sign-in (Code.gs ensureBase_/importBase_). It was the public data.json until 13 Nov 2026; never put real items, suppliers or prices in the repo again. demo-data.json is made-up sample data for demo mode and tests.
- index.html is the whole app (one file). config.js holds SHEET_URL (the Procurement Apps Script web app) and ERP_URL. CNAME is procurement.forka.com, served by GitHub Pages from main.
- Sign-in only goes through erp.forka.com (Forka Apps). The server asks the accounts server "who" this person is and caches the answer for 5 minutes. Sections (sides): plan, ops, dept, fin, ceo, oman. Access is set in Forka Apps > People and access. An active CEO gets all of them automatically.
- Code.gs = Apps Script project "Procurment" (1RDOgbmpCbTzqOYhr28cVHDNEfeo3H06Cpu_2MPJyK790lEA8tv951FcT), bound to the Sheet "Forka Procurement Planner — November 2026 (database)". Khaled deploys it himself: paste, then Deploy > Manage deployments > pencil > New version. It lives in a different project from the Forka Apps accounts server, so never mix them up.
- Oman (REGION 'oman'): its own items, suppliers, LPOs (LPO-OM-…), GRNs (GRN-OM-…), stock and payments, in OMR. These are kept in the Sheet tabs OmanItems / OmanSuppliers / OmanPOs / OmanGRN / Oman<kind>. The Oman button opens 3 sides: Purchasing (lpo, fill, sups, ana, sum), Operations (grn, moves) and Payments (pay, soa). Payments show "Paid from: UAE / Oman" with a filter. The Oman manager (oman@forka.com, Mr. Tamer) orders, receives and counts. Abu Ali and Khaled approve.

## Rollback
Website: revert the commit on main. Script: Manage deployments > pencil > previous version.

## Open items (8 Nov 2026)
- Oman item list starts empty. Oman adds items and suppliers, or Khaled sends a file to import.
- WhatsApp alerts need a Meta WhatsApp Cloud API account. Email works without it.
- Offered, waiting for Khaled: email the LPO PDF to the supplier automatically on issue.
- Long term: Foodics inventory or Odoo within 3–6 months.
