#!/usr/bin/env python3
"""
Gmail email importance classification and period-based summary script.

Uses the gws CLI to fetch emails and classify/summarize them by importance.

Usage:
    python .claude/scripts/email_summary.py [--days N]

    --days N   : Fetch emails from the last N days (1~30, default: 7)
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape


# ─── Importance classification rules ────────────────────────────────────────

# Keywords for spam/promotional detection (in subject or sender)
PROMO_KEYWORDS = [
    "광고", "ad", "(광고)", "unsubscribe", "수신거부", "newsletter",
    "프로모션", "할인", "이벤트", "특가", "쿠폰", "혜택", "sale",
    "offer", "deal", "discount", "무료", "경품", "위클리", "뉴스레터",
    "마케팅", "홍보",
]

PROMO_SENDERS = [
    "noreply@e.coupang", "ebay@reply.ebay", "customermail.microsoft",
    "notifications-noreply@linkedin", "jobs-listings@linkedin",
    "noreply@glassdoor", "newsletter@", "no-reply@e.udemymail",
    "deliver@aladin", "no-reply@hanbit", "aladin.co.kr",
    "onoffmix.com", "sten@sten.or.kr", "aws-marketing-email",
    "subscriptions@medium",
]

# Important sender patterns (work/official)
IMPORTANT_SENDERS = [
    "github.com", "gitlab.com", "jira", "confluence",
    "google.com", "amazon.com", "aws.amazon",
    "nipa.kr", "iitp.kr",
    "greenhouse-mail",  # recruitment results
]

# Keywords requiring immediate action
ACTION_KEYWORDS = [
    "초대", "invitation", "invite", "승인", "approval", "confirm",
    "결제", "payment", "invoice", "청구", "만료", "expire",
    "긴급", "urgent", "중요", "important", "오류", "error",
    "alert", "알림", "경고", "warning", "보안", "security",
    "인터뷰", "interview", "면접", "offer", "제안",
]


def gws(args: list[str]) -> dict:
    """Call gws CLI and return JSON response."""
    result = subprocess.run(
        ["gws"] + args,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"gws error: {result.stderr[:200]}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def gws_triage(query: str, max_results: int = 100) -> list[dict]:
    """Fetch message list via gws gmail +triage --format json."""
    result = subprocess.run(
        ["gws", "gmail", "+triage", "--format", "json", "--query", query, "--max", str(max_results)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"gws error: {result.stderr[:200]}", file=sys.stderr)
        sys.exit(1)
    data = json.loads(result.stdout)
    # +triage JSON: {"messages": [...]} or [...]
    if isinstance(data, list):
        return data
    return data.get("messages", [])


def classify(subject: str, sender: str, snippet: str) -> str:
    """Email importance classification: action / important / info / promo"""
    subject_l = subject.lower()
    sender_l = sender.lower()
    snippet_l = snippet.lower()

    # Check for promotional first
    if any(kw in subject_l for kw in PROMO_KEYWORDS):
        return "promo"
    if any(s in sender_l for s in PROMO_SENDERS):
        return "promo"

    # Immediate action required
    if any(kw in subject_l or kw in snippet_l for kw in ACTION_KEYWORDS):
        return "action"

    # Important senders
    if any(s in sender_l for s in IMPORTANT_SENDERS):
        return "important"

    return "info"


def parse_date(date_str: str) -> datetime:
    """Email Date header → timezone-aware datetime."""
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return datetime.now(timezone.utc)


def fetch_messages(days: int) -> list[dict]:
    """Fetch email metadata for the last N days via GWS CLI (+triage method)."""
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y/%m/%d")
    until = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y/%m/%d")
    query = f"after:{since} before:{until}"

    messages = gws_triage(query, max_results=100)
    if not messages:
        return []

    results = []
    for msg in messages:
        subject = unescape(msg.get("subject", "(no subject)"))
        sender = msg.get("from", "")
        date_str = msg.get("date", "")

        results.append({
            "id": msg.get("id", ""),
            "subject": subject,
            "sender": sender,
            "date": parse_date(date_str) if date_str else datetime.now(timezone.utc),
            "date_str": date_str,
            "snippet": "",
            "category": classify(subject, sender, ""),
        })

    results.sort(key=lambda x: x["date"], reverse=True)
    return results


def group_by_period(messages: list[dict], days: int) -> dict[str, list]:
    """Group messages by time period."""
    now = datetime.now(timezone.utc)
    groups: dict[str, list] = {}

    if days <= 1:
        groups["Today"] = messages
    elif days <= 7:
        for d in range(days):
            day = now - timedelta(days=d)
            label = day.strftime("%-m/%-d (%a)")
            groups[label] = [
                m for m in messages
                if m["date"].date() == day.date()
            ]
    else:
        # Weekly grouping
        week_count = (days + 6) // 7
        for w in range(week_count):
            start = now - timedelta(days=(w + 1) * 7)
            end = now - timedelta(days=w * 7)
            label = f"{start.strftime('%-m/%-d')} ~ {end.strftime('%-m/%-d')}"
            groups[label] = [
                m for m in messages
                if start <= m["date"] <= end
            ]

    return {k: v for k, v in groups.items() if v}


def format_sender(sender: str) -> str:
    """Format sender display: name only or domain."""
    # "Name <email@domain>" format
    m = re.match(r'^"?([^"<]+)"?\s*<', sender)
    if m:
        name = m.group(1).strip().strip('"')
        if name:
            return name[:30]
    # Email only
    m2 = re.search(r'@([\w.]+)', sender)
    if m2:
        return m2.group(0)[:30]
    return sender[:30]


def render(messages: list[dict], days: int) -> str:
    """Generate output string."""
    lines = []
    total = len(messages)

    # Category aggregation
    by_cat: dict[str, list] = defaultdict(list)
    for m in messages:
        by_cat[m["category"]].append(m)

    lines.append(f"📬 Email Summary — Last {days} days ({total} total)")
    lines.append("")

    # ── Summary statistics ────────────────────────
    lines.append("## Category Overview")
    cat_labels = [
        ("action",    "🔴 Immediate Action Required"),
        ("important", "🟡 Important"),
        ("info",      "🔵 Info/Notifications"),
        ("promo",     "⚪ Promotional/Newsletters"),
    ]
    for cat, label in cat_labels:
        count = len(by_cat.get(cat, []))
        if count:
            lines.append(f"  {label}: {count}")
    lines.append("")

    # ── Period + category detail ──────────────────
    groups = group_by_period(messages, days)

    for period, period_msgs in groups.items():
        lines.append(f"## {period} ({len(period_msgs)} emails)")

        period_by_cat: dict[str, list] = defaultdict(list)
        for m in period_msgs:
            period_by_cat[m["category"]].append(m)

        for cat, label in cat_labels:
            cat_msgs = period_by_cat.get(cat, [])
            if not cat_msgs:
                continue
            lines.append(f"\n  {label} ({len(cat_msgs)})")
            for m in cat_msgs:
                sender_short = format_sender(m["sender"])
                date_fmt = m["date"].astimezone().strftime("%m/%d %H:%M")
                lines.append(f"  • [{date_fmt}] {sender_short}")
                lines.append(f"    {m['subject']}")
                if m["snippet"]:
                    lines.append(f"    → {m['snippet'][:80]}...")

        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gmail Email Summary")
    parser.add_argument(
        "--days", "-d", type=int, default=7,
        help="Lookup period (1~30 days, default: 7)",
    )
    args = parser.parse_args()

    days = max(1, min(30, args.days))

    print(f"Fetching emails from the last {days} days...", file=sys.stderr)
    messages = fetch_messages(days)

    if not messages:
        print(f"No emails received in the last {days} days.")
        return

    print(render(messages, days))


if __name__ == "__main__":
    main()
