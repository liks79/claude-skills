#!/usr/bin/env python3
"""
Naver Real Estate Apartment Complex Listing Tracker (apt-watch)

Fetches the current sale/jeonse listing status of a specific apartment complex
via the Naver Real Estate API and generates a Markdown report.
Accumulates snapshots in SQLite to track new and disappeared listings.

Usage:
    uv run --with "httpx[http2]" python .claude/scripts/apt_watch.py <complex_number> [options]

Arguments:
    complex_number   Naver Real Estate complex number
                     Found in the URL: fin.land.naver.com/complexes/<number>

Options:
    --name TEXT      Complex name (auto-extracted from API if not specified)
    --location TEXT  Location label for display (e.g., Seoul Gangnam-gu)
    --type           매매|전세|전체 (default: 전체)
    --output PATH    Output file path (default: 20_AREAS/fortune/apt-watch-<number>-<date>.md)
    --db PATH        SQLite DB path (default: 20_AREAS/fortune/.apt-watch/<number>.db)
    --no-db          Output current snapshot only without saving to DB

Examples:
    uv run --with "httpx[http2]" python .claude/scripts/apt_watch.py 25937
    uv run --with "httpx[http2]" python .claude/scripts/apt_watch.py 25937 --name e편한세상센트레빌 --location 경기 광명시
    uv run --with "httpx[http2]" python .claude/scripts/apt_watch.py 10000 --type 전세 --output 20_AREAS/fortune/my-apt.md

How to find the complex number:
    Click on a complex at Naver Real Estate (fin.land.naver.com) and extract the number from the URL
    e.g.) https://fin.land.naver.com/complexes/25937 → 25937
"""
from __future__ import annotations

import argparse
import json
import re as _re
import sqlite3
import sys
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

# ── Naver API configuration ───────────────────────────────────────────────────
_API_URL = "https://fin.land.naver.com/front-api/v1/complex/article/list"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://fin.land.naver.com/",
    "Origin":  "https://fin.land.naver.com",
}

# Transaction type codes
_TRADE_CODE: dict[str, str] = {"매매": "A1", "전세": "B1"}

# ── Price formatting ──────────────────────────────────────────────────────────
def _fmt_price(won: int) -> str:
    """Convert KRW amount → '12억 3,000만원' format (Korean real estate price notation)"""
    if won <= 0:
        return "-"
    man = won // 10_000
    eok = man // 10_000
    rem = man % 10_000
    if eok and rem:
        return f"{eok}억 {rem:,}만원"
    if eok:
        return f"{eok}억"
    return f"{man:,}만원"


_DIRECTION_MAP = {
    "N": "북", "S": "남", "E": "동", "W": "서",
    "NE": "북동", "NW": "북서", "SE": "남동", "SW": "남서",
    "SSE": "남남동", "SSW": "남남서", "NNE": "북북동", "NNW": "북북서",
}

def _decode_dir(code: str) -> str:
    return _DIRECTION_MAP.get(code.upper(), code) if code else "-"


# ── SQLite DB ─────────────────────────────────────────────────────────────────
def _init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            complex_no  TEXT    NOT NULL,
            trade_type  TEXT    NOT NULL,
            fetched_at  TEXT    NOT NULL,
            article_cnt INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS articles (
            article_no   TEXT    NOT NULL,
            complex_no   TEXT    NOT NULL,
            trade_type   TEXT    NOT NULL,
            fetched_at   TEXT    NOT NULL,
            price_won    INTEGER,
            price_text   TEXT,
            supply_area  REAL,
            excl_area    REAL,
            area_name    TEXT,
            floor_info   TEXT,
            direction    TEXT,
            description  TEXT,
            article_url  TEXT,
            dong_name    TEXT,
            PRIMARY KEY (article_no, trade_type, fetched_at)
        );
        CREATE INDEX IF NOT EXISTS idx_art_fetched ON articles(fetched_at);
        CREATE INDEX IF NOT EXISTS idx_art_no      ON articles(article_no);
        CREATE INDEX IF NOT EXISTS idx_art_complex ON articles(complex_no, trade_type);
    """)
    conn.commit()
    return conn


def _save_snapshot(
    conn: sqlite3.Connection,
    articles: list[dict],
    complex_no: str,
    trade_type: str,
    fetched_at: str,
) -> None:
    conn.execute(
        "INSERT INTO snapshots (complex_no, trade_type, fetched_at, article_cnt) VALUES (?,?,?,?)",
        (complex_no, trade_type, fetched_at, len(articles)),
    )
    conn.executemany(
        """INSERT OR REPLACE INTO articles
           (article_no, complex_no, trade_type, fetched_at, price_won, price_text,
            supply_area, excl_area, area_name, floor_info, direction,
            description, article_url, dong_name)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [
            (
                a["article_no"], complex_no, trade_type, fetched_at,
                a["price_won"], a["price_text"],
                a["supply_area"], a["excl_area"], a["area_name"],
                a["floor_info"], a["direction"],
                a["description"], a["article_url"], a["dong_name"],
            )
            for a in articles
        ],
    )
    conn.commit()


def _analyse_changes(
    conn: sqlite3.Connection,
    complex_no: str,
    trade_type: str,
    fetched_at: str,
) -> dict:
    """Analyze new/disappeared listings compared to 1-week and 1-month prior snapshots."""
    now = datetime.fromisoformat(fetched_at)

    cur = conn.execute(
        "SELECT article_no FROM articles WHERE complex_no=? AND trade_type=? AND fetched_at=?",
        (complex_no, trade_type, fetched_at),
    )
    current = {r[0] for r in cur.fetchall()}

    def _detail_current(nos: set) -> list[dict]:
        rows = []
        for no in nos:
            r = conn.execute(
                """SELECT price_won, price_text, area_name, floor_info,
                          direction, article_url, dong_name
                   FROM articles WHERE article_no=? AND trade_type=? AND fetched_at=?""",
                (no, trade_type, fetched_at),
            ).fetchone()
            if r:
                rows.append(dict(r))
        return sorted(rows, key=lambda x: x["price_won"] or 0)

    def _detail_last(nos: set) -> list[dict]:
        rows = []
        for no in nos:
            r = conn.execute(
                """SELECT price_won, price_text, area_name, floor_info,
                          direction, article_url, dong_name, fetched_at
                   FROM articles WHERE article_no=? AND trade_type=?
                   ORDER BY fetched_at DESC LIMIT 1""",
                (no, trade_type),
            ).fetchone()
            if r:
                rows.append(dict(r))
        return sorted(rows, key=lambda x: x["price_won"] or 0)

    result = {}
    for label, delta in [("1 week", timedelta(days=7)), ("1 month", timedelta(days=30))]:
        start = (now - delta).isoformat()
        past = {
            r[0]
            for r in conn.execute(
                """SELECT DISTINCT article_no FROM articles
                   WHERE complex_no=? AND trade_type=? AND fetched_at>=? AND fetched_at<?""",
                (complex_no, trade_type, start, fetched_at),
            ).fetchall()
        }
        result[label] = {
            "new":         _detail_current(current - past),
            "disappeared": _detail_last(past - current),
        }
    return result


# ── Naver API calls ───────────────────────────────────────────────────────────
def _make_client():
    """HTTP/2 client (compatible with Naver API)."""
    try:
        import httpx
    except ImportError:
        print(
            "Error: httpx is not installed.\n"
            "Run with: uv run --with 'httpx[http2]'",
            file=sys.stderr,
        )
        sys.exit(1)

    ts = int(time.time() * 1000)
    cookies = {
        "PROP_TEST_KEY": f"{ts}.session",
        "PROP_TEST_ID":  "land_session",
    }
    return httpx.Client(http2=True, headers=_HEADERS, cookies=cookies, timeout=20)


def _fetch_complex_name(complex_no: str) -> str:
    """Extract complex name from Naver Real Estate article list API (uses complexName field of first listing)."""
    client = _make_client()
    try:
        payload = {
            "complexNumber":   complex_no,
            "tradeTypes":      ["A1"],   # Try sale first
            "pyeongTypes":     [],
            "dongNumbers":     [],
            "userChannelType": "PC",
            "articleSortType": "PRICE_ASC",
            "size":            1,
            "lastInfo":        [],
            "seed":            str(uuid.uuid4()),
        }
        resp = client.post(_API_URL, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("isSuccess"):
                items = data.get("result", {}).get("list", [])
                if items:
                    name = items[0].get("representativeArticleInfo", {}).get("complexName", "")
                    if name:
                        return str(name)
        # If no sale listings, retry with jeonse
        payload["tradeTypes"] = ["B1"]
        resp = client.post(_API_URL, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("isSuccess"):
                items = data.get("result", {}).get("list", [])
                if items:
                    name = items[0].get("representativeArticleInfo", {}).get("complexName", "")
                    if name:
                        return str(name)
    except Exception as exc:
        print(f"  [WARN] Auto complex name lookup failed: {exc}", file=sys.stderr)
    finally:
        client.close()
    return ""


def _fetch_articles(complex_no: str, trade_code: str) -> list[dict]:
    """Fetch all listings for a complex (pagination + 429 retry)."""
    client = _make_client()
    all_items: list[dict] = []
    last_info: list = []
    seed = str(uuid.uuid4())
    page = 1

    try:
        while True:
            payload = {
                "complexNumber":   complex_no,
                "tradeTypes":      [trade_code],
                "pyeongTypes":     [],
                "dongNumbers":     [],
                "userChannelType": "PC",
                "articleSortType": "PRICE_ASC",
                "size":            20,
                "lastInfo":        last_info,
                "seed":            seed,
            }

            for attempt in range(4):
                resp = client.post(_API_URL, json=payload)
                if resp.status_code in (429, 400):
                    wait = 15 * (attempt + 1)
                    print(f"    [WARN] HTTP {resp.status_code}, retrying in {wait}s...", file=sys.stderr)
                    time.sleep(wait)
                else:
                    break

            resp.raise_for_status()
            data = resp.json()

            if not data.get("isSuccess"):
                print(f"    [ERROR] API error: {data}", file=sys.stderr)
                break

            result = data.get("result", {})
            items  = result.get("list", [])
            if not items:
                break

            all_items.extend(items)
            total = result.get("totalCount", "?")
            print(f"    Page {page}: {len(items)} listings (cumulative {len(all_items)} / total {total})", file=sys.stderr)

            if not result.get("hasNextPage"):
                break

            last_info = result.get("lastInfo", [])
            seed      = result.get("seed", seed)
            page     += 1
            time.sleep(0.8)

    finally:
        client.close()

    return all_items


def _normalize(raw: dict, trade_type: str) -> dict:
    """API response → standardized dict."""
    rep        = raw.get("representativeArticleInfo", {})
    price_info = rep.get("priceInfo", {})
    space_info = rep.get("spaceInfo", {})
    detail     = rep.get("articleDetail", {})

    article_no = rep.get("articleNumber", "")

    # Sale: dealPrice / Jeonse: depositPrice → fallback to dealPrice if missing
    if trade_type == "전세":
        price_won = (
            price_info.get("depositPrice")
            or price_info.get("warrantyPrice")
            or price_info.get("dealPrice")
            or 0
        )
    else:
        price_won = price_info.get("dealPrice", 0) or 0

    # Convert to KRW (handle cases where API returns value in 10,000-won units)
    if isinstance(price_won, (int, float)) and 0 < price_won < 100_000:
        price_won = int(price_won) * 10_000   # 10,000 KRW → KRW

    return {
        "article_no":  article_no,
        "price_won":   int(price_won),
        "price_text":  _fmt_price(int(price_won)),
        "supply_area": float(space_info.get("supplySpace") or 0),
        "excl_area":   float(space_info.get("exclusiveSpace") or 0),
        "area_name":   space_info.get("supplySpaceName") or "",
        "floor_info":  detail.get("floorInfo") or "",
        "direction":   _decode_dir(detail.get("direction") or ""),
        "description": (detail.get("articleFeatureDescription") or "").replace("|", "｜"),
        "dong_name":   rep.get("dongName") or "",
        "article_url": f"https://fin.land.naver.com/articles/{article_no}",
    }


# ── Price statistics ──────────────────────────────────────────────────────────
def _price_stats(articles: list[dict]) -> dict:
    prices = sorted(a["price_won"] for a in articles if a["price_won"] > 0)
    if not prices:
        return {}
    n = len(prices)
    return {
        "min":    prices[0],
        "max":    prices[-1],
        "median": prices[n // 2],
        "count":  n,
    }


def _price_stats_by_area(articles: list[dict]) -> list[dict]:
    """Price statistics by area (area_name). Sorted by area descending."""
    from collections import defaultdict

    groups: dict[str, list[int]] = defaultdict(list)
    for a in articles:
        name = (a.get("area_name") or "").strip()
        if name and a["price_won"] > 0:
            groups[name].append(a["price_won"])

    def _area_num(name: str) -> float:
        m = _re.match(r"(\d+(?:\.\d+)?)", name)
        return float(m.group(1)) if m else 0.0

    result = []
    for area_name, prices in groups.items():
        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        result.append({
            "area_name": area_name,
            "count":     n,
            "min":       prices_sorted[0],
            "max":       prices_sorted[-1],
            "median":    prices_sorted[n // 2],
        })
    return sorted(result, key=lambda x: _area_num(x["area_name"]), reverse=True)


def _mermaid_area_chart(area_stats: list[dict], title: str) -> str:
    """Area-based median price bar chart (xychart-beta)."""
    if not area_stats:
        return ""
    data = area_stats[:10]
    labels = [s["area_name"] + "㎡" for s in data]
    values = [round(s["median"] / 100_000_000, 1) for s in data]
    max_v  = round(max(values) * 1.15, 1)
    label_str = ", ".join(f'"{l}"' for l in labels)
    val_str   = ", ".join(str(v) for v in values)
    return "\n".join([
        "```mermaid",
        "xychart-beta",
        f'    title "{title}"',
        f'    x-axis [{label_str}]',
        f'    y-axis 0 --> {max_v}',
        f'    bar [{val_str}]',
        "```",
    ])


# ── Markdown rendering ────────────────────────────────────────────────────────
def _article_row(a: dict, rank: int | None = None) -> str:
    price = a.get("price_text") or _fmt_price(a.get("price_won", 0))
    area  = a.get("area_name") or "-"
    floor = a.get("floor_info") or "-"
    direc = a.get("direction") or "-"
    dong  = a.get("dong_name") or "-"
    url   = a.get("article_url") or "#"
    if rank is not None:
        desc = (a.get("description") or "-")
        return f"| {rank} | [{price}]({url}) | {area} | {floor} | {direc} | {dong} | {desc} |"
    return f"| [{price}]({url}) | {area} | {floor} | {direc} | {dong} |"


def _render_trade_section(
    trade_label: str,
    articles: list[dict],
    changes: dict | None,
    complex_no: str,
) -> list[str]:
    lines: list[str] = []
    stats = _price_stats(articles)
    source_url = (
        f"https://fin.land.naver.com/complexes/{complex_no}"
        f"?articleTradeTypes={'A1' if trade_label == '매매' else 'B1'}&tab=article"
    )

    lines += [
        f"## {trade_label} Listing Status",
        "",
        f"- **Total Listings**: {len(articles)}  ",
    ]
    if stats:
        lines += [
            f"- **Lowest Asking Price**: {_fmt_price(stats['min'])}  ",
            f"- **Highest Asking Price**: {_fmt_price(stats['max'])}  ",
            f"- **Median Asking Price**: {_fmt_price(stats['median'])}  ",
        ]
    lines += [
        f"- **Source**: [Naver Real Estate]({source_url})",
        "",
    ]

    # Price range comparison by area
    area_stats = _price_stats_by_area(articles)
    if area_stats:
        lines += [
            "### Price Range by Area",
            "",
            "| Area | Listings | Min | Max | Median |",
            "|------|---------|------|------|------|",
        ]
        for s in area_stats:
            lines.append(
                f"| {s['area_name']}㎡ | {s['count']} "
                f"| {_fmt_price(s['min'])} | {_fmt_price(s['max'])} | {_fmt_price(s['median'])} |"
            )
        lines.append("")

        chart = _mermaid_area_chart(area_stats, f"{trade_label} Median Asking Price by Area (100M KRW)")
        if chart:
            lines += [chart, ""]

    # Change analysis
    if changes:
        for period, data in changes.items():
            nc, gc = len(data["new"]), len(data["disappeared"])
            if nc == 0 and gc == 0:
                continue
            lines += [
                f"### Changes in the Last {period}",
                "",
                f"- New listings: **{nc}** | Disappeared: **{gc}**",
                "",
            ]
            if data["new"]:
                lines += [
                    f"#### New ({nc})",
                    "| Asking Price | Area | Floor | Direction | Dong |",
                    "|------|------|------|------|-----|",
                ]
                for a in data["new"][:10]:
                    lines.append(_article_row(a))
                lines.append("")
            if data["disappeared"]:
                lines += [
                    f"#### Disappeared ({gc})",
                    "| Asking Price | Area | Floor | Direction | Dong |",
                    "|------|------|------|------|-----|",
                ]
                for a in data["disappeared"][:10]:
                    lines.append(_article_row(a))
                lines.append("")

    # Full listing (larger area descending → price ascending, show all)
    lines += [
        f"### Full Listing ({len(articles)} · Larger Area First / Price Ascending)",
        "",
        "| Rank | Asking Price | Area | Floor | Direction | Dong | Description |",
        "|------|------|------|------|------|-----|------|",
    ]
    for i, a in enumerate(articles, 1):
        lines.append(_article_row(a, rank=i))
    lines += ["", "---", ""]
    return lines


def render_report(
    complex_no: str,
    complex_name: str,
    location: str,
    fetched_at: str,
    sections: list[tuple[str, list[dict], dict | None]],
) -> str:
    now = datetime.fromisoformat(fetched_at)
    complex_url = f"https://fin.land.naver.com/complexes/{complex_no}"
    lines: list[str] = [
        f"# {location} {complex_name} Listing Status",
        "",
        f"**Complex Number**: {complex_no} · **Complex Name**: [{complex_name}]({complex_url})  ",
        f"**Fetched At**: {now.strftime('%Y-%m-%d %H:%M')}  ",
        "**Data Source**: Naver Real Estate (fin.land.naver.com)  ",
        "**Note**: Based on asking prices (not actual transaction prices)",
        "",
        "---",
        "",
    ]
    for trade_label, articles, changes in sections:
        lines += _render_trade_section(trade_label, articles, changes, complex_no)
    return "\n".join(lines)


# ── Naver Map URL parsing (LZ-String decoding) ────────────────────────────────
_LZ_KEY_BASE64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="


def _lz_decompress(length: int, reset_value: int, get_next_value) -> str:
    """Python port of LZ-String library (Pieroxy) _decompress()."""
    dictionary: dict[int, str] = {}
    enlarge_in  = 4
    dict_size   = 4
    num_bits    = 3
    result: list[str] = []
    data_val      = get_next_value(0)
    data_index    = 1
    data_position = reset_value

    for i in range(3):
        dictionary[i] = chr(i)

    # Read first code
    bits = 0
    maxpower = 4
    power = 1
    while power != maxpower:
        resb = data_val & data_position
        data_position >>= 1
        if data_position == 0:
            data_position = reset_value
            data_val = get_next_value(data_index)
            data_index += 1
        bits |= (1 if resb > 0 else 0) * power
        power <<= 1

    next_code = bits
    c: str
    if next_code == 0:
        bits = 0
        maxpower = 256
        power = 1
        while power != maxpower:
            resb = data_val & data_position
            data_position >>= 1
            if data_position == 0:
                data_position = reset_value
                data_val = get_next_value(data_index)
                data_index += 1
            bits |= (1 if resb > 0 else 0) * power
            power <<= 1
        c = chr(bits)
    elif next_code == 1:
        bits = 0
        maxpower = 65536
        power = 1
        while power != maxpower:
            resb = data_val & data_position
            data_position >>= 1
            if data_position == 0:
                data_position = reset_value
                data_val = get_next_value(data_index)
                data_index += 1
            bits |= (1 if resb > 0 else 0) * power
            power <<= 1
        c = chr(bits)
    elif next_code == 2:
        return ""
    else:
        return ""

    dictionary[3] = c
    w = c
    result.append(c)

    while True:
        if data_index > length:
            return ""

        bits = 0
        maxpower = 1 << num_bits
        power = 1
        while power != maxpower:
            resb = data_val & data_position
            data_position >>= 1
            if data_position == 0:
                data_position = reset_value
                data_val = get_next_value(data_index)
                data_index += 1
            bits |= (1 if resb > 0 else 0) * power
            power <<= 1

        code = bits
        if code == 0:
            bits = 0
            maxpower = 256
            power = 1
            while power != maxpower:
                resb = data_val & data_position
                data_position >>= 1
                if data_position == 0:
                    data_position = reset_value
                    data_val = get_next_value(data_index)
                    data_index += 1
                bits |= (1 if resb > 0 else 0) * power
                power <<= 1
            dictionary[dict_size] = chr(bits)
            dict_size += 1
            code = dict_size - 1
            enlarge_in -= 1
        elif code == 1:
            bits = 0
            maxpower = 65536
            power = 1
            while power != maxpower:
                resb = data_val & data_position
                data_position >>= 1
                if data_position == 0:
                    data_position = reset_value
                    data_val = get_next_value(data_index)
                    data_index += 1
                bits |= (1 if resb > 0 else 0) * power
                power <<= 1
            dictionary[dict_size] = chr(bits)
            dict_size += 1
            code = dict_size - 1
            enlarge_in -= 1
        elif code == 2:
            return "".join(result)

        if enlarge_in == 0:
            enlarge_in = 1 << num_bits
            num_bits += 1

        if code in dictionary:
            entry = dictionary[code]
        elif code == dict_size:
            entry = w + w[0]
        else:
            return ""

        result.append(entry)
        dictionary[dict_size] = w + entry[0]
        dict_size += 1
        enlarge_in -= 1

        if enlarge_in == 0:
            enlarge_in = 1 << num_bits
            num_bits += 1

        w = entry


def _decompress_from_base64(value: str) -> str:
    """Restore string compressed with lz-string compressToBase64()."""
    if not value:
        return ""
    return _lz_decompress(
        len(value),
        32,
        lambda idx: _LZ_KEY_BASE64.index(value[idx]),
    )


def _resolve_short_url(url: str) -> str:
    """Resolve Naver short URL (naver.me/...) to the actual URL."""
    try:
        req = Request(url, method="HEAD")
        req.add_header("User-Agent", _HEADERS["User-Agent"])
        resp = urlopen(req, timeout=10)
        resolved = resp.url
        print(f"  → Short URL resolved: {url} → {resolved[:80]}...", file=sys.stderr)
        return resolved
    except Exception as exc:
        print(f"  [WARN] Short URL resolution failed: {exc}", file=sys.stderr)
        return url


def _extract_complex_from_map_url(naver_map_url: str) -> tuple[str, str]:
    """
    Extract complexId and complexName from a Naver Real Estate /map?...&layer=<lz-base64>... URL.
    Returns: (complex_no, complex_name) — ("", "") if not found
    """
    parsed = urlparse(naver_map_url)
    query  = parse_qs(parsed.query)
    layer_values = query.get("layer")
    if not layer_values:
        return "", ""

    layer_encoded = layer_values[0]
    try:
        decoded = _decompress_from_base64(layer_encoded)
    except Exception as exc:
        print(f"  [WARN] layer decoding failed: {exc}", file=sys.stderr)
        return "", ""

    if not decoded:
        print("  [WARN] layer decoding result is empty.", file=sys.stderr)
        return "", ""

    # Extract complexId
    id_matches = _re.findall(r'"complexId"\s*:\s*"?(\d+)"?', decoded)
    complex_no = id_matches[0] if id_matches else ""

    # Try to extract complexName
    name_matches = _re.findall(r'"complexName"\s*:\s*"([^"]+)"', decoded)
    complex_name = name_matches[0] if name_matches else ""

    if complex_no:
        print(f"  → Extracted complexId={complex_no} from map URL", file=sys.stderr)
        if complex_name:
            print(f"  → complexName={complex_name}", file=sys.stderr)

    return complex_no, complex_name


# ── main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Naver Real Estate Apartment Complex Listing Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("complex_number", help="Naver Real Estate complex number (from URL)")
    parser.add_argument("--name",     default="",     help="Complex name for display")
    parser.add_argument("--location", default="",     help="Location label for display (e.g., Seoul Gangnam-gu)")
    parser.add_argument("--type",     dest="trade_type", default="전체",
                        choices=["매매", "전세", "전체"], help="Transaction type (default: 전체)")
    parser.add_argument("--output",   default=None,   help="Output file path (stdout if not specified)")
    parser.add_argument("--db",       default=None,   help="SQLite DB path")
    parser.add_argument("--no-db",    action="store_true", help="Output current snapshot only without saving to DB")
    args = parser.parse_args()

    # Auto-extract complex number from URL
    raw_input = args.complex_number.strip()
    inferred_name = ""

    # 0. Naver short URL (naver.me/...) → resolve to actual URL first
    if "naver.me/" in raw_input:
        print("  → Naver short URL detected, following redirect...", file=sys.stderr)
        raw_input = _resolve_short_url(raw_input)

    # 1. /complexes/<number> format URL
    url_match = _re.search(r"/complexes/(\d+)", raw_input)
    if url_match:
        complex_no = url_match.group(1)
    # 2. /map?...&layer=<lz-base64>... format (Naver Maps share URL)
    elif "/map?" in raw_input and "layer=" in raw_input:
        print("  → Naver map URL detected, decoding layer parameter...", file=sys.stderr)
        complex_no, inferred_name = _extract_complex_from_map_url(raw_input)
        if not complex_no:
            print(
                "Error: Could not extract complexId from map URL.\n"
                "Enter the complex number directly or use a /complexes/<number> format URL.",
                file=sys.stderr,
            )
            sys.exit(1)
    # 3. Direct number input
    else:
        complex_no = raw_input

    # Complex name priority: --name > URL decoded > API auto-lookup > fallback
    if args.name.strip():
        complex_name = args.name.strip()
    elif inferred_name:
        complex_name = inferred_name
    else:
        print("  → Looking up complex name automatically...", file=sys.stderr)
        fetched_name = _fetch_complex_name(complex_no)
        if fetched_name:
            print(f"  → Complex name: {fetched_name}", file=sys.stderr)
            complex_name = fetched_name
        else:
            complex_name = f"Complex {complex_no}"

    location   = args.location.strip()
    fetched_at = datetime.now().isoformat(timespec="seconds")

    # DB path
    use_db = not args.no_db
    if use_db:
        db_path = Path(args.db) if args.db else Path(f"20_AREAS/fortune/.apt-watch/{complex_no}.db")
    else:
        db_path = None

    conn = _init_db(db_path) if use_db and db_path else None

    # Determine transaction types
    trade_types = (
        ["매매", "전세"] if args.trade_type == "전체"
        else [args.trade_type]
    )

    print(f"[{complex_name} ({complex_no})] Fetching listings...", file=sys.stderr)

    sections: list[tuple[str, list[dict], dict | None]] = []

    for trade_label in trade_types:
        trade_code = _TRADE_CODE[trade_label]
        print(f"  {trade_label} lookup (tradeType={trade_code})...", file=sys.stderr)

        try:
            raw = _fetch_articles(complex_no, trade_code)
        except Exception as exc:
            print(f"  [ERROR] {trade_label} fetch failed: {exc}", file=sys.stderr)
            sections.append((trade_label, [], None))
            continue

        articles = [_normalize(r, trade_label) for r in raw]
        # Sort: larger area descending → price ascending
        def _area_sort_key(a: dict):
            name = (a.get("area_name") or "0").strip()
            m = _re.match(r"(\d+(?:\.\d+)?)", name)
            return float(m.group(1)) if m else 0.0
        articles.sort(key=lambda a: (-_area_sort_key(a), a["price_won"] if a["price_won"] > 0 else 10**15))
        print(f"  → {len(articles)} listings collected", file=sys.stderr)

        changes: dict | None = None
        if conn:
            _save_snapshot(conn, articles, complex_no, trade_label, fetched_at)
            changes = _analyse_changes(conn, complex_no, trade_label, fetched_at)
            new_cnt  = sum(len(v["new"])         for v in changes.values())
            gone_cnt = sum(len(v["disappeared"]) for v in changes.values())
            print(f"  → Change analysis: {new_cnt} new / {gone_cnt} disappeared", file=sys.stderr)

        sections.append((trade_label, articles, changes))

    if conn:
        conn.close()

    if not any(arts for _, arts, _ in sections):
        print(
            f"Error: No listings found for {complex_name}({complex_no}).\n"
            "Check the complex number or try again later.",
            file=sys.stderr,
        )
        sys.exit(1)

    report = render_report(complex_no, complex_name, location, fetched_at, sections)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report saved: {out}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
