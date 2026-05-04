#!/usr/bin/env python3
"""
company_research.py — Generate a structured research brief for a public company.

Usage:
    python company_research.py "Apple Inc"
    python company_research.py AAPL          # ticker works too

Dependencies:
    pip install yfinance ddgs
"""

import re
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    sys.exit("Missing dependency: pip install yfinance")

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        sys.exit("Missing dependency: pip install ddgs")


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def find_ticker(query: str) -> tuple[str, str]:
    """Return (ticker_symbol, display_name). Raises ValueError if not found."""
    # If query looks like a ticker already, validate it directly
    if re.fullmatch(r"[A-Z]{1,5}", query.upper()):
        t = yf.Ticker(query.upper())
        name = t.info.get("longName") or t.info.get("shortName")
        if name:
            return query.upper(), name

    # Use yfinance search (available in yfinance >= 0.2.x)
    try:
        results = yf.Search(query, max_results=5).quotes
        for r in results:
            symbol = r.get("symbol", "")
            name = r.get("shortname") or r.get("longname") or query
            exchange = r.get("exchDisp", "")
            # Prefer US equity listings
            if symbol and exchange in ("NYSE", "NASDAQ", "NYSEArca", "NasdaqGS", "NasdaqGM"):
                return symbol, name
        # Accept first result if no US exchange matched
        if results:
            r = results[0]
            return r["symbol"], r.get("shortname") or r.get("longname") or query
    except Exception:
        pass

    # Fallback: ask the user
    raise ValueError(
        f"Could not automatically resolve a ticker for '{query}'. "
        "Try passing the ticker symbol directly (e.g. AAPL)."
    )


def fetch_yahoo_data(ticker_symbol: str) -> dict:
    """Return info dict and news list from Yahoo Finance."""
    t = yf.Ticker(ticker_symbol)
    info = t.info or {}
    news = t.news or []
    return {"info": info, "news": news[:8]}


def ddg_search(query: str, max_results: int = 4) -> list[dict]:
    """DuckDuckGo text search; returns list of result dicts."""
    try:
        return DDGS().text(query, max_results=max_results) or []
    except Exception as e:
        print(f"  [warning] search failed: {e}")
        return []


def process_news_items(news_list: list) -> list[dict]:
    """Normalize yfinance news items into consistent dicts (handles old flat and new nested format)."""
    items = []
    for item in news_list:
        c = item.get("content") or item
        title = c.get("title") or ""
        if not title:
            continue
        url = (
            (c.get("clickThroughUrl") or {}).get("url")
            or (c.get("canonicalUrl") or {}).get("url")
            or c.get("link") or c.get("url") or ""
        )
        provider = c.get("provider") or {}
        source = provider.get("displayName") or c.get("publisher") or c.get("source") or extract_domain(url)
        pub = c.get("pubDate") or c.get("displayTime")
        ts = c.get("providerPublishTime") or c.get("published")
        items.append({"title": title, "url": url, "source": source, "date": fmt_timestamp(pub or ts)})
    return items


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_market_cap(value) -> str:
    if not value:
        return "N/A"
    if value >= 1e12:
        return f"${value / 1e12:.2f}T"
    if value >= 1e9:
        return f"${value / 1e9:.2f}B"
    return f"${value / 1e6:.0f}M"


def fmt_timestamp(ts) -> str:
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    if isinstance(ts, str):
        return ts[:10]
    return "—"


def extract_domain(url: str) -> str:
    m = re.search(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1) if m else url


def sanitize_filename(name: str) -> str:
    safe = re.sub(r'[^\w\s-]', '', name).strip()
    return re.sub(r'\s+', '_', safe)


# ---------------------------------------------------------------------------
# Brief assembly
# ---------------------------------------------------------------------------

def build_brief(
    company_name: str,
    ticker_symbol: str,
    yahoo: dict,
    revenue_results: list[dict],
    risk_results: list[dict],
) -> str:
    info = yahoo["info"]
    news = yahoo["news"]

    full_name = info.get("longName") or info.get("shortName") or company_name
    description = info.get("longBusinessSummary") or "_No description available from Yahoo Finance._"
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    exchange = info.get("exchange", "N/A")
    cap_str = fmt_market_cap(info.get("marketCap"))
    today = datetime.now().strftime("%Y-%m-%d")

    parts: list[str] = [
        f"# Research Brief: {full_name} ({ticker_symbol})",
        f"*Generated: {today}*",
        "",
        "---",
        "",
        "## Overview",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| **Sector** | {sector} |",
        f"| **Industry** | {industry} |",
        f"| **Market Cap** | {cap_str} |",
        f"| **Exchange** | {exchange} |",
        "",
        "---",
        "",
        "## Business Description",
        "",
        description,
        "",
        "---",
        "",
        "## Revenue Model",
        "",
        "_Sourced from web search — review links for full context._",
        "",
    ]

    if revenue_results:
        for i, r in enumerate(revenue_results, 1):
            title = r.get("title") or ""
            body = (r.get("body") or "")[:280].rstrip()
            url = r.get("href") or r.get("url") or ""
            source = extract_domain(url)
            parts += [
                f"**{i}. {title}**",
                "",
                f"{body}…",
                "",
                f"— [{source}]({url})" if url else "",
                "",
            ]
    else:
        parts += ["_No results found._", ""]

    parts += [
        "---",
        "",
        "## Key Risks",
        "",
        "_Sourced from web search — review links for full context._",
        "",
    ]

    if risk_results:
        for i, r in enumerate(risk_results, 1):
            title = r.get("title") or ""
            body = (r.get("body") or "")[:280].rstrip()
            url = r.get("href") or r.get("url") or ""
            source = extract_domain(url)
            parts += [
                f"**{i}. {title}**",
                "",
                f"{body}…",
                "",
                f"— [{source}]({url})" if url else "",
                "",
            ]
    else:
        parts += ["_No results found._", ""]

    parts += [
        "---",
        "",
        "## Recent News",
        "",
    ]

    processed_news = process_news_items(news)
    if processed_news:
        parts += ["| Date | Headline | Source |", "|------|----------|--------|"]
        for item in processed_news:
            headline = f"[{item['title']}]({item['url']})" if item["url"] else item["title"]
            parts.append(f"| {item['date']} | {headline} | {item['source']} |")
        parts.append("")
    else:
        parts += ["_No recent news found._", ""]

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    query = " ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else input("Company name or ticker: ").strip()
    if not query:
        sys.exit("Error: provide a company name or ticker.")

    print(f"\nResearching: {query}")
    print("-" * 44)

    print("[ ] Resolving ticker ...")
    try:
        ticker_symbol, display_name = find_ticker(query)
    except ValueError as e:
        sys.exit(f"Error: {e}")
    print(f"    {display_name} ({ticker_symbol})")

    print("[ ] Fetching data from Yahoo Finance ...")
    yahoo = fetch_yahoo_data(ticker_symbol)

    print("[ ] Searching: revenue model ...")
    revenue = ddg_search(f"{display_name} revenue model business model how does it make money")

    time.sleep(1)  # avoid DDG rate limiting between back-to-back searches
    print("[ ] Searching: key risks ...")
    risks = ddg_search(f"{display_name} key risks investor concerns headwinds challenges 2025")

    print("[ ] Assembling brief ...\n")
    brief = build_brief(query, ticker_symbol, yahoo, revenue, risks)

    # Console output — encode safely for Windows terminals
    print(brief.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding))

    # File output (always UTF-8)
    filename = sanitize_filename(display_name or query) + ".md"
    Path(filename).write_text(brief, encoding="utf-8")
    print(f"\nSaved -> {Path(filename).resolve()}")


if __name__ == "__main__":
    main()
