#!/usr/bin/env python3
"""
gmail_fetch_newsletter.py — Fetch Gmail messages by label and date range via gws CLI.

Outputs a JSON array of messages with decoded body text and extracted links.

Usage:
    uv run python scripts/gmail_fetch_newsletter.py \\
        --label-id LABEL_ID \\
        [--days N]          (default: 7) \\
        [--max-results M]   (default: 30) \\
        [--user EMAIL]      (default: from $USER_EMAIL env or liks79@gmail.com)
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta


DEFAULT_USER = os.environ.get("USER_EMAIL", "liks79@gmail.com")

# ── GWS helpers ──────────────────────────────────────────────────────────────

def _gws(*args: str) -> dict | list:
    """Run a gws command and return parsed JSON. stderr is suppressed."""
    result = subprocess.run(
        ["gws", *args],
        capture_output=True,
        text=True,
    )
    stdout = result.stdout.strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {}


def list_messages(user: str, label_id: str, after_date: str, max_results: int) -> list[dict]:
    params = json.dumps({
        "userId": user,
        "labelIds": [label_id],
        "q": f"after:{after_date}",
        "maxResults": max_results,
    })
    data = _gws("gmail", "users", "messages", "list", "--params", params)
    return data.get("messages", [])


def get_message_full(user: str, msg_id: str) -> dict:
    params = json.dumps({"userId": user, "id": msg_id, "format": "full"})
    return _gws("gmail", "users", "messages", "get", "--params", params)


def list_labels(user: str) -> list[dict]:
    params = json.dumps({"userId": user})
    data = _gws("gmail", "users", "labels", "list", "--params", params)
    return data.get("labels", [])


# ── Parsing helpers ───────────────────────────────────────────────────────────

def get_header(headers: list[dict], name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def decode_part(part: dict) -> tuple[str, str]:
    """Recursively decode a message part. Returns (plain_text, html_text)."""
    mime = part.get("mimeType", "")
    data = part.get("body", {}).get("data", "")
    plain, html = "", ""

    if data:
        try:
            decoded = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
        except Exception:
            decoded = ""
        if mime == "text/plain":
            plain = decoded
        elif mime == "text/html":
            html = decoded

    for subpart in part.get("parts", []):
        sp, sh = decode_part(subpart)
        plain = plain or sp
        html = html or sh

    return plain, html


def html_to_text(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    for entity, char in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                          ("&gt;", ">"), ("&#39;", "'"), ("&quot;", '"'),
                          ("&#8203;", ""), ("&#xFEFF;", "")]:
        text = text.replace(entity, char)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_links(plain: str, html: str) -> list[str]:
    """Extract unique HTTP(S) URLs, filtering noise."""
    combined = plain + " " + html
    raw = re.findall(r"https?://[^\s<>\"')\]]+", combined)
    skip_patterns = re.compile(
        r"(unsubscribe|click\.mail|track\.|pixel\.|beacon\.|email\.mg\.|"
        r"mailchimp|sendgrid|mandrillapp|mailgun|list-manage\.com|"
        r"tracking\.|r\.mail|click\.email|links\.email|go\.mail|"
        r"e\.mail|t\.co/|bit\.ly/[a-zA-Z0-9]{5}$)",
        re.IGNORECASE,
    )
    seen: set[str] = set()
    result: list[str] = []
    for url in raw:
        url = url.rstrip(".,;:!?)")
        if url in seen or len(url) > 400:
            continue
        if skip_patterns.search(url):
            continue
        seen.add(url)
        result.append(url)
    return result[:25]


# ── Main ──────────────────────────────────────────────────────────────────────

def fetch(user: str, label_id: str, days: int, max_results: int) -> list[dict]:
    after_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
    msg_stubs = list_messages(user, label_id, after_date, max_results)
    if not msg_stubs:
        return []

    results = []
    for stub in msg_stubs:
        msg_id = stub["id"]
        full = get_message_full(user, msg_id)
        if not full or "payload" not in full:
            continue

        headers = full["payload"].get("headers", [])
        plain, html = decode_part(full["payload"])
        body_text = plain if plain.strip() else html_to_text(html)
        links = extract_links(plain, html)

        results.append({
            "id": msg_id,
            "from": get_header(headers, "From"),
            "subject": get_header(headers, "Subject"),
            "date": get_header(headers, "Date"),
            "snippet": full.get("snippet", ""),
            "body_text": body_text[:4000],
            "links": links,
        })

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", default=DEFAULT_USER)
    parser.add_argument("--label-id", required=True, help="Gmail label ID (e.g. Label_39)")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days")
    parser.add_argument("--max-results", type=int, default=30, help="Max messages to fetch")
    parser.add_argument("--list-labels", action="store_true", help="Print all labels and exit")
    args = parser.parse_args()

    if args.list_labels:
        labels = list_labels(args.user)
        print(json.dumps(labels, ensure_ascii=False, indent=2))
        return

    messages = fetch(args.user, args.label_id, args.days, args.max_results)
    print(json.dumps(messages, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
