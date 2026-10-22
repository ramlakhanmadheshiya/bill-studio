# Bill Studio — Business-owner test report

**Date:** 22 Oct 2026
**Tested:** local build, the same code that is live at theramlakhan.com/projects/bill-studio.
**How:** I acted as a shop owner, once for each of the 56 countries in the app, plus "Other country".

> **Update 22 Oct 2026: every problem below is fixed.** See section 7 for what changed and the retest results.
> After the fixes, the business-owner journey passes in **all 73 countries** (56 + 17 new ones + "Other country") with zero findings.

## 1. Summary

| | Result |
|---|---|
| Countries tested end to end | 56 + "Other country" |
| Invoice totals correct (checked against an independent calculation) | **57 / 57** (incl. "Other country") |
| Countries with no problem except the UPI/UTR wording | 52 |
| Real bugs found | 3 high, 6 medium, 7 low (listed below) |
| Crashes / JavaScript errors | **0** |

The core of the app is solid. In every country:
- The tax maths and totals are right.
- Part payments, credit notes, customer balances, the dashboard and the tax reports agree with each other.
- The print size defaults to Letter in the US, Canada, Mexico and the Philippines, and to A4 elsewhere.

The problems below are mostly legal wording, one rounding bug, and India-only words leaking into other countries.

## 2. What the business-owner test did (per country)

1. **Set up the business.** Chose the country, registered for tax, and entered the tax number, address, phone and email.
2. **Added a customer:** a B2B buyer with a tax number. For India, the buyer was in another state (Karnataka), to test IGST.
3. **Added a product:** price 1,234.56, stock tracked at 10.
4. **Made an invoice** with:
   - 3 × product at 10% discount
   - 2 × service at a second tax rate
   - shipping 50
   - The test then checked the taxable value, tax and total against my own calculation.
5. **Checked the printed bill:**
   - legal title, number, seller and buyer tax IDs, buyer address
   - tax %, grand total, amount in words
   - India: place of supply and HSN
6. **Checked stock** went down by 3.
7. **Recorded a 40% part payment.** Status should read "Partly paid", and the payment dialog was checked for wrong wording.
8. **Issued a credit note** for 1 returned item. It must reference the original invoice, and its total was checked.
9. **Checked the balance due** after payment + credit note. It must match on the invoice page, in the customer ledger and on the dashboard.
10. **Checked the tax report.** It must show net output tax = invoice tax − credit-note tax.
11. **Made a quotation and converted it** to an invoice. Numbering must continue.
12. **Opened Print** and checked the default paper size.

Extra owner scenarios:
- an Indian composition dealer
- a Saudi walk-in B2C sale
- a Qatar shop under "Other country" with QAR
- a German purchase with input VAT shown in the VAT report

All four worked correctly.

Earlier test suites, still valid because the code has not changed since:
- the country sweep (every country × registered/unregistered, 114/114)
- sign-in, every paper size, export/import (`tools/features.py`)
- unit tests (59/59)

Re-run everything with:
```
python3 tools/serve.py 8765 &
python3 tools/owner_journey.py http://127.0.0.1:8765/ 0 1 results.jsonl   # this report (≈2 min per country)
python3 tools/owner_edge.py                                               # extra owner scenarios
python3 tools/country_sweep.py && python3 tools/features.py
```

## 3. Problems found

### HIGH — fix first

**✅ H1. Tax can be 1 cent/paisa too low (rounding bug). All countries.**
- **What happens:** On a credit note in Croatia, Sweden, Denmark and Norway (25% VAT), VAT on 1,111.10 printed as **277.77** instead of **277.78**, so the total was 1,388.87 instead of 1,388.88.
- **Cause:** `round()` in `assets/js/lib/money.js:12` adds `Number.EPSILON`, which only helps for numbers near 1. In the browser, `round(277.775, 2)` returns 277.77. It also happens with other values and in every currency; it is just less frequent.
- **Why it matters:** Tax shown on the bill won't match what an accountant or the tax office calculates, and totals can differ by 1 unit.
- **Fix:** Round on a decimal-safe value, for example `Math.round(Number((n * f).toPrecision(15))) / f`, or use integer minor units. Add unit tests for 277.775, 1.005, 2.675 and 10.235.

**✅ H2. Default terms say "Goods once sold will not be taken back." All countries.**
- **What happens:** Every new business gets this line printed on every bill (`assets/js/store.js:71`).
- **Why it matters:**
  - In the EU, UK and Australia, consumers have legal return and warranty rights. A clause that denies them is unenforceable and can count as misleading.
  - India's consumer authorities have called this phrase an unfair trade practice.
  - An owner could get into trouble for something the app wrote for them.
- **Fix:** Default to only "Payment is due within N days." Let owners add their own return policy.

**✅ H3. Missing e-invoicing warnings for countries where a PDF/paper invoice is not, or soon won't be, enough.**

The app already warns for IT, PL, BE, HR, HU, PT, FR, SA, MX, BR, VN, EG, KE, ID, MY and IN (`assets/js/tax/countries.js`, `E_INVOICE`). Missing:

| Country | Rule |
|---|---|
| **Romania** | RO e-Factura is mandatory for domestic B2B, and B2C transactions must be reported through it since 1 Jan 2025. |
| **Germany** | Since 2025 businesses must be able to receive e-invoices. From **1 Jan 2027**, businesses with prior-year turnover above €800,000 must issue XRechnung/ZUGFeRD for domestic B2B; all businesses from 1 Jan 2028. A plain PDF is not an e-invoice. |
| **Spain** | VeriFactu certified-software rules are coming (2027). |
| **Greece** | myDATA transmission. |
| **UAE** | E-invoicing phase-in announced (large businesses first). |

Please verify Spain, Greece and the UAE before adding them. Romania and Germany are confirmed.

Sources:
- [EU Commission – eInvoicing in Romania](https://ec.europa.eu/digital-building-blocks/sites/display/DIGITAL/eInvoicing+in+Romania)
- [Orbitax – Romania B2C](https://orbitax.com/news/country/article/Romania-Extends-National-E-Inv-56101)
- [Softco – Germany 2026 update](https://softco.com/blog/germany-e-invoicing-mandate-2026-update/)
- [advisori – Germany 2025-2028](https://www.advisori.de/en/blog/e-invoicing-mandate-germany)

### MEDIUM

**✅ M1. "UPI" and "UTR" shown to every country.** Seen in all 56 non-Indian countries.
- **What happens:**
  - The payment dialog's "Mode" list includes **upi**, an Indian payment system.
  - The reference placeholder says **"UTR / cheque no."**; UTR is an Indian bank term.
  - The same list is used in the expense dialog.
- **Where:** `assets/js/payui.js:7` (`PAY_MODES`), and the placeholder in `paymentDialog`; `assets/js/views/money.js:23`.
- **Fix:**
  - Show "UPI" only when the country is IN (or the currency is INR).
  - Use "Transaction / cheque no." elsewhere.
  - Consider local modes: SEPA transfer (EU), PayNow (SG), PIX (BR), M-Pesa (KE), Zelle/ACH (US).

**✅ M2. Wrong or misleading bill titles in some countries.** These countries use the generic "VAT Invoice" title from `vat()` in `countries.js`:

| Country | App prints | Law / practice expects |
|---|---|---|
| Pakistan | VAT Invoice, but tax column says "Sales tax" | **Sales Tax Invoice** (contradicts itself) |
| Brazil | VAT Invoice | Brazil has no VAT (ICMS/ISS). Use "Invoice / Fatura". The legal document is the NF-e (already warned). |
| Oman | VAT Invoice | **Tax Invoice** |
| Sri Lanka | VAT Invoice | **Tax Invoice**. A standard VAT tax-invoice format is mandatory from 1 Apr 2026. |
| Thailand, Nepal, Egypt, Kenya | VAT Invoice | Usually "Tax Invoice". Please verify each. |

Bahrain checked: "VAT Invoice" or "Tax Invoice" are both accepted.

Sources:
- [Tally – Oman tax invoice checklist](https://tallysolutions.com/mena/oman-vat/quick-checklist-for-tax-invoice-in-oman)
- [Daily FT – Sri Lanka VAT tax invoice format](https://www.ft.lk/columns/New-VAT-tax-invoice-format-mandatory-from-1-April-2026/4-790220)
- [Avalara – Bahrain](https://www.avalara.com/vatlive/en/country-guides/africa-and-middle-east/bahrain/bahrain-vat-rates.html)

**✅ M3. No backup reminder where the owner looks.**
- **What happens:** "Last backup: Never" appears only inside Settings. The home screen never warns.
- **Why it matters:** All data lives in one browser. Safari can delete website data after 7 days without a visit, unless the app is installed. Clearing browser data or changing PC also loses everything.
- **Fix:** Show a dashboard banner when there has been no backup for 7 or more days, with a one-tap "Back up now".

**✅ M4. Purchases can't record the supplier's tax number or invoice details.**
- **What happens:** The expense form has only total + "tax included" (`assets/js/views/money.js:18-25`).
- **Why it matters:**
  - Indian owners need the supplier GSTIN, invoice number and date to claim input tax credit and to match GSTR-2B.
  - EU/UK owners need the supplier VAT number for input VAT.
- **Fix:** Add optional supplier tax ID, supplier invoice number and tax rate fields. For India, add a GSTR-2B-style purchase register report.

**✅ M5. Germany: supply date (Leistungsdatum) is not printed when it equals the invoice date.**
- **What happens:** `render.js:162` prints the supply date only when it differs.
- **Why it matters:** §14(4) UStG requires the delivery or service date. When it is the same day, German practice is to print "Leistungsdatum = Rechnungsdatum".
- **Fix:** For DE (and AT), always print the supply date, or that note.

**✅ M6. EU "customer address required" rule is stricter than the law.**
- **What happens:** For every EU country, an invoice over **€100** without a customer address is blocked (`editor.js:451`).
- **Why it matters:**
  - Germany allows small-amount invoices up to **€250** without the buyer's address; Austria up to **€400**.
  - A café or shop selling to walk-in customers is blocked for no legal reason.
- **Fix:** Use each country's simplified-invoice limit (DE 250, AT 400, others 100, UK 250).
- **Also:** warn when saving a *quotation* without an address. Today the quotation saves fine and the conversion to invoice then fails. This happened in 28 EU/UK countries in the test.

### LOW

| # | Problem | Where / fix |
|---|---|---|
| ✅ L1 | **Switzerland:** the seller UID prints as `CHE-123.456.789MWST`. The space is removed on save, while the official format is `CHE-123.456.789 MWST` (the buyer's UID keeps the space). | Don't strip spaces from the stored tax ID. Normalise only for validation. |
| ✅ L2 | **Japan / JPY:** product prices accept decimals (1,234.56). The bill shows the rate as ¥1,235 but calculates with .56, so 3 × 1,235 − 10% doesn't equal the printed ¥3,333. | Round prices to the currency's decimals when saving items and lines. |
| ✅ L3 | **India:** a shipping or other charge has no HSN/SAC, so the HSN summary shows a "—" row, which the GSTR-1 HSN table needs filled. | Let charges carry a SAC (e.g. 9965/9968). |
| ✅ L4 | **US:** shipping is taxed at the sales-tax rate by default. Many states don't tax separately stated shipping. | Default the shipping tax to "Tax exempt" for the US, and mention it in the help text. |
| ✅ L5 | Dates in the bill header use the country locale ("22. Oktober 2026", "2026年10月22日") while the app is in English. Mixed languages look odd. | Use an English month format, or offer an "invoice language" setting. |
| ✅ L6 | Reports reopen the last report instead of the list when the owner comes back. It's slightly confusing at first. | Start at the list; remember only the period. |
| ✅ L7 | **Missing countries.** Owners from these countries must pick "Other country" and set up tax by hand: South Korea, Turkey, China, Hong Kong, Taiwan, Israel, Qatar, Kuwait, Ghana, Tanzania, Uganda, Morocco, Argentina, Chile, Colombia, Peru, Iceland. Switzerland also lacks the Swiss **QR-bill**, which Swiss customers expect on invoices. | Add profiles over time. Qatar and Kuwait have no VAT, so a preset with the currency is enough. |

## 4. What worked well (no change needed)

**India:**
- CGST/SGST vs IGST split.
- Place of supply auto-filled from the buyer's GSTIN.
- HSN summary.
- Composition dealer "Bill of Supply" with the legal declaration.
- Original/Duplicate labels.
- ₹50,000 address rule.
- B2CL threshold ₹1 lakh.
- Export/SEZ/LUT endorsements.

**Saudi Arabia:**
- Simplified Tax Invoice for B2C, with the Arabic title.
- ZATCA QR code.

**Japan:** Qualified Invoice with registration number, per-rate totals, tax rounded once per rate, and the reduced-rate (8%) mark.

**Currencies with 3 decimals and no decimals:**
- Bahrain and Oman: 3 decimals, with words in Dinars/Rials and Fils/Baisa.
- JPY, IDR, VND: no decimals.
- Qatar under "Other country": "Riyals and Dirhams".

**Germany:** the VAT report shows output VAT − input VAT = net payable correctly.

**Every country:**
- Stock reduces when billed.
- Part-payment status.
- Credit notes linked to the invoice.
- Customer ledger, dashboard and reports agree.
- Quotation → invoice keeps the numbering sequence.
- Correct default paper size.

## 5. Per-country results

"Pass" means every check passed. "(UPI/UTR shown)" is problem M1, which affects every non-Indian country.

| Country | Bill title | Currency | Default tax | Invoice total (app = expected) | Paper | Result |
|---|---|---|---|---|---|---|
| Australia (AU) | Tax Invoice | AUD | GST 10% | 3941.62 (Yes) | A4 | Pass (UPI/UTR shown) |
| Austria (AT) | VAT Invoice | EUR | VAT 20% | 4285.95 (Yes) | A4 | Pass (UPI/UTR shown) |
| Bahrain (BH) | VAT Invoice | BHD | VAT 10% | 3941.621 (Yes) | A4 | Pass (UPI/UTR shown) |
| Bangladesh (BD) | VAT Invoice | BDT | VAT 15% | 4110.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| Belgium (BE) | VAT Invoice | EUR | VAT 21% | 4317.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| Brazil (BR) | VAT Invoice ⚠ M2 | BRL | ICMS 18% | 4202.29 (Yes) | A4 | Pass (UPI/UTR shown) |
| Bulgaria (BG) | VAT Invoice | EUR | VAT 20% | 4277.95 (Yes) | A4 | Pass (UPI/UTR shown) |
| Canada (CA) | Invoice | CAD | HST 13% (ON) | 4033.12 (Yes) | US Letter | Pass (UPI/UTR shown) |
| Croatia (HR) | VAT Invoice | EUR | VAT 25% | 4455.12 (Yes) | A4 | **Credit note 1 cent low (H1)** (UPI/UTR shown) |
| Cyprus (CY) | VAT Invoice | EUR | VAT 19% | 4244.12 (Yes) | A4 | Pass (UPI/UTR shown) |
| Czechia (CZ) | VAT Invoice | CZK | VAT 21% | 4317.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| Denmark (DK) | VAT Invoice | DKK | VAT 25% | 4479.12 (Yes) | A4 | **Credit note 1 øre low (H1)** (UPI/UTR shown) |
| Egypt (EG) | VAT Invoice | EGP | VAT 14% | 4084.95 (Yes) | A4 | Pass (UPI/UTR shown) |
| Estonia (EE) | VAT Invoice | EUR | VAT 24% | 4421.28 (Yes) | A4 | Pass (UPI/UTR shown) |
| Finland (FI) | VAT Invoice | EUR | VAT 25.5% | 4473.03 (Yes) | A4 | Pass (UPI/UTR shown) |
| France (FR) | VAT Invoice | EUR | VAT 20% | 4279.95 (Yes) | A4 | Pass (UPI/UTR shown) |
| Germany (DE) | VAT Invoice | EUR | VAT 19% | 4240.12 (Yes) | A4 | Pass (UPI/UTR shown) — see H3, M5, M6 |
| Greece (GR) | VAT Invoice | EUR | VAT 24% | 4421.28 (Yes) | A4 | Pass (UPI/UTR shown) |
| Hungary (HU) | VAT Invoice | HUF | VAT 27% | 4533 (Yes) | A4 | Pass (UPI/UTR shown) |
| India (IN) | Tax Invoice | INR | GST 18% | 4193 (Yes) | A4 | Pass |
| Indonesia (ID) | VAT Invoice | IDR | PPN 12% | 4011 (Yes) | A4 | Pass (UPI/UTR shown) |
| Ireland (IE) | VAT Invoice | EUR | VAT 23% | 4388.45 (Yes) | A4 | Pass (UPI/UTR shown) |
| Italy (IT) | VAT Invoice | EUR | VAT 22% | 4347.62 (Yes) | A4 | Pass (UPI/UTR shown) |
| Japan (JP) | Qualified Invoice | JPY | Consumption tax 10% | 3937 (Yes) | A4 | Pass (UPI/UTR shown) — see L2 |
| Kenya (KE) | VAT Invoice | KES | VAT 16% | 4140.62 (Yes) | A4 | Pass (UPI/UTR shown) |
| Latvia (LV) | VAT Invoice | EUR | VAT 21% | 4317.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| Lithuania (LT) | VAT Invoice | EUR | VAT 21% | 4317.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| Luxembourg (LU) | VAT Invoice | EUR | VAT 17% | 4186.45 (Yes) | A4 | Pass (UPI/UTR shown) |
| Malaysia (MY) | Tax Invoice | MYR | Sales tax 10% | 3931.62 (Yes) | A4 | Pass (UPI/UTR shown) |
| Malta (MT) | VAT Invoice | EUR | VAT 18% | 4206.29 (Yes) | A4 | Pass (UPI/UTR shown) |
| Mexico (MX) | VAT Invoice | MXN | IVA 16% | 4140.62 (Yes) | US Letter | Pass (UPI/UTR shown) |
| Nepal (NP) | VAT Invoice | NPR | VAT 13% | 4049.12 (Yes) | A4 | Pass (UPI/UTR shown) |
| Netherlands (NL) | VAT Invoice | EUR | VAT 21% | 4311.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| New Zealand (NZ) | Tax Invoice | NZD | GST 15% | 4120.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| Nigeria (NG) | VAT Invoice | NGN | VAT 7.5% | 3852.04 (Yes) | A4 | Pass (UPI/UTR shown) |
| Norway (NO) | VAT Invoice | NOK | VAT 25% | 4459.12 (Yes) | A4 | **Credit note 1 øre low (H1)** (UPI/UTR shown) |
| Oman (OM) | VAT Invoice ⚠ M2 | OMR | VAT 5% | 3762.457 (Yes) | A4 | Pass (UPI/UTR shown) |
| Other country (OTHER) | Invoice | USD | Tax 10% | 3941.62 (Yes) | A4 | Pass (UPI/UTR shown) |
| Pakistan (PK) | VAT Invoice ⚠ M2 | PKR | Sales tax 18% | 4228 (Yes) | A4 | Pass (UPI/UTR shown) |
| Philippines (PH) | VAT Invoice | PHP | VAT 12% | 4013.29 (Yes) | US Letter | Pass (UPI/UTR shown) |
| Poland (PL) | VAT Invoice | PLN | VAT 23% | 4377.45 (Yes) | A4 | Pass (UPI/UTR shown) |
| Portugal (PT) | VAT Invoice | EUR | VAT 23% | 4387.45 (Yes) | A4 | Pass (UPI/UTR shown) |
| Romania (RO) | VAT Invoice | RON | VAT 21% | 4315.79 (Yes) | A4 | Pass (UPI/UTR shown) — see H3 |
| Saudi Arabia (SA) | Tax Invoice | SAR | VAT 15% | 4120.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| Singapore (SG) | Tax Invoice | SGD | GST 9% | 3905.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| Slovakia (SK) | VAT Invoice | EUR | VAT 23% | 4399.45 (Yes) | A4 | Pass (UPI/UTR shown) |
| Slovenia (SI) | VAT Invoice | EUR | VAT 22% | 4346.62 (Yes) | A4 | Pass (UPI/UTR shown) |
| South Africa (ZA) | Tax Invoice | ZAR | VAT 15% | 4120.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| Spain (ES) | VAT Invoice | EUR | VAT 21% | 4313.79 (Yes) | A4 | Pass (UPI/UTR shown) |
| Sri Lanka (LK) | VAT Invoice ⚠ M2 | LKR | VAT 18% | 4228.29 (Yes) | A4 | Pass (UPI/UTR shown) |
| Sweden (SE) | VAT Invoice | SEK | VAT 25% | 4453.12 (Yes) | A4 | **Credit note 1 öre low (H1)** (UPI/UTR shown) |
| Switzerland (CH) | VAT Invoice | CHF | VAT 8.1% | 3864.94 (Yes) | A4 | Pass (UPI/UTR shown) — see L1 |
| Thailand (TH) | VAT Invoice | THB | VAT 7% | 3834.12 (Yes) | A4 | Pass (UPI/UTR shown) |
| United Arab Emirates (AE) | Tax Invoice | AED | VAT 5% | 3762.46 (Yes) | A4 | Pass (UPI/UTR shown) |
| United Kingdom (GB) | VAT Invoice | GBP | VAT 20% | 4269.95 (Yes) | A4 | Pass (UPI/UTR shown) |
| United States (US) | Invoice | USD | Sales tax 8.25% | 3878.92 (Yes) | US Letter | Pass (UPI/UTR shown) — see L4 |
| Vietnam (VN) | VAT Invoice | VND | VAT 10% | 3937 (Yes) | A4 | Pass (UPI/UTR shown) |

Test-script false alarms I checked by hand and **dismissed**:
- Canada "HST vs GST": my script picked GST 5% for the second line itself.
- Switzerland "tax ID missing": it is printed, just without the space (L1).
- EU quotation conversions blocked: this is the correct address rule (see M6 for the threshold).

## 6. Suggested fix order

1. **H1** rounding (one small function + tests)
2. **H2** default terms (one line)
3. **M1** UPI/UTR
4. **M2** titles
5. **H3** e-invoice warnings
6. **M3** backup banner
7. **M5 / M6** Germany and EU rules
8. **M4** purchase fields
9. The **low** items as time allows.

## 7. Fixes applied (22 Oct 2026)

| Issue | What changed | Where |
|---|---|---|
| H1 rounding | `round()` now rounds the decimal value people see (277.775 → 277.78, 1.005 → 1.01). 10 new unit tests, including 25% VAT on 1,111.10 = 277.78. | `assets/js/lib/money.js` |
| H2 terms | The default terms are now only "Payment is due within 15 days." Businesses that still had the old untouched default are cleaned automatically. | `assets/js/store.js` |
| H3 e-invoicing | Added warnings for Romania (RO e-Factura), Germany (2027/2028 B2B e-invoice), Spain (VeriFactu), Greece (myDATA) and the UAE, plus every new country that has a mandate. | `assets/js/tax/countries.js` |
| M1 UPI/UTR | Payment modes are now per country: UPI in India only, plus local methods (PIX, M-Pesa, PayNow, DuitNow, PromptPay, GCash, bKash, iDEAL, Raast, ACH/Zelle, PayID, Swish, Vipps, MobilePay, BLIK, TWINT). The placeholder reads "Transaction / cheque no." outside India. The demo data no longer uses UPI outside India. | `assets/js/payui.js`, `money.js`, `editor.js`, `seed.js` |
| M2 titles | Pakistan "Sales Tax Invoice". Brazil and Mexico "Invoice". Oman, Sri Lanka, Thailand, Nepal, Egypt and Kenya "Tax Invoice". Bangladesh "Tax Invoice (Mushak-6.3)". | `countries.js` |
| M3 backup | The home screen shows a banner when there has been no backup for 7+ days, with "Back up now" and a 3-day "Later". | `views/dashboard.js` |
| M4 purchases | Expenses now record the supplier's tax ID (GSTIN is checked in India) and the supplier invoice number. A new **Input tax register** appears in the Expense report (CSV-exportable). The VAT/GST report lists the supplier ID and invoice number. | `views/money.js`, `views/reports.js` |
| M5 DE/AT supply date | German and Austrian invoices and credit notes always print the date of supply. | `render.js` |
| M6 EU address | Each country's simplified-invoice limit is used, in its own currency: DE €250, AT €400, UK £250, SE 4,000 kr, DK 3,000 kr, PL 450 zł, CZ 10,000 Kč, HU 40,000 Ft, RO 500 lei, other EU €100. **This also fixed a hidden bug:** the €100 limit was compared directly to SEK, DKK, PLN, CZK, HUF and RON amounts. Saving a quotation without an address now warns that the converted invoice will need one. | `views/editor.js` |
| L1 Swiss UID | The tax ID keeps its official spacing (`CHE-123.456.789 MWST`). Other countries are still compacted. | `tax/rules.js` (`normTaxId`) |
| L2 JPY rates | Unit rates print with their real decimals (up to 4), so ¥1,234.56 no longer shows as ¥1,235. | `money.js` (`fmtRate`), `render.js` |
| L3 SAC on charges | Indian charges have a SAC field, pre-filled with 9965 for shipping, so the HSN summary has no blank row. | `editor.js` |
| L4 US shipping | New shipping charges in the US default to tax-exempt. The owner can change this per bill. | `editor.js` |
| L5 dates | Spelled-out dates are in English in the country's order ("22 October 2026"). Numeric dates keep the local format. | `lib/dates.js` |
| L6 reports | Reports always open at the list. | `views/reports.js` |
| L7 countries | **17 new countries:** South Korea, Taiwan, China, Hong Kong, Türkiye, Israel, Qatar, Kuwait, Tanzania, Uganda, Morocco, Argentina, Chile, Colombia, Peru and Iceland. Hong Kong, Qatar and Kuwait are set up as no-tax countries, with no registration question. Currency words and WhatsApp dialling codes were added for all countries. **Swiss QR-bill:** Swiss and Liechtenstein IBANs now print a Swiss QR payment code (SPC 0200, structured address, Swiss cross). | `countries.js`, `words.js`, `share.js`, `lib/qr.js`, onboarding and profile |

Found and fixed during the live retest: **a new user's setup could reset to the welcome screen.** On a first visit the offline service worker took control and the app reloaded itself, wiping a half-filled setup. It now reloads only after the owner presses "Update" (`assets/js/app.js`).

Not added: **Ghana**, because its 2026 VAT reform rates could not be confirmed. Ghanaian owners can use "Other country" until then.

### Retest after the fixes
- Unit tests: **84 / 84** pass (25 new).
- Business-owner journey: **73 / 73 countries pass with zero findings**. It now also checks that the no-returns clause is gone and that the DE/AT supply date is printed.
- Edge scenarios (India composition, Saudi B2C, Qatar, German input VAT and the new supplier fields): pass.
- Swiss QR-bill: printed on a Swiss invoice with an IBAN.
- Country sweep (every country, registered and not registered): **146 / 146** with 0 issues.
- Sign-in, every paper size, export/import (`features.py`): all pass. Smoke tests for India, the US and mobile: pass.
- **Live site** (theramlakhan.com) owner journey for IN, US, SE, DE, QA and KR: all pass.
