# MyFolioPulse — Implementation Document

**Version:** 1.0 (Demo)  
**Built:** May 2026  
**Status:** Fully functional demo — end-to-end tested  
**Live URL:** https://muralmu.github.io/my-folio-pulse/

---

## What It Does

MyFolioPulse is a daily mutual fund health digest for NRI investors. Users sign up once via a web form, configure their Indian mutual funds, and receive a personalised daily email report with a health score per fund, benchmark comparison, and returns across all periods. Every user also gets a private dashboard URL they can bookmark.

---

## Architecture Overview

```
User signs up via signup.html (GitHub Pages)
        ↓
POST to Google Apps Script Web App
        ↓
Apps Script writes to Google Sheet (private database)
        ↓
GitHub Actions triggers daily (5 timezone cron schedules)
        ↓
generate_reports.py reads Google Sheet CSV
        ↓
Fetches NAV data from mfapi.in for each user's funds
        ↓
Calculates returns + health scores + benchmark comparison
        ↓
Generates personalised HTML report per user
        ↓
Saves dashboard to users/[uuid].html (GitHub Pages)
        ↓
Emails report to user via Gmail SMTP
        ↓
Commits updated dashboards back to repo (GitHub Actions)
```

---

## Repository Structure

```
my-folio-pulse/
├── index.html                    ← Landing page
├── signup.html                   ← Sign-up form with live fund search
├── privacy.html                  ← Privacy notice
├── robots.txt                    ← Blocks /users/ from search engines
├── data/
│   └── users.json                ← Placeholder (not used in v1)
├── users/
│   ├── .gitkeep                  ← Keeps folder tracked by git
│   └── [uuid].html               ← Auto-generated per-user dashboards
├── scripts/
│   ├── generate_reports.py       ← Main report engine
│   └── apps_script.js            ← Google Apps Script source (reference copy)
└── .github/
    └── workflows/
        └── daily_reports.yml     ← GitHub Actions cron workflow
```

---

## Key Files

### `index.html` — Landing Page
- NRI-focused messaging
- How it works (3 steps)
- Feature cards
- Sample report preview
- Timezone coverage section
- CTA → signup.html

### `signup.html` — Sign-up Form
- 4-step wizard: You → Timezone → Funds → Confirm
- Live fund search powered by mfapi.in search API
- Results filtered to Growth plans only
- Selected funds shown as removable chips
- Max 10 funds per user
- On submit: POSTs to Google Apps Script with `no-cors`
- Stores: name, email, timezone, fund scheme codes + names

### `privacy.html` — Privacy Notice
- Plain English
- What is collected (name, email, timezone, fund preferences only)
- No financial data, no broker access
- Data deletion process
- Contact: myfoliopulse@gmail.com

### `scripts/generate_reports.py` — Report Engine
- Reads active users from Google Sheet CSV
- Filters by `RUN_TIMEZONE` environment variable
- For each user:
  - Fetches NAV history from mfapi.in for each fund
  - Calculates returns: 1D, 1W, 1M, 3M, 6M, 1Y, 3Y
  - Fetches benchmark fund NAV for peer comparison
  - Computes weighted health score (0–100)
  - Generates HTML report (dashboard + email versions)
  - Saves dashboard to `users/[uuid].html`
  - Sends email via Gmail SMTP

### `.github/workflows/daily_reports.yml` — Scheduler
- 5 cron triggers for timezone coverage
- Manual trigger with timezone override
- Commits generated dashboards back to repo

---

## Data Flow

### Sign-up Flow
```
signup.html → fetch (no-cors POST) → Apps Script Web App
→ validates secret token
→ checks for duplicate email
→ generates UUID v4
→ writes row to Google Sheet
→ returns {status, userId, dashboardUrl}
```

### Daily Report Flow
```
GitHub Actions cron → determine RUN_TIMEZONE
→ python generate_reports.py
→ GET Google Sheet CSV URL → parse active users
→ filter by RUN_TIMEZONE
→ for each user:
    → GET mfapi.in/mf/{scheme} for each fund
    → calculate returns across periods
    → GET benchmark fund NAV
    → compute health score
    → generate HTML
    → write users/{uuid}.html
    → send email via SMTP
→ git add users/ && git commit && git push
```

---

## Health Score Algorithm

**Scoring starts at 50 (neutral baseline)**

### Return Weights
| Period | Weight | Rationale |
|---|---|---|
| 1M | 10% | Low — short-term noise |
| 3M | 15% | Low-medium |
| 6M | 20% | Medium |
| 1Y | 30% | High — meaningful signal |
| 3Y | 25% | High — long-term strength |

*1D and 1W are displayed but excluded from scoring entirely*

### Benchmark Delta Bonus
- 1Y outperformance vs peer: +15% of delta added to score
- 3Y outperformance vs peer: +10% of delta added to score

### Verdict Thresholds
| Score | Verdict |
|---|---|
| 65–100 | 🟢 Healthy |
| 40–64 | 🟡 Watch |
| 0–39 | 🔴 Concern |

---

## Benchmark Map

| Fund Type (keyword match) | Benchmark Fund | Scheme Code |
|---|---|---|
| nifty 50 | UTI Nifty 50 Direct | 120716 |
| nasdaq | Mirae Asset FANG+ ETF FoF Direct | 148928 |
| small cap | SBI Small Cap Direct | 125497 |
| mid cap | DSP Midcap Direct | 119071 |
| momentum 30 | MO Nifty 200 Momentum 30 Direct | 149800 |
| multi asset | SBI Multi Asset Allocation Direct | 119843 |
| silver | Nippon India Silver ETF FoF Direct | 149760 |
| flexi cap | Parag Parikh Flexi Cap Direct | 122639 |
| large cap | UTI Nifty 50 Direct | 120716 |

---

## Timezone Schedule

| Region | Local Delivery | UTC Cron |
|---|---|---|
| UAE | 8:00 AM GST | `0 4 * * *` |
| EU / CET | 8:00 AM CET | `0 7 * * *` |
| UK / GMT | 8:00 AM GMT | `0 8 * * *` |
| US East | 8:00 AM EST | `0 13 * * *` |
| US West | 8:00 AM PST | `0 16 * * *` |

---

## Google Sheet Schema

**Sheet name:** `Sheet1`  
**Location:** Private Google Sheet (mkm0007@gmail.com)

| Column | Field | Description |
|---|---|---|
| A | id | UUID v4 — unique user identifier |
| B | name | User's full name |
| C | email | User's email address |
| D | timezone | UAE / EU / UK / US_EAST / US_WEST |
| E | funds | JSON array: [{scheme, name, category}] |
| F | submitted_at | ISO timestamp of signup |
| G | active | TRUE / FALSE — controls report delivery |
| H | dashboard_url | Full URL to user's dashboard page |

---

## GitHub Secrets

| Secret Name | Description |
|---|---|
| `GMAIL_USER` | myfoliopulse@gmail.com |
| `GMAIL_APP_PASSWORD` | Gmail App Password for above account |
| `SHEET_CSV_URL` | Published CSV URL of Google Sheet |

---

## Google Apps Script

**Web App URL:** `https://script.google.com/macros/s/AKfycbzaCu3V4h0OXjPxCnsdmxSVaB_6iQE-iNBxyjJykIGXVEgRzHGl5mmR0TB3rjo9eSN4/exec`  
**Deployed as:** Web App — Execute as Me — Anyone can access  
**Secret token:** `mfp_2026_secret` (in Apps Script + signup.html)

**Endpoints:**
- `GET /exec` — health check, returns `{status: "ok"}`
- `POST /exec` — accepts signup payload, writes to sheet

---

## External APIs Used

| API | Usage | Cost | Rate Limit |
|---|---|---|---|
| mfapi.in/mf/{scheme} | Fetch NAV history | Free | None documented |
| mfapi.in/mf/search | Fund name search in signup form | Free | None documented |
| Gmail SMTP (smtp.gmail.com:465) | Send daily emails | Free | 500/day |
| Google Sheets (CSV publish) | Read user database | Free | None |

---

## Free Tier Limits

| Resource | Free Limit | Current Usage | Scales out at |
|---|---|---|---|
| GitHub Actions | 2,000 min/month | ~5 min/day = 150/month | 150+ users |
| GitHub Pages | 1GB storage | <10MB | Never (HTML files are tiny) |
| Gmail SMTP | 500 emails/day | 1/user/day | 500 users |
| Google Sheets | 10M cells | <100 rows | Never |
| mfapi.in | Unlimited | ~10 calls/user/day | Never |

---

## Known Limitations (Demo Version)

1. **Google Sheet CSV is publicly readable** if the URL is known — acceptable for demo, must fix before production
2. **No dashboard authentication** — UUID URL is the only protection
3. **Apps Script secret token** is visible in signup.html browser source
4. **No email verification** — users are activated immediately on signup
5. **No self-service unsubscribe** — users must email to unsubscribe
6. **Benchmark matching** is keyword-based — may not match all fund types
7. **No fund manager / news data** — health score is purely NAV-based

---

## How to Run Locally (Testing)

```bash
# Install dependencies
pip install requests pytz

# Set environment variables
export SHEET_CSV_URL="your-csv-url"
export GMAIL_USER="myfoliopulse@gmail.com"
export GMAIL_APP_PASSWORD="your-app-password"
export RUN_TIMEZONE="ALL"

# Run
cd my-folio-pulse
python scripts/generate_reports.py
```

---

## How to Add a Test User Manually

Add a row to the Google Sheet with:
- `id`: any UUID (e.g. `test-001` for testing)
- `name`: test name
- `email`: your email
- `timezone`: `ALL` (processes in every run)
- `funds`: `[{"scheme":"119063","name":"HDFC Nifty 50 Index Fund - Direct Plan","category":""}]`
- `submitted_at`: today's date
- `active`: `TRUE`
- `dashboard_url`: `https://muralmu.github.io/my-folio-pulse/users/test-001.html`

---

## Deployment Steps (Fresh Setup)

1. Fork / clone `muralmu/my-folio-pulse` repo
2. Enable GitHub Pages (main branch, root folder)
3. Create Google Sheet with correct column headers
4. Deploy Google Apps Script as Web App
5. Update `APPS_SCRIPT_URL` and token in `signup.html`
6. Publish Google Sheet as CSV → copy URL
7. Add GitHub Secrets: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `SHEET_CSV_URL`
8. Set up Gmail App Password for sending account
9. Trigger manual workflow run to test
10. Sign up via the live form to confirm end-to-end

---

*Built entirely on free infrastructure. Zero monthly cost at demo scale.*
