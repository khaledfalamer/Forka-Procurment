# Forka Procurement Planner — GitHub version

The team fills in the November purchase plan in the browser. No Claude account needed.
Everything they type is saved in a Google Sheet that Khaled owns:
**Forka Procurement Planner — November 2026 (database)**
https://docs.google.com/spreadsheets/d/18QYN4Js_pmckauDBkPT6oFie2icp3PNak71VNtVEYHc/edit

## Files
- `index.html`: the app (EN / عربي).
- The item list is kept in the Google Sheet (tab "Base") and is sent only after sign-in. `demo-data.json` is made-up sample data for demo mode and tests.
- `config.js`: the one file you edit (the Sheet link and the PIN switch).
- `Code.gs`: the small script that connects the Sheet. It goes into Google, not GitHub.

## Setup (about 10 minutes, one time)

### A. Connect the Google Sheet
1. Open the Sheet above → **Extensions → Apps Script**.
2. Delete what is there, paste all of `Code.gs`, and save.
3. **Team PIN (required):** **Project Settings (⚙) → Script properties → Add**. Name `PIN`, value e.g. `4821`. Without a PIN nobody can save.
4. **Deploy → New deployment →** type **Web app**. Set *Execute as*: **Me**, and *Who has access*: **Anyone**. Press **Deploy** and allow access.
5. Copy the **Web app URL** (it ends with `/exec`).

### B. Put it on GitHub
1. In GitHub, create a repository (e.g. `forka-procurement`), or add a folder `procurement/` to an existing one.
2. `config.js` already holds your Sheet link. `PIN: 'auto'` means the PIN box appears only if you set a PIN in the script.
3. Upload `index.html`, `demo-data.json` and `config.js`.
4. Go to **Settings → Pages → Deploy from branch → main / root → Save**. After a minute, the link is `https://<account>.github.io/<repo>/`.
5. Send the link (and the PIN) to the procurement team.

## How the team uses it
- The app opens **view only**. To change anything: type your name and the team PIN, then press **Edit**.
- Red boxes are missing: price, unit, packing, supplier, payment, monthly use, PAR. Changed boxes turn bronze.
- Nothing is saved until you press **Save changes**. **Cancel changes** throws them away.
- **To buy = Use + PAR − Stock now.** Update the stock with today's count, then press **Confirm** on each line.
- After saving, others see the changes within 30 seconds.
- The Sheet has one row per line the team touched, with readable columns. Don't edit the last column (`data`).

## Suppliers tab
- Add suppliers and their details: contact, phone, email, payment terms, credit days, delivery days, lead time, TRN, area, what they supply, notes.
- Red = missing phone or payment terms (and credit days for credit suppliers). Renaming a supplier renames it on all its items.
- Saved to the **Suppliers** tab of the Sheet.

## Notes
- Only people with the PIN can save; the Sheet checks it. To change the PIN, edit it in Script properties (no redeploy needed).
- If the Sheet can't be reached, changes stay in that browser. "Send my updates" copies them so they can be sent and imported later.
- To change the code later, edit the script and use **Deploy → Manage deployments → Edit → New version**. The URL stays the same.

---

# مخطط المشتريات — نسخة GitHub

الفريق يعبّي خطة مشتريات نوفمبر من المتصفح، ولا يحتاج حساب Claude.
كل شيء يُحفظ في Google Sheet يملكه خالد (الرابط أعلاه).

## الإعداد (مرة واحدة، حوالي 10 دقائق)
1. افتح الشيت → **Extensions → Apps Script**. الصق كل محتوى `Code.gs` واحفظ.
2. **رمز الفريق (إلزامي):** **Project Settings → Script properties**. الاسم `PIN` والقيمة مثلاً `4821`. بدون رمز لا أحد يستطيع الحفظ.
3. **Deploy → New deployment → Web app**. *Execute as*: Me، و*Who has access*: Anyone. ثم Deploy، وانسخ الرابط الذي ينتهي بـ `/exec`.
4. ملف `config.js` فيه رابط الشيت جاهز. خانة الرمز تظهر فقط إذا وضعت رمزاً في السكربت.
5. ارفع `index.html` و`demo-data.json` و`config.js` إلى GitHub، وفعّل **Settings → Pages**، ثم أرسل الرابط والرمز للفريق.

## تبويب الموردين
- أضف الموردين وبياناتهم: الشخص المسؤول، الهاتف، البريد، شروط الدفع، أيام الآجل، أيام التوريد، مدة التوريد، الرقم الضريبي، المنطقة، ماذا يورّد، ملاحظات.
- تُحفظ في تبويب **Suppliers** في الشيت.

## طريقة الاستخدام
- التطبيق يفتح **للعرض فقط**. للتعديل اكتب اسمك ورمز الفريق ثم اضغط **تعديل**.
- الخانات الحمراء ناقصة، والخانات التي غيّرتها تصبح بلون برونزي.
- لا يُحفظ شيء حتى تضغط **حفظ التعديلات**.
- **للشراء = الاستهلاك + مخزون الأمان − المخزون الآن.** حدّث المخزون بجرد اليوم ثم اضغط **تأكيد** لكل سطر.
- بعد الحفظ تظهر التعديلات للباقين خلال 30 ثانية.
