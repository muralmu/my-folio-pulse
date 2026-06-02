# MyFolioPulse — Production Plan

**Status:** Demo complete and validated  
**Next milestone:** Production-ready for public launch  
**Last updated:** May 2026

---

## What "Production Ready" Means

The demo proves the concept works. Production means:
- Real users can sign up safely
- Data is properly secured
- The system is reliable and monitored
- There is a proper domain and brand presence
- The business model is defined

---

## Phase P1 — Security Hardening

### P1.1 — Replace CSV URL with Proper Auth
**Problem:** Google Sheet published as public CSV — anyone with the URL can read user data  
**Fix:** Migrate to a backend with a proper database  
**Options (all have free tiers):**
- Supabase (Postgres + Auth + API) — recommended
- PlanetScale (MySQL)
- Railway (hosted Postgres)

**Priority:** 🔴 Critical — must be done before public launch

---

### P1.2 — Dashboard Authentication
**Problem:** Dashboards are public URLs protected only by UUID obscurity  
**Fix:** Add login/auth so only the account owner can view their dashboard  
**Options:**
- Supabase Auth (free tier)
- Auth0 (free up to 7,500 users)
- Clerk (free up to 10,000 users)

**Priority:** 🔴 Critical — must be done before public launch

---

### P1.3 — Apps Script Secret Rotation
**Problem:** Current secret token `mfp_2026_secret` is hardcoded in `signup.html` (visible in browser source)  
**Fix:** Move to a server-side form submission handler so the token is never client-side  
**Priority:** 🔴 Critical

---

### P1.4 — Rate Limiting & CAPTCHA
**Problem:** Signup form has no abuse protection  
**Fix:**
- Add Google reCAPTCHA v3 (free)
- Add server-side rate limiting (max 3 signups per IP per hour)
- Add email verification step before activating user

**Priority:** 🟡 Important

---

### P1.5 — Email Verification Flow
**Problem:** Users are activated immediately — no confirmation they own the email  
**Fix:** Send a verification link on signup → only activate after click  
**Priority:** 🟡 Important

---

## Phase P2 — Infrastructure Migration

### P2.1 — Move off GitHub Actions for Report Generation
**Problem:** GitHub Actions free tier (2,000 min/month) will run out at ~200+ users  
**Fix:** Move report generation to a proper scheduled job  
**Options:**
- Railway cron job (free tier available)
- Render cron job (free tier available)
- Vercel serverless functions + cron

**Trigger:** When user base exceeds 150 active users

---

### P2.2 — Real Database
**Problem:** Google Sheet is not a real database — no indexing, no transactions, limited at scale  
**Fix:** Migrate to Supabase Postgres  
**Tables needed:**
```
users         — id, name, email, timezone, created_at, active, verified
user_funds    — user_id, scheme_code, fund_name, added_at
report_logs   — user_id, sent_at, status
```

**Trigger:** When user base exceeds 50 active users or Google Sheet feels painful

---

### P2.3 — Custom Domain
**What:** Replace `muralmu.github.io/my-folio-pulse` with `myfoliopulse.in` or `myfoliopulse.com`  
**Cost:** ~₹800–1,500/year (`.in`) or ~$12/year (`.com`)  
**Steps:**
- Purchase domain (GoDaddy, Namecheap, or Google Domains)
- Point DNS to GitHub Pages or new hosting
- Set up SSL (automatic with GitHub Pages / Vercel)

**Priority:** 🟡 Important for credibility before sharing widely

---

### P2.4 — Transactional Email Service
**Problem:** Gmail SMTP limited to 500 emails/day  
**Fix:** Move to a transactional email provider  
**Options (all have free tiers):**
- Resend (3,000 emails/month free)
- SendGrid (100 emails/day free)
- Mailgun (1,000 emails/month free)

**Trigger:** When user base exceeds 400 active users

---

## Phase P3 — Product Enhancements

### P3.1 — Fund Name Search Improvement
**Problem:** mfapi.in search returns too many irrelevant results  
**Fix:** Add fuzzy matching + filter to only show relevant fund types (no ETFs unless requested, no institutional plans)  
**Priority:** 🟡 Nice to have

---

### P3.2 — WhatsApp Delivery
**What:** Send daily digest via WhatsApp in addition to email  
**How:** WhatsApp Business API (free tier: 1,000 conversations/month)  
**Why:** NRI investors check WhatsApp more than email  
**Priority:** 🟢 High value feature — build after user validation

---

### P3.3 — Unsubscribe Flow
**Problem:** Currently users must email to unsubscribe — no self-service  
**Fix:** Add one-click unsubscribe link in every email → sets `active = false` in DB  
**Priority:** 🔴 Critical for GDPR compliance

---

### P3.4 — User Preferences Page
**What:** Let users update their fund list, timezone, or email without re-signing up  
**How:** Authenticated page (requires P1.2 auth to be done first)  
**Priority:** 🟡 Important for retention

---

### P3.5 — Weekly Summary Mode
**What:** Option to receive a weekly summary instead of daily  
**Why:** Some users may find daily too frequent  
**Priority:** 🟢 Nice to have

---

### P3.6 — Portfolio-Level Insights
**What:** Beyond per-fund health — show overall portfolio diversification, sector exposure, SIP total performance  
**Priority:** 🟢 Nice to have — differentiator for power users

---

## Phase P4 — Business Model

### Option A — Freemium
| Tier | Price | What You Get |
|---|---|---|
| Free | ₹0 | Up to 3 funds, daily email |
| Pro | ₹99/month | Up to 10 funds, WhatsApp + email, weekly summary, preferences page |
| Family | ₹199/month | Up to 5 family members, all Pro features |

### Option B — IFA White Label
Sell to Independent Financial Advisors (IFAs) who want to send branded reports to their clients  
- Monthly subscription per IFA: ₹999–₹2,999/month
- IFA adds their logo, brand colours, client list
- Each client gets a branded daily report

### Option C — NRI Community Partnerships
Partner with NRI community groups, WhatsApp groups, Reddit communities  
- Free tier drives signups
- Pro tier monetises power users

---

## Phase P5 — Legal & Compliance

### P5.1 — Disclaimer
- Add clear "Not a SEBI registered advisor" disclaimer on all pages and emails
- Add "Data sourced from AMFI via mfapi.in — not real-time" note

### P5.2 — Terms of Service
- Basic ToS covering: free service, no financial advice, data usage, termination

### P5.3 — GDPR Compliance (for EU users)
- Email verification required
- One-click unsubscribe
- Data deletion within 30 days of request
- Cookie notice (currently no cookies — easy win)

---

## Launch Checklist

Before sharing publicly:

- [ ] P1.1 — Secure database (no public CSV)
- [ ] P1.2 — Dashboard authentication
- [ ] P1.3 — Remove secret token from client-side code
- [ ] P1.5 — Email verification flow
- [ ] P3.3 — Self-service unsubscribe link in emails
- [ ] P2.3 — Custom domain
- [ ] P5.1 — Disclaimers on all pages
- [ ] P5.2 — Terms of Service page
- [ ] Test with 5–10 real users (friends/family) before public launch

---

## To-Do List (Carry Forward)

| # | Item | Priority | Phase |
|---|---|---|---|
| 1 | Replace CSV URL with authenticated database | 🔴 Critical | P1.1 |
| 2 | Add dashboard login/authentication | 🔴 Critical | P1.2 |
| 3 | Remove Apps Script token from client-side | 🔴 Critical | P1.3 |
| 4 | Self-service unsubscribe in every email | 🔴 Critical | P3.3 |
| 5 | Email verification on signup | 🟡 Important | P1.5 |
| 6 | reCAPTCHA on signup form | 🟡 Important | P1.4 |
| 7 | Custom domain (myfoliopulse.in) | 🟡 Important | P2.3 |
| 8 | User preferences / edit page | 🟡 Important | P3.4 |
| 9 | WhatsApp delivery option | 🟢 Nice to have | P3.2 |
| 10 | Migrate to Supabase at 50+ users | 🟢 Scale trigger | P2.2 |
| 11 | Move off GitHub Actions at 150+ users | 🟢 Scale trigger | P2.1 |
| 12 | IFA white-label offering | 🟢 Business | P4 |
| 13 | GDPR full compliance for EU users | 🟡 Important | P5.3 |
| 14 | Terms of Service page | 🟡 Important | P5.2 |

---

*MyFolioPulse — Demo validated May 2026. Production target: when first 10 real users are onboarded and feedback collected.*
