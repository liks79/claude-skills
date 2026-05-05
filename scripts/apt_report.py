#!/usr/bin/env python3
"""
Seoul/Metropolitan Area Apartment Price Report Generator

Uses the Ministry of Land, Infrastructure and Transport actual transaction price API (data.go.kr)
to aggregate monthly price trends and generate a Markdown report including
short-term forecasts based on linear regression.

Usage:
    uv run --with PublicDataReader --with pandas --with numpy \\
        python .claude/scripts/apt_report.py <region> [options]

Arguments:
    region          Region name (e.g., Gangnam-gu, Mapo-gu, Bundang-gu, Yeonsu-gu)

Options:
    --months N      Analysis period in months (default: 12)
    --type          매매|전세|전체 (default: 매매; Korean trade type codes)
    --forecast N    Forecast months (default: 6, 0 to skip forecast)
    --output PATH   Output file path (stdout if not specified)

Environment:
    DATA_GO_KR_API_KEY   data.go.kr general authentication key (required)

Examples:
    uv run --with PublicDataReader --with pandas --with numpy \\
        python .claude/scripts/apt_report.py 강남구
    uv run --with PublicDataReader --with pandas --with numpy \\
        python .claude/scripts/apt_report.py 마포구 --months 24 --type 전세
    uv run --with PublicDataReader --with pandas --with numpy \\
        python .claude/scripts/apt_report.py 분당구 --output reports/apt-분당구-2026.md
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

# ── Legal-dong sigungu codes (5-digit) ───────────────────────────────────────
# Source: Ministry of the Interior and Safety legal-dong code list (sigungu unit)
SIGUNGU_CODES: dict[str, str] = {
    # Seoul Special City - 25 districts
    "종로구":   "11110",
    "중구":     "11140",
    "용산구":   "11170",
    "성동구":   "11200",
    "광진구":   "11215",
    "동대문구": "11230",
    "중랑구":   "11260",
    "성북구":   "11290",
    "강북구":   "11305",
    "도봉구":   "11320",
    "노원구":   "11350",
    "은평구":   "11380",
    "서대문구": "11410",
    "마포구":   "11440",
    "양천구":   "11470",
    "강서구":   "11500",
    "구로구":   "11530",
    "금천구":   "11545",
    "영등포구": "11560",
    "동작구":   "11590",
    "관악구":   "11620",
    "서초구":   "11650",
    "강남구":   "11680",
    "송파구":   "11710",
    "강동구":   "11740",
    # Gyeonggi Province - major sigungu
    "수원시장안구": "41111",
    "수원시권선구": "41113",
    "수원시팔달구": "41115",
    "수원시영통구": "41117",
    "성남시수정구": "41131",
    "성남시중원구": "41133",
    "성남시분당구": "41135",
    "분당구":       "41135",   # shorthand
    "의정부시":     "41150",
    "안양시만안구": "41171",
    "안양시동안구": "41173",
    "부천시":         ["41192", "41194", "41196"],  # Sum of Wonmi-gu, Sosa-gu, Ojeong-gu
    "부천시원미구":   "41192",
    "부천시소사구":   "41194",
    "부천시오정구":   "41196",
    "광명시":       "41210",
    "안산시상록구": "41271",
    "안산시단원구": "41273",
    "고양시덕양구": "41281",
    "고양시일산동구": "41285",
    "고양시일산서구": "41287",
    "일산동구":     "41285",   # shorthand
    "일산서구":     "41287",   # shorthand
    "과천시":       "41290",
    "구리시":       "41310",
    "남양주시":     "41360",
    "오산시":       "41370",
    "시흥시":       "41390",
    "군포시":       "41410",
    "의왕시":       "41430",
    "하남시":       "41450",
    "용인시처인구": "41461",
    "용인시기흥구": "41463",
    "용인시수지구": "41465",
    "수지구":       "41465",   # shorthand
    "파주시":       "41480",
    "김포시":       "41570",
    "화성시":       "41590",
    "광주시":       "41610",
    "양주시":       "41630",
    # Incheon Metropolitan City
    "인천중구":     "28110",
    "인천동구":     "28140",
    "인천미추홀구": "28177",
    "인천연수구":   "28185",
    "연수구":       "28185",   # shorthand
    "인천남동구":   "28200",
    "인천부평구":   "28237",
    "인천계양구":   "28245",
    "인천서구":     "28260",
}


def _get_api_key() -> str:
    key = os.environ.get("DATA_GO_KR_API_KEY", "").strip()
    if not key:
        print(
            "Error: DATA_GO_KR_API_KEY environment variable is not set.\n"
            "Check settings.local.json > env > DATA_GO_KR_API_KEY.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key


def _resolve_region(name: str) -> tuple[str, str | list[str]]:
    """Region name → (canonical name, sigungu code or code list). Includes partial matching."""
    if name in SIGUNGU_CODES:
        return name, SIGUNGU_CODES[name]
    matches = [k for k in SIGUNGU_CODES if name in k]
    if len(matches) == 1:
        canonical = matches[0]
        code = SIGUNGU_CODES[canonical]
        print(f"Auto-matched region name: {canonical}", file=sys.stderr)
        return canonical, code
    if len(matches) > 1:
        print(f"Error: Multiple regions match '{name}': {matches}", file=sys.stderr)
        sys.exit(1)
    print(
        f"Error: Region '{name}' not found.\n"
        f"Supported regions: {', '.join(sorted(SIGUNGU_CODES))}",
        file=sys.stderr,
    )
    sys.exit(1)


def _month_range(months: int) -> tuple[str, str]:
    """(start_YYYYMM, end_YYYYMM) — end is previous month (MOLIT data is 1 month delayed)."""
    today = date.today()
    # Set end to previous month
    if today.month == 1:
        ey, em = today.year - 1, 12
    else:
        ey, em = today.year, today.month - 1

    # Set start to N months ago
    sm = em - months
    sy = ey
    while sm <= 0:
        sm += 12
        sy -= 1

    return f"{sy}{sm:02d}", f"{ey}{em:02d}"


# ── Data fetch ───────────────────────────────────────────────────────────────

def _fetch(api, sigungu_code: str | list[str], trade_type: str, start_ym: str, end_ym: str):
    """Query actual transaction data via PublicDataReader. Aggregates multiple codes. Returns empty DataFrame on failure."""
    import pandas as pd

    codes = sigungu_code if isinstance(sigungu_code, list) else [sigungu_code]
    frames = []
    for code in codes:
        try:
            df = api.get_data(
                property_type="아파트",
                trade_type=trade_type,
                sigungu_code=code,
                start_year_month=start_ym,
                end_year_month=end_ym,
            )
            if df is not None and not df.empty:
                frames.append(df)
        except Exception as exc:
            print(f"  [warn] {code} {trade_type} data fetch failed: {exc}", file=sys.stderr)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]


# ── Aggregation ──────────────────────────────────────────────────────────────

def _parse_price(val: object) -> float | None:
    """Convert value in 10,000-won units → 100 million won. Handles both numeric and string types."""
    try:
        if isinstance(val, (int, float)):
            return float(val) / 10_000
        return float(str(val).replace(",", "").strip()) / 10_000
    except (ValueError, TypeError):
        return None


def _find_col(df, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def aggregate_trade(df) -> list[dict]:
    """Sale transaction DataFrame → monthly aggregation list."""
    import numpy as np
    import pandas as pd

    if df.empty:
        return []

    price_col = _find_col(df, ["거래금액", "거래 금액"])
    area_col  = _find_col(df, ["전용면적", "전용 면적"])
    year_col  = _find_col(df, ["계약년도", "년"])
    month_col = _find_col(df, ["계약월", "월"])

    if not all([price_col, year_col, month_col]):
        print(f"  [warn] Sale transaction columns not found. Actual columns: {list(df.columns)}", file=sys.stderr)
        return []

    df = df.copy()
    df["_price"] = df[price_col].apply(_parse_price)
    df["_area"]  = pd.to_numeric(df[area_col], errors="coerce") if area_col else np.nan
    df["_ym"]    = df[year_col].astype(str) + "-" + df[month_col].astype(str).str.zfill(2)
    df = df.dropna(subset=["_price"])

    result = []
    for ym, g in df.groupby("_ym"):
        prices = g["_price"].values
        areas  = g["_area"].dropna().values
        med    = float(np.median(prices))
        avg_a  = float(np.mean(areas)) if len(areas) > 0 else 0.0
        pyeong = avg_a / 3.3058
        ppp    = int(med * 10_000 / pyeong) if pyeong > 0 else 0
        result.append({
            "ym":              str(ym),
            "count":           len(g),
            "median_eok":      round(med, 1),
            "avg_area":        round(avg_a, 1),
            "price_per_pyeong": ppp,
        })
    return sorted(result, key=lambda x: x["ym"])


_AREA_BUCKETS: list[tuple[str, float, float]] = [
    ("59㎡대",   59.0,   84.0),
    ("84㎡대",   84.0,  102.0),
    ("102㎡대", 102.0,  135.0),
    ("135㎡ 이상", 135.0, 9999.0),
]


def aggregate_by_area_bucket(df) -> list[dict]:
    """Aggregate transactions of 59㎡ or larger by area bucket (sum of last 12 months).

    Returns: [{"bucket": str, "count": int, "median_eok": float, "price_per_pyeong": int}, ...]
    """
    import numpy as np
    import pandas as pd

    if df.empty:
        return []

    price_col = _find_col(df, ["거래금액", "거래 금액"])
    area_col  = _find_col(df, ["전용면적", "전용 면적"])
    year_col  = _find_col(df, ["계약년도", "년"])
    month_col = _find_col(df, ["계약월", "월"])

    if not all([price_col, area_col, year_col, month_col]):
        return []

    df = df.copy()
    df["_price"] = df[price_col].apply(_parse_price)
    df["_area"]  = pd.to_numeric(df[area_col], errors="coerce")
    df["_ym"]    = df[year_col].astype(str) + "-" + df[month_col].astype(str).str.zfill(2)
    df = df.dropna(subset=["_price", "_area"])
    df = df[df["_area"] >= 59.0]

    # Last 12 months only
    recent_yms = sorted(df["_ym"].unique())[-12:]
    df = df[df["_ym"].isin(recent_yms)]

    result = []
    for bucket_name, lo, hi in _AREA_BUCKETS:
        sub = df[(df["_area"] >= lo) & (df["_area"] < hi)]
        if sub.empty:
            continue
        prices = sub["_price"].values
        areas  = sub["_area"].values
        med    = float(np.median(prices))
        avg_a  = float(np.mean(areas))
        pyeong = avg_a / 3.3058
        ppp    = int(med * 10_000 / pyeong) if pyeong > 0 else 0
        result.append({
            "bucket":           bucket_name,
            "count":            len(sub),
            "median_eok":       round(med, 1),
            "price_per_pyeong": ppp,
            "avg_area":         round(avg_a, 1),
        })
    return result


def aggregate_by_complex(df) -> list[dict]:
    """Aggregate transaction status by complex (sum of last 12 months, sorted by transaction count descending).

    Returns: [{"name": str, "count": int, "median_eok": float,
               "avg_area": float, "price_per_pyeong": int}, ...]
    """
    import numpy as np
    import pandas as pd

    if df.empty:
        return []

    name_col  = _find_col(df, ["단지명", "아파트명"])
    price_col = _find_col(df, ["거래금액", "거래 금액"])
    area_col  = _find_col(df, ["전용면적", "전용 면적"])
    year_col  = _find_col(df, ["계약년도", "년"])
    month_col = _find_col(df, ["계약월", "월"])

    if not all([name_col, price_col, year_col, month_col]):
        return []

    df = df.copy()
    df["_price"] = df[price_col].apply(_parse_price)
    df["_area"]  = pd.to_numeric(df[area_col], errors="coerce") if area_col else np.nan
    df["_ym"]    = df[year_col].astype(str) + "-" + df[month_col].astype(str).str.zfill(2)
    df = df.dropna(subset=["_price"])

    # Last 12 months only
    recent_yms = sorted(df["_ym"].unique())[-12:]
    df = df[df["_ym"].isin(recent_yms)]

    result = []
    for name, g in df.groupby(name_col):
        prices = g["_price"].values
        areas  = g["_area"].dropna().values
        med    = float(np.median(prices))
        avg_a  = float(np.mean(areas)) if len(areas) > 0 else 0.0
        pyeong = avg_a / 3.3058
        ppp    = int(med * 10_000 / pyeong) if pyeong > 0 else 0
        result.append({
            "name":             str(name),
            "count":            len(g),
            "median_eok":       round(med, 1),
            "avg_area":         round(avg_a, 1),
            "price_per_pyeong": ppp,
        })
    return sorted(result, key=lambda x: x["count"], reverse=True)


def aggregate_complex_monthly(df) -> dict[str, list[dict]]:
    """Aggregate monthly transaction status by complex (last 12 months).

    Returns: {complex_name: [{"ym": str, "count": int, "median_eok": float}, ...], ...}
    """
    import numpy as np
    import pandas as pd

    if df.empty:
        return {}

    name_col  = _find_col(df, ["단지명", "아파트명"])
    price_col = _find_col(df, ["거래금액", "거래 금액"])
    year_col  = _find_col(df, ["계약년도", "년"])
    month_col = _find_col(df, ["계약월", "월"])

    if not all([name_col, price_col, year_col, month_col]):
        return {}

    df = df.copy()
    df["_price"] = df[price_col].apply(_parse_price)
    df["_ym"]    = df[year_col].astype(str) + "-" + df[month_col].astype(str).str.zfill(2)
    df = df.dropna(subset=["_price"])

    recent_yms = sorted(df["_ym"].unique())[-12:]
    df = df[df["_ym"].isin(recent_yms)]

    result: dict[str, list[dict]] = {}
    for name, gname in df.groupby(name_col):
        monthly = []
        for ym in recent_yms:
            g = gname[gname["_ym"] == ym]
            if g.empty:
                monthly.append({"ym": ym, "count": 0, "median_eok": 0.0})
            else:
                prices = g["_price"].values
                med = float(np.median(prices))
                monthly.append({"ym": ym, "count": len(g), "median_eok": round(med, 1)})
        result[str(name)] = monthly
    return result


def aggregate_jeonse(df) -> list[dict]:
    """Jeonse/monthly rent DataFrame → monthly aggregation list of pure jeonse (deposit-only).

    Filters only rows where monthly rent amount == 0 to capture pure jeonse transactions.
    """
    import numpy as np

    if df.empty:
        return []

    price_col  = _find_col(df, ["보증금액", "보증금", "전세 보증금"])
    rent_col   = _find_col(df, ["월세금액", "월세"])
    year_col   = _find_col(df, ["계약년도", "년"])
    month_col  = _find_col(df, ["계약월", "월"])

    # Filter pure jeonse (no monthly rent)
    if rent_col:
        df = df[df[rent_col].apply(lambda x: _parse_price(x) or 0) == 0]

    if not all([price_col, year_col, month_col]):
        print(f"  [warn] Jeonse columns not found. Actual columns: {list(df.columns)}", file=sys.stderr)
        return []

    df = df.copy()
    df["_price"] = df[price_col].apply(_parse_price)
    df["_ym"]    = df[year_col].astype(str) + "-" + df[month_col].astype(str).str.zfill(2)
    df = df.dropna(subset=["_price"])

    result = []
    for ym, g in df.groupby("_ym"):
        prices = g["_price"].values
        med    = float(np.median(prices))
        result.append({
            "ym":         str(ym),
            "count":      len(g),
            "median_eok": round(med, 1),
        })
    return sorted(result, key=lambda x: x["ym"])


# ── Forecast ─────────────────────────────────────────────────────────────────

def linear_forecast(monthly: list[dict], forecast_months: int = 6) -> list[dict]:
    """N-month forecast via linear regression. Includes 95% confidence interval."""
    import numpy as np

    if len(monthly) < 4:
        return []

    x = np.arange(len(monthly), dtype=float)
    y = np.array([m["median_eok"] for m in monthly])
    coeffs = np.polyfit(x, y, 1)
    y_hat  = np.polyval(coeffs, x)
    std_e  = float(np.std(y - y_hat))

    last_ym = monthly[-1]["ym"]
    ly, lm  = int(last_ym[:4]), int(last_ym[5:])

    result = []
    for i in range(1, forecast_months + 1):
        nm, ny = lm + i, ly
        while nm > 12:
            nm -= 12
            ny += 1
        pred = float(np.polyval(coeffs, len(monthly) - 1 + i))
        result.append({
            "ym":            f"{ny:04d}-{nm:02d}",
            "predicted_eok": round(max(pred, 0.0), 1),
            "lower":         round(max(pred - 1.96 * std_e, 0.0), 1),
            "upper":         round(pred + 1.96 * std_e, 1),
        })
    return result


# ── Change rates ─────────────────────────────────────────────────────────────

def compute_changes(monthly: list[dict]) -> dict:
    if len(monthly) < 2:
        return {}
    latest = monthly[-1]["median_eok"]
    prev   = monthly[-2]["median_eok"]
    mom    = (latest - prev) / prev * 100 if prev else 0.0
    res    = {"latest": latest, "mom": round(mom, 1)}
    if len(monthly) >= 13:
        ya     = monthly[-13]["median_eok"]
        yoy    = (latest - ya) / ya * 100 if ya else 0.0
        res["yoy"]      = round(yoy, 1)
        res["year_ago"] = ya
    return res


# ── Mermaid charts ────────────────────────────────────────────────────────────

def _mermaid_line(
    data: list[dict],
    title: str,
    value_key: str = "median_eok",
    forecast: list[dict] | None = None,
    forecast_key: str = "predicted_eok",
) -> str:
    """Generate xychart-beta line chart. Appends forecast data if provided."""
    if not data:
        return ""

    all_rows = list(data) + (forecast or [])
    labels   = [d["ym"][5:] for d in data]          # "MM" format
    values   = [d[value_key] for d in data]

    if forecast:
        labels += [d["ym"][5:] for d in forecast]
        values += [d[forecast_key] for d in forecast]

    if not values:
        return ""

    min_v = round(max(0.0, min(values) * 0.90), 1)
    max_v = round(max(values) * 1.10, 1)

    label_str = ", ".join(f'"{l}"' for l in labels)
    val_str   = ", ".join(str(v) for v in values)

    return "\n".join([
        "```mermaid",
        "xychart-beta",
        f'    title "{title}"',
        f'    x-axis [{label_str}]',
        f'    y-axis {min_v} --> {max_v}',
        f'    line [{val_str}]',
        "```",
    ])


def _mermaid_bar(
    data: list[dict],
    title: str,
    value_key: str = "count",
    label_key: str = "ym",
    label_slice: int | None = 5,
) -> str:
    """Generate xychart-beta bar chart (for transaction volume, etc.).

    label_slice: If None, uses label_key value as-is; if integer, slices from that position.
    """
    if not data:
        return ""
    if label_slice is not None:
        labels = [d[label_key][label_slice:] for d in data]
    else:
        labels = [d[label_key] for d in data]
    values = [d[value_key] for d in data]
    max_v  = max(round(max(values) * 1.20), 1)
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


# ── Report rendering ──────────────────────────────────────────────────────────

def render_report(
    region: str,
    trade_monthly: list[dict],
    jeonse_monthly: list[dict],
    trade_forecast: list[dict],
    jeonse_forecast: list[dict],
    start_ym: str,
    end_ym: str,
    sigungu_code: str = "",
    trade_area_buckets: list[dict] | None = None,
    trade_complex_stats: list[dict] | None = None,
    trade_complex_monthly: dict[str, list[dict]] | None = None,
) -> str:
    today = date.today().strftime("%Y-%m-%d")
    s_label = f"{start_ym[:4]}-{start_ym[4:]}"
    e_label = f"{end_ym[:4]}-{end_ym[4:]}"

    lines: list[str] = [
        f"# {region} 아파트 가격 리포트",
        "",
        f"**생성일**: {today}  ",
        f"**분석 기간**: {s_label} ~ {e_label}  ",
        "**데이터 출처**: 국토교통부 실거래가 공개시스템 (data.go.kr)  ",
        "**분석 기준**: 아파트 실거래가 중간값",
        "",
        "---",
        "",
    ]

    # ── Sale transaction section ───────────────────────────────────────────
    if trade_monthly:
        lines += [
            "## 매매가격 추세",
            "",
            "> 실거래가 중간값 기준 (단위: 억원)",
            "",
            _mermaid_line(
                trade_monthly,
                f"{region} 아파트 매매 중간가격 (억원)",
                "median_eok",
            ),
            "",
            "| 월 | 거래건수 | 중간가격 | 평균면적 | 평당가격 |",
            "|---|---|---|---|---|",
        ]
        for row in trade_monthly[-12:]:
            ppp = f"{row['price_per_pyeong']:,}원/평" if row["price_per_pyeong"] else "-"
            lines.append(
                f"| {row['ym']} | {row['count']} "
                f"| {row['median_eok']}억원 "
                f"| {row['avg_area']}㎡ "
                f"| {ppp} |"
            )
        lines.append("")

        # Area analysis (59㎡ and above)
        if trade_area_buckets:
            recent_yms = sorted({r["ym"] for r in trade_monthly})[-12:]
            period_label = f"{recent_yms[0]} ~ {recent_yms[-1]}" if recent_yms else ""
            lines += [
                "### 면적별 분석 (59㎡ 이상)",
                "",
                f"> 최근 12개월 실거래 합산 ({period_label})",
                "",
                "| 면적 | 거래건수 | 중간가격 | 평균면적 | 평당가격 |",
                "|------|---------|--------------|--------------|----------|",
            ]
            for b in trade_area_buckets:
                ppp = f"{b['price_per_pyeong']:,}원/평" if b["price_per_pyeong"] else "-"
                lines.append(
                    f"| {b['bucket']} | {b['count']} "
                    f"| {b['median_eok']}억원 "
                    f"| {b['avg_area']}㎡ "
                    f"| {ppp} |"
                )
            lines.append("")

        # Transaction status by complex
        if trade_complex_stats:
            recent_yms = sorted({r["ym"] for r in trade_monthly})[-12:]
            period_label = f"{recent_yms[0]} ~ {recent_yms[-1]}" if recent_yms else ""
            total_count = sum(c["count"] for c in trade_complex_stats)
            top20 = trade_complex_stats[:20]
            top10_chart = trade_complex_stats[:10]
            lines += [
                "### 단지별 거래현황",
                "",
                f"> 최근 12개월 실거래 합산 ({period_label}) · 거래건수 내림차순 · 총 {total_count}건",
                "",
                "| # | 단지명 | 거래건수 | 비율 | 중간가격 | 평균면적 | 평당가격 |",
                "|---|--------|---------|------|--------------|--------------|----------|",
            ]
            def _anchor_id(name: str) -> str:
                """Complex name → Markdown heading anchor ID (spaces→hyphens, strip special chars)."""
                import re as _re
                slug = _re.sub(r"[^\w\s가-힣]", "", name).strip()
                slug = _re.sub(r"\s+", "-", slug)
                return f"appendix-{slug}"

            has_appendix = bool(trade_complex_monthly)
            for i, c in enumerate(top20, 1):
                ppp  = f"{c['price_per_pyeong']:,}원/평" if c["price_per_pyeong"] else "-"
                pct  = round(c["count"] / total_count * 100, 1) if total_count else 0.0
                name_cell = (
                    f"[{c['name']}](#{_anchor_id(c['name'])})"
                    if has_appendix and c["name"] in trade_complex_monthly
                    else c["name"]
                )
                lines.append(
                    f"| {i} | {name_cell} | {c['count']} "
                    f"| {pct}% "
                    f"| {c['median_eok']}억원 "
                    f"| {c['avg_area']}㎡ "
                    f"| {ppp} |"
                )
            if len(trade_complex_stats) > 20:
                lines.append(f"\n> 외 {len(trade_complex_stats) - 20}개 단지 생략")
            lines.append("")

            # Top 10 complex transaction volume bar chart (x-axis: rank number, avoids Korean rendering issues)
            bar_data = [{"ym": str(i + 1), "count": c["count"]} for i, c in enumerate(top10_chart)]
            complex_chart = _mermaid_bar(
                bar_data,
                f"{region} 단지별 거래건수 Top 10 (x=순위)",
                "count",
                label_slice=None,
            )
            if complex_chart:
                lines += [complex_chart, ""]

        # Transaction volume bar chart
        vol_chart = _mermaid_bar(
            trade_monthly[-12:],
            f"{region} 월별 매매 거래량",
            "count",
        )
        if vol_chart:
            lines += ["### 월별 거래량", "", vol_chart, ""]

        ch = compute_changes(trade_monthly)
        if ch:
            mom_sym = "▲" if ch["mom"] >= 0 else "▼"
            lines += [
                "### 변동률",
                "",
                f"- **전월 대비**: {mom_sym} {abs(ch['mom'])}%",
            ]
            if "yoy" in ch:
                yoy_sym = "▲" if ch["yoy"] >= 0 else "▼"
                lines.append(
                    f"- **전년 동월 대비**: {yoy_sym} {abs(ch['yoy'])}%"
                    f" (전년 동월: {ch['year_ago']}억원)"
                )
            lines.append("")

        if trade_forecast:
            lines += [
                "### 6개월 가격 예측",
                "",
                "> ⚠️ 단순 선형 회귀 예측 — 금리·정책·수급 변수 미반영. 참고용으로만 활용하세요.",
                "",
                _mermaid_line(
                    trade_monthly[-6:],
                    f"{region} 매매가격 예측",
                    "median_eok",
                    trade_forecast,
                    "predicted_eok",
                ),
                "",
                "| 월 | 예측 중간가격 | 하한 (95%) | 상한 (95%) |",
                "|---|---|---|---|",
            ]
            for row in trade_forecast:
                lines.append(
                    f"| {row['ym']} | {row['predicted_eok']}억원 "
                    f"| {row['lower']}억원 | {row['upper']}억원 |"
                )
            lines.append("")

        lines += ["---", ""]

    # ── Market summary ─────────────────────────────────────────────────────
    if trade_monthly:
        recent = trade_monthly[-3:]
        avg_cnt = sum(r["count"] for r in recent) / len(recent)
        lines += [
            "## 시장 요약",
            "",
            f"- **매매 거래량** (3개월 평균): {avg_cnt:.0f}건/월",
            f"- **최근 매매 중간가격**: {trade_monthly[-1]['median_eok']}억원 ({trade_monthly[-1]['ym']})",
            "",
            "> **참고**: 이 리포트는 국토교통부 실거래가 데이터 기반 자동 분석입니다.",
            "> 실거래 데이터는 약 1개월 지연됩니다. 투자 결정 전 전문가 상담을 권장합니다.",
            "",
        ]

    # ── Reference links ────────────────────────────────────────────────────
    naver_url = (
        f"https://new.land.naver.com/complexes?cortarNo={sigungu_code}&a=APT&b=A1"
        if sigungu_code
        else "https://new.land.naver.com/"
    )
    lines += [
        "## 참고 링크",
        "",
        f"- [국토교통부 실거래가 공개시스템](https://rt.molit.go.kr/) — 공식 거래가 조회",
        f"- [네이버 부동산 — {region} 매물]({naver_url}) — 현재 호가 매물",
        f"- [KB부동산](https://kbland.kr/) — KB 가격지수 및 시장 동향",
        f"- [한국부동산원 R-ONE](https://www.reb.or.kr/r-one) — 공식 통계 및 가격지수",
        "",
    ]

    # ── Appendix: Monthly transaction status by complex ───────────────────────
    if trade_complex_monthly and trade_complex_stats:
        import re as _re

        def _anchor_id_app(name: str) -> str:
            slug = _re.sub(r"[^\w\s가-힣]", "", name).strip()
            slug = _re.sub(r"\s+", "-", slug)
            return f"appendix-{slug}"

        lines += ["---", "", "## 부록 — 단지별 월별 거래현황", ""]

        # Maintain same order as the complex transaction table (sorted by transaction count descending)
        complex_order = [c["name"] for c in trade_complex_stats if c["name"] in trade_complex_monthly]

        for name in complex_order:
            monthly = trade_complex_monthly[name]
            anchor  = _anchor_id_app(name)
            lines += [f'<a id="{anchor}"></a>', "", f"### {name}", ""]

            # Transaction volume bar chart
            count_data  = [r for r in monthly if r["count"] > 0]
            if count_data:
                cnt_chart = _mermaid_bar(
                    monthly,
                    f"{name} 월별 거래건수",
                    "count",
                )
                if cnt_chart:
                    lines += [cnt_chart, ""]

            # Monthly median sale price line chart (only months with transactions)
            price_data = [r for r in monthly if r["median_eok"] > 0]
            if price_data:
                price_chart = _mermaid_line(
                    [r for r in monthly if r["median_eok"] > 0],
                    f"{name} 월별 매매 중간가격 (억원)",
                    "median_eok",
                )
                if price_chart:
                    lines += [price_chart, ""]

            lines.append("")

    return "\n".join(lines)


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seoul/Metropolitan Area Apartment Price Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("region", help="Region name (e.g., 강남구, 마포구, 분당구)")
    parser.add_argument("--months",   type=int, default=12,       help="Analysis period in months (default: 12)")
    parser.add_argument("--type",     dest="trade_type", default="매매",
                        choices=["매매"],                          help="Transaction type (only 매매 supported)")
    parser.add_argument("--forecast", type=int, default=6,        help="Forecast months (default: 6, 0=skip)")
    parser.add_argument("--output",   default=None,               help="Output file path (stdout if not specified)")
    args = parser.parse_args()

    region, code = _resolve_region(args.region.strip())
    api_key      = _get_api_key()
    start_ym, end_ym = _month_range(args.months)

    code_label = "+".join(code) if isinstance(code, list) else code
    # sigungu_code for render_report is for Naver URL — use first code when multiple codes
    sigungu_code_for_report = code[0] if isinstance(code, list) else code

    print(f"[{region} ({code_label})] Fetching data for {start_ym} ~ {end_ym}...", file=sys.stderr)

    try:
        import PublicDataReader as pdr
    except ImportError:
        print(
            "Error: PublicDataReader is not installed.\n"
            "Run with: uv run --with PublicDataReader --with pandas --with numpy",
            file=sys.stderr,
        )
        sys.exit(1)

    api = pdr.TransactionPrice(service_key=api_key)

    trade_monthly:         list[dict] = []
    jeonse_monthly:        list[dict] = []
    trade_forecast:        list[dict] = []
    jeonse_forecast:       list[dict] = []
    trade_area_buckets:    list[dict] = []
    trade_complex_stats:   list[dict] = []
    trade_complex_monthly: dict[str, list[dict]] = {}

    print("  Fetching sale transactions...", file=sys.stderr)
    df = _fetch(api, code, "매매", start_ym, end_ym)
    trade_monthly         = aggregate_trade(df)
    trade_area_buckets    = aggregate_by_area_bucket(df)
    trade_complex_stats   = aggregate_by_complex(df)
    trade_complex_monthly = aggregate_complex_monthly(df)
    print(f"  → Aggregated {len(trade_monthly)} months, {len(trade_complex_stats)} complexes", file=sys.stderr)
    if args.forecast > 0 and len(trade_monthly) >= 4:
        trade_forecast = linear_forecast(trade_monthly, args.forecast)

    if not trade_monthly:
        print(
            f"Error: No data found for region {region}.\n"
            "Check the API key and region code, or try increasing --months.",
            file=sys.stderr,
        )
        sys.exit(1)

    report = render_report(
        region, trade_monthly, jeonse_monthly,
        trade_forecast, jeonse_forecast,
        start_ym, end_ym,
        sigungu_code=sigungu_code_for_report,
        trade_area_buckets=trade_area_buckets,
        trade_complex_stats=trade_complex_stats,
        trade_complex_monthly=trade_complex_monthly,
    )

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"Report saved: {out}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
