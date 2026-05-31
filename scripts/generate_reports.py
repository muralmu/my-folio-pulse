import requests
import smtplib
import os
import csv
import json
import io
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pytz

# ── Config ───────────────────────────────────────────────────────────────────
SHEET_CSV_URL = os.environ.get("SHEET_CSV_URL", "")
GMAIL_USER    = os.environ.get("GMAIL_USER", "")
GMAIL_PASS    = os.environ.get("GMAIL_APP_PASSWORD", "")
RUN_TIMEZONE  = os.environ.get("RUN_TIMEZONE", "ALL")  # UAE | EU | UK | US_EAST | US_WEST | ALL

BASE_URL      = "https://muralmu.github.io/my-folio-pulse"

# ── Benchmark map (scheme code → benchmark scheme code + name) ───────────────
BENCHMARKS = {
    # Key = partial match in fund name (lowercase), Value = (scheme, label)
    "nifty 50":         ("120716", "UTI Nifty 50 Direct"),
    "nasdaq":           ("148928", "Mirae FANG+ ETF FoF Direct"),
    "small cap":        ("125497", "SBI Small Cap Direct"),
    "mid cap":          ("119071", "DSP Midcap Direct"),
    "momentum 30":      ("149800", "MO Nifty 200 Momentum 30 Direct"),
    "multi asset":      ("119843", "SBI Multi Asset Allocation Direct"),
    "silver":           ("149760", "Nippon India Silver ETF FoF Direct"),
    "flexi cap":        ("122639", "Parag Parikh Flexi Cap Direct"),
    "large cap":        ("120716", "UTI Nifty 50 Direct"),
}

WEIGHTS = {"1M": 0.10, "3M": 0.15, "6M": 0.20, "1Y": 0.30, "3Y": 0.25}

# ── Sheet Reader ─────────────────────────────────────────────────────────────
def read_users():
    resp = requests.get(SHEET_CSV_URL, timeout=15)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    users = []
    for row in reader:
        if row.get("active", "").strip().upper() == "TRUE":
            try:
                row["funds"] = json.loads(row.get("funds", "[]"))
            except Exception:
                row["funds"] = []
            users.append(row)
    return users

def filter_users_by_timezone(users):
    if RUN_TIMEZONE == "ALL":
        return users
    return [u for u in users if u.get("timezone", "").strip() == RUN_TIMEZONE]

# ── NAV Fetching ─────────────────────────────────────────────────────────────
def fetch_nav(scheme_code):
    url = f"https://api.mfapi.in/mf/{scheme_code}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_nav_on_or_before(nav_list, target_date):
    for entry in nav_list:
        entry_date = datetime.strptime(entry["date"], "%d-%m-%Y").date()
        if entry_date <= target_date:
            return entry
    return None

def calculate_returns(nav_list, current_nav, current_date):
    results = {}
    periods = {"1D": 1, "1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "3Y": 1095}
    for label, days in periods.items():
        past_date = current_date - timedelta(days=days)
        past_entry = get_nav_on_or_before(nav_list, past_date)
        if past_entry:
            past_nav = float(past_entry["nav"])
            change = ((current_nav - past_nav) / past_nav) * 100
            results[label] = round(change, 2)
        else:
            results[label] = None
    return results

def get_benchmark(fund_name):
    name_lower = fund_name.lower()
    for keyword, (scheme, label) in BENCHMARKS.items():
        if keyword in name_lower:
            return scheme, label
    return None, None

# ── Health Scoring ───────────────────────────────────────────────────────────
def compute_health(returns, benchmark_returns):
    score = 50.0
    notes = []
    periods_available = 0

    for period, weight in WEIGHTS.items():
        val = returns.get(period)
        if val is None:
            continue
        periods_available += 1
        contribution = weight * min(max(val, -30), 30)
        score += contribution
        if period in ("1Y", "3Y") and val > 10:
            notes.append(f"strong {period}")
        elif period in ("1Y", "3Y") and val < 0:
            notes.append(f"negative {period}")

    benchmark_delta_note = None
    for period in ("1Y", "3Y"):
        fund_r = returns.get(period)
        bench_r = benchmark_returns.get(period) if benchmark_returns else None
        if fund_r is not None and bench_r is not None:
            delta = fund_r - bench_r
            if period == "1Y":
                score += delta * 0.15
            else:
                score += delta * 0.10
            if abs(delta) >= 2:
                direction = "outperforming" if delta > 0 else "lagging"
                benchmark_delta_note = f"{direction} peer by {abs(delta):.1f}% ({period})"

    score = max(0, min(100, score))

    if score >= 65:
        emoji, label = "🟢", "Healthy"
    elif score >= 40:
        emoji, label = "🟡", "Watch"
    else:
        emoji, label = "🔴", "Concern"

    if notes and benchmark_delta_note:
        oneliner = f"{', '.join(notes[:2]).capitalize()}; {benchmark_delta_note}"
    elif notes:
        oneliner = f"{', '.join(notes[:2]).capitalize()}"
    elif benchmark_delta_note:
        oneliner = benchmark_delta_note.capitalize()
    elif periods_available == 0:
        oneliner = "Insufficient history"
    else:
        oneliner = "Performing in line with expectations"

    return round(score, 1), emoji, label, oneliner

# ── Process One User's Funds ─────────────────────────────────────────────────
def process_user_funds(funds):
    ist = pytz.timezone("Asia/Kolkata")
    today = datetime.now(ist).date()
    report_date = today.strftime("%d %b %Y")
    results = []

    for fund in funds:
        scheme = fund.get("scheme", "")
        name   = fund.get("name", "Unknown Fund")
        try:
            data     = fetch_nav(scheme)
            nav_list = data["data"]
            meta     = data["meta"]

            latest      = nav_list[0]
            current_nav = float(latest["nav"])
            nav_date    = latest["date"]
            current_date = datetime.strptime(nav_date, "%d-%m-%Y").date()

            prev_nav   = float(nav_list[1]["nav"]) if len(nav_list) > 1 else None
            day_change = round(((current_nav - prev_nav) / prev_nav) * 100, 2) if prev_nav else None

            returns = calculate_returns(nav_list, current_nav, current_date)

            bench_scheme, bench_label = get_benchmark(name)
            benchmark_returns = None
            if bench_scheme:
                try:
                    bdata = fetch_nav(bench_scheme)
                    bnav  = float(bdata["data"][0]["nav"])
                    bdate = datetime.strptime(bdata["data"][0]["date"], "%d-%m-%Y").date()
                    benchmark_returns = calculate_returns(bdata["data"], bnav, bdate)
                except Exception:
                    pass

            score, emoji, verdict, oneliner = compute_health(returns, benchmark_returns)

            results.append({
                "name": name, "scheme": scheme,
                "category": meta.get("scheme_category", ""),
                "nav": current_nav, "nav_date": nav_date,
                "day_change": day_change, "returns": returns,
                "benchmark_label": bench_label or "—",
                "benchmark_returns": benchmark_returns,
                "health_score": score, "health_emoji": emoji,
                "health_label": verdict, "health_oneliner": oneliner,
                "status": "ok"
            })
        except Exception as e:
            results.append({"name": name, "scheme": scheme, "status": "error", "error": str(e)})

    return results, report_date

# ── HTML Helpers ─────────────────────────────────────────────────────────────
def color_for(v):
    if v is None: return "#888"
    return "#16a34a" if v >= 0 else "#dc2626"

def arrow_for(v):
    if v is None: return ""
    return "▲" if v >= 0 else "▼"

def fmt_ret(v):
    if v is None: return "—"
    return f"{'+'if v>=0 else ''}{v:.2f}%"

def score_bar(score):
    color = "#16a34a" if score >= 65 else "#d97706" if score >= 40 else "#dc2626"
    return f"""<div style="font-size:11px;color:#888;margin-top:3px;">Score: {score}/100</div>
    <div style="background:#e5e7eb;border-radius:4px;height:5px;margin-top:3px;width:80px;">
      <div style="background:{color};width:{int(score)}%;height:5px;border-radius:4px;"></div>
    </div>"""

# ── Generate HTML Report ─────────────────────────────────────────────────────
def generate_report_html(user_name, fund_results, report_date, dashboard_url, is_email=False):
    ok_funds       = [f for f in fund_results if f["status"] == "ok"]
    healthy_count  = sum(1 for f in ok_funds if f.get("health_label") == "Healthy")
    watch_count    = sum(1 for f in ok_funds if f.get("health_label") == "Watch")
    concern_count  = sum(1 for f in ok_funds if f.get("health_label") == "Concern")
    avg_score      = round(sum(f["health_score"] for f in ok_funds) / len(ok_funds), 1) if ok_funds else 0
    score_color    = "#16a34a" if avg_score >= 65 else "#d97706" if avg_score >= 40 else "#dc2626"

    rows = ""
    for f in fund_results:
        if f["status"] == "error":
            rows += f'<tr><td colspan="11" style="color:#dc2626;padding:12px;">⚠️ {f["name"]} — Failed to fetch: {f.get("error","")}</td></tr>'
            continue

        r  = f["returns"]
        br = f.get("benchmark_returns")
        dc = f["day_change"]

        if f["health_label"] == "Healthy":
            vbg, vborder = "#f0fdf4", "#86efac"
        elif f["health_label"] == "Watch":
            vbg, vborder = "#fffbeb", "#fcd34d"
        else:
            vbg, vborder = "#fff1f2", "#fca5a5"

        # benchmark 1Y delta
        f1y = r.get("1Y"); b1y = br.get("1Y") if br else None
        if f1y is not None and b1y is not None:
            delta = f1y - b1y
            peer_cell = f'<td style="text-align:right;padding:8px 10px;color:{color_for(delta)};font-size:13px;">{arrow_for(delta)} {fmt_ret(delta)}</td>'
        else:
            peer_cell = '<td style="text-align:right;padding:8px 10px;color:#aaa;">—</td>'

        def rc(key):
            v = r.get(key)
            return f'<td style="text-align:right;color:{color_for(v)};padding:8px 10px;font-size:13px;">{fmt_ret(v)}</td>'

        rows += f"""<tr style="border-bottom:1px solid #f0f0f0;">
          <td style="padding:12px 10px;min-width:180px;">
            <div style="font-weight:600;font-size:14px;">{f['name']}</div>
            <div style="font-size:11px;color:#888;margin-top:2px;">{f['category']}</div>
          </td>
          <td style="text-align:right;padding:8px 10px;">
            <div style="font-weight:600;">₹{f['nav']:.4f}</div>
            <div style="font-size:10px;color:#aaa;">{f['nav_date']}</div>
          </td>
          <td style="text-align:right;padding:8px 10px;color:{color_for(dc)};font-weight:600;">{arrow_for(dc)} {fmt_ret(dc)}</td>
          {rc('1W')}{rc('1M')}{rc('3M')}{rc('6M')}{rc('1Y')}{rc('3Y')}
          {peer_cell}
          <td style="padding:10px;min-width:170px;">
            <div style="background:{vbg};border:1px solid {vborder};border-radius:8px;padding:8px 10px;">
              <div style="font-size:13px;font-weight:700;">{f['health_emoji']} {f['health_label']}</div>
              {score_bar(f['health_score'])}
              <div style="font-size:11px;color:#555;margin-top:5px;line-height:1.4;">{f['health_oneliner']}</div>
              <div style="font-size:10px;color:#aaa;margin-top:3px;">vs {f['benchmark_label']}</div>
            </div>
          </td>
        </tr>"""

    dashboard_btn = ""
    if is_email and dashboard_url:
        dashboard_btn = f"""
        <div style="text-align:center;padding:24px 32px;background:#f0f7ff;border-top:1px solid #e0eaff;">
          <a href="{dashboard_url}"
             style="display:inline-block;background:#2563eb;color:#fff;font-weight:700;font-size:15px;
                    padding:13px 32px;border-radius:8px;text-decoration:none;">
            📊 View My Live Dashboard →
          </a>
          <div style="font-size:12px;color:#888;margin-top:10px;">
            Bookmark this link — your portfolio dashboard is always up to date.
          </div>
        </div>"""

    unsubscribe = ""
    if is_email:
        unsubscribe = '<br>To unsubscribe, reply to this email with "Unsubscribe" in the subject.'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>MyFolioPulse — {user_name}'s Report — {report_date}</title>
<style>
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;margin:0;padding:20px;color:#1a1a1a; }}
  .container {{ max-width:1100px;margin:0 auto;background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.08);overflow:hidden; }}
  .header {{ background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:28px 32px; }}
  .header h1 {{ margin:0 0 4px;font-size:20px; }}
  .header p {{ margin:0;opacity:0.8;font-size:14px; }}
  .summary {{ display:flex;gap:16px;padding:20px 32px;background:#f0f7ff;border-bottom:1px solid #e0eaff;flex-wrap:wrap; }}
  .sc {{ background:#fff;border-radius:8px;padding:12px 20px;flex:1;min-width:110px;box-shadow:0 1px 4px rgba(0,0,0,0.06);text-align:center; }}
  .sc .lbl {{ font-size:11px;color:#888;text-transform:uppercase;letter-spacing:0.5px; }}
  .sc .val {{ font-size:22px;font-weight:700;margin-top:4px; }}
  .note {{ font-size:11px;color:#aaa;padding:8px 32px;background:#fafafa;border-bottom:1px solid #f0f0f0; }}
  table {{ width:100%;border-collapse:collapse; }}
  th {{ background:#f8fafc;color:#666;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;padding:10px;text-align:right;border-bottom:2px solid #e5e7eb;white-space:nowrap; }}
  th:first-child {{ text-align:left; }}
  tr:hover {{ background:#fafafa; }}
  .footer {{ padding:16px 32px;font-size:12px;color:#aaa;text-align:center;border-top:1px solid #f0f0f0; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>📊 MyFolioPulse — {user_name}'s Daily Report</h1>
    <p>As of {report_date} &nbsp;·&nbsp; {len(ok_funds)} funds tracked</p>
  </div>
  <div class="summary">
    <div class="sc"><div class="lbl">Avg Health Score</div><div class="val" style="color:{score_color};">{avg_score}</div></div>
    <div class="sc"><div class="lbl">🟢 Healthy</div><div class="val" style="color:#16a34a;">{healthy_count}</div></div>
    <div class="sc"><div class="lbl">🟡 Watch</div><div class="val" style="color:#d97706;">{watch_count}</div></div>
    <div class="sc"><div class="lbl">🔴 Concern</div><div class="val" style="color:#dc2626;">{concern_count}</div></div>
  </div>
  <div class="note">ℹ️ Health verdict is weighted: long-term returns (1Y, 3Y) carry more weight than short-term. Short-term dips alone will not trigger a concern.</div>
  <div style="overflow-x:auto;">
  <table>
    <thead>
      <tr>
        <th style="text-align:left;padding:10px;">Fund</th>
        <th>NAV</th><th>1D</th><th>1W</th><th>1M</th>
        <th>3M</th><th>6M</th><th>1Y</th><th>3Y</th>
        <th>vs Peer (1Y)</th>
        <th style="text-align:left;">Health</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  </div>
  {dashboard_btn}
  <div class="footer">
    Data: <a href="https://mfapi.in" style="color:#2563eb;">mfapi.in</a> &nbsp;·&nbsp;
    Not financial advice &nbsp;·&nbsp;
    <a href="{BASE_URL}" style="color:#2563eb;">MyFolioPulse</a>
    {unsubscribe}
  </div>
</div>
</body>
</html>"""
    return html

# ── Send Email ────────────────────────────────────────────────────────────────
def send_email(to_email, user_name, html_content, report_date):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 MyFolioPulse — Your Daily Report ({report_date})"
    msg["From"]    = f"MyFolioPulse <{GMAIL_USER}>"
    msg["To"]      = to_email
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())
    print(f"  ✉️  Email sent to {to_email}")

# ── Save Dashboard ────────────────────────────────────────────────────────────
def save_dashboard(user_id, html_content):
    os.makedirs("users", exist_ok=True)
    path = f"users/{user_id}.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  💾 Dashboard saved: {path}")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🚀 MyFolioPulse Report Engine — timezone: {RUN_TIMEZONE}")

    if not SHEET_CSV_URL:
        print("❌ SHEET_CSV_URL not set. Exiting.")
        exit(1)

    print("📋 Reading users from Google Sheet...")
    all_users = read_users()
    users     = filter_users_by_timezone(all_users)
    print(f"   {len(all_users)} total users · {len(users)} due a report now")

    if not users:
        print("✅ No users to process for this timezone run.")
        exit(0)

    for user in users:
        name         = user.get("name", "Investor")
        email        = user.get("email", "")
        user_id      = user.get("id", "")
        dashboard_url = user.get("dashboard_url", "")
        funds        = user.get("funds", [])

        print(f"\n👤 Processing: {name} ({email}) — {len(funds)} funds")

        if not funds:
            print("   ⚠️  No funds configured, skipping.")
            continue

        fund_results, report_date = process_user_funds(funds)

        # Generate dashboard HTML (no email button)
        dashboard_html = generate_report_html(name, fund_results, report_date, dashboard_url, is_email=False)
        save_dashboard(user_id, dashboard_html)

        # Generate email HTML (with dashboard button)
        email_html = generate_report_html(name, fund_results, report_date, dashboard_url, is_email=True)

        if email and GMAIL_USER and GMAIL_PASS:
            try:
                send_email(email, name, email_html, report_date)
            except Exception as e:
                print(f"   ❌ Email failed: {e}")
        else:
            print("   ⚠️  Email skipped (missing credentials)")

    print("\n✅ All reports generated.")
