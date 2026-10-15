# Bill Studio

Beautiful, free, offline billing for any business in any country.

**Live:** https://theramlakhan.com/projects/bill-studio/

## What it does
- **Every country:** pick your country and get its tax system, currency, bill titles and financial year. This covers Indian GST (CGST/SGST/IGST/UTGST split, cess, HSN, Bill of Supply for composition dealers), EU/UK VAT, US sales tax, Canada GST/HST/PST/QST, Australia, UAE, Saudi Arabia (ZATCA QR), Japan and about 50 more. There is also a generic mode for anywhere else.
- **Bills:** Invoice/Tax Invoice, Sales Receipt, Quotation, Proforma, Credit Note, Debit Note, Delivery Challan and Purchase Order. Numbering is automatic per financial year. The editor shows a live preview.
- **Five templates** (Cupertino, Classic GST, Minimal, Bold, Elegant) and a drag-and-drop **designer**. You can move, resize and restyle every block, with snapping guides, layers and undo.
- **Dues (khata):** customer ledgers, partial payments, ageing, and statement PDFs. Free reminders go out through WhatsApp, SMS or email.
- **Reports:** sales, sales register, GSTR-1 (B2B/B2CL/B2CS/CDN/HSN/docs) or VAT return, profit & loss, ageing, balances, item-wise sales, collections, expenses and day book. Every report exports to PDF and CSV.
- **Payment QR codes:** UPI, SEPA GiroCode, or any payment link.
- **Private and offline:** all data lives in the browser's IndexedDB on the device. The app is an installable PWA. Backups can be encrypted (AES-GCM).
- Light and dark themes. Works on phones, tablets and desktops.

## Develop
No build step and no Node required: it is plain HTML, CSS and ES modules.

```bash
python3 tools/serve.py 8765          # http://127.0.0.1:8765/
python3 tools/smoke.py http://127.0.0.1:8765/ /tmp/shots            # end-to-end (desktop)
python3 tools/smoke.py http://127.0.0.1:8765/ /tmp/shots --mobile   # phone
open http://127.0.0.1:8765/tests/unit.html                          # tax-engine unit tests
```

## Deploy
```bash
tools/deploy.sh
```
This regenerates `sw.js` (the offline cache list) and copies the runtime files into the GitHub Pages site repo under `projects/bill-studio/`.

## Layout
| Path | Contents |
|---|---|
| `assets/js/tax/` | Country profiles and the pure tax engine |
| `assets/js/views/` | One module per screen |
| `assets/js/render.js`, `templates.js` | Block-based bill renderer and the five built-in designs |
| `assets/js/db.js` | IndexedDB wrapper |
| `assets/vendor/` | qrcode-generator, html2canvas and jsPDF (all MIT), stored locally so the app works offline |

Tax rates are editable defaults. Confirm them with your tax advisor.
