#!/usr/bin/env python3
"""
台美股每日新聞 Dashboard
生成靜態 HTML 頁面，包含大盤指數與各來源最新新聞
"""

import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
import yfinance as yf

OUTPUT_FILE = Path(__file__).parent / "dashboard.html"
NEWS_PER_SOURCE = 10
NEWS_TOTAL = 20  # 每區塊最多顯示幾則
REQUEST_TIMEOUT = 10
TW_TZ = timezone(timedelta(hours=8))

# ── 指數設定 ─────────────────────────────────────────────
INDICES = [
    {"symbol": "^TWII",  "name": "台股加權指數", "region": "tw"},
    {"symbol": "^TWOII", "name": "櫃買指數",     "region": "tw"},
    {"symbol": "^DJI",   "name": "道瓊工業指數", "region": "us"},
    {"symbol": "^GSPC",  "name": "S&P 500",      "region": "us"},
    {"symbol": "^IXIC",  "name": "那斯達克",     "region": "us"},
    {"symbol": "^RUT",   "name": "羅素 2000",    "region": "us"},
]

# ── 新聞來源 ─────────────────────────────────────────────
TW_FEEDS = [
    ("鉅亨網",         "https://feeds.feedburner.com/cnyes"),
    ("經濟日報",       "https://money.udn.com/rssfeed/news/1001/5591?ch=money"),
    ("Yahoo股市",      "https://tw.news.yahoo.com/rss/finance"),
    ("TechNews投資",   "https://finance.technews.tw/feed/"),
    ("聯合財經",       "https://udn.com/rssfeed/news/2/6644?ch=news"),
    ("Google-台股",    "https://news.google.com/rss/search?q=%E5%8F%B0%E8%82%A1&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ("Google-美股中文","https://news.google.com/rss/search?q=%E7%BE%8E%E8%82%A1&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ("Google-半導體",  "https://news.google.com/rss/search?q=%E5%8D%8A%E5%B0%8E%E9%AB%94+%E8%82%A1%E5%B8%82&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ("Google-AI股",    "https://news.google.com/rss/search?q=AI+%E8%82%A1%E7%A5%A8&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
    ("Seeking Alpha",  "https://seekingalpha.com/market_currents.xml"),
]

US_FEEDS = [
    ("MarketWatch",    "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("CNBC Markets",   "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
    ("Yahoo Finance",  "https://finance.yahoo.com/news/rssindex"),
    ("WSJ Markets",    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("FT Markets",     "https://www.ft.com/markets?format=rss"),
    ("Seeking Alpha",  "https://seekingalpha.com/market_currents.xml"),
    ("Google-Nasdaq",  "https://news.google.com/rss/search?q=nasdaq+sp500&hl=en-US&gl=US&ceid=US:en"),
    ("Google-Fed",     "https://news.google.com/rss/search?q=federal+reserve+interest+rate&hl=en-US&gl=US&ceid=US:en"),
    ("Google-Earnings","https://news.google.com/rss/search?q=earnings+stock+market&hl=en-US&gl=US&ceid=US:en"),
    ("Google-AI Tech", "https://news.google.com/rss/search?q=AI+semiconductor+stocks&hl=en-US&gl=US&ceid=US:en"),
]


# ── 資料抓取 ─────────────────────────────────────────────
def fetch_index(symbol: str) -> dict:
    try:
        t = yf.Ticker(symbol)
        daily = t.history(period="5d", interval="1d")
        if len(daily) < 2:
            return {"price": None}
        price = float(daily["Close"].iloc[-1])
        prev  = float(daily["Close"].iloc[-2])
        chg = price - prev
        pct = chg / prev * 100
        return {"price": price, "change": chg, "pct": pct}
    except Exception:
        return {"price": None}


def fetch_rss(name: str, url: str) -> list[dict]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/rss+xml,application/xml"}
        )
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            raw = r.read()
        root = ET.fromstring(raw)
        ns   = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)
        results = []
        for item in items[:NEWS_PER_SOURCE]:
            title = (item.findtext("title") or item.findtext("atom:title", namespaces=ns) or "").strip()
            link  = (item.findtext("link")  or item.findtext("atom:link", namespaces=ns) or "").strip()
            pub   = (item.findtext("pubDate") or item.findtext("atom:published", namespaces=ns) or "").strip()
            # atom:link is an element with href attr
            if not link:
                el = item.find("atom:link", ns)
                link = el.get("href", "") if el is not None else ""
            if title and link:
                results.append({"title": title, "link": link, "pub": pub, "source": name})
        return results
    except Exception as e:
        print(f"  [skip] {name}: {e}")
        return []


def fmt_time(pub_str: str) -> str:
    """把 RSS pubDate 轉成易讀格式"""
    if not pub_str:
        return ""
    fmts = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(pub_str, fmt)
            dt = dt.astimezone(TW_TZ)
            return dt.strftime("%m/%d %H:%M")
        except Exception:
            continue
    return pub_str[:16]


def escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ── HTML 生成 ─────────────────────────────────────────────
def build_index_card(idx: dict, data: dict) -> str:
    sym_id = idx["symbol"].replace("^", "")
    if data["price"] is None:
        return f"""
        <div class="index-card" id="card-{sym_id}">
          <div class="index-name">{idx['name']}</div>
          <div class="index-price na" id="price-{sym_id}">N/A</div>
          <div class="index-change" id="change-{sym_id}"></div>
        </div>"""
    price  = data["price"]
    chg    = data["change"]
    pct    = data["pct"]
    is_tw  = idx["region"] == "tw"
    if is_tw:
        color = "up-tw" if chg >= 0 else "down-tw"
    else:
        color = "up" if chg >= 0 else "down"
    arrow = "▲" if chg >= 0 else "▼"
    return f"""
        <div class="index-card {color}" id="card-{sym_id}" data-region="{idx['region']}">
          <div class="index-name">{idx['name']}</div>
          <div class="index-price" id="price-{sym_id}">{price:,.2f}</div>
          <div class="index-change" id="change-{sym_id}">{arrow} {abs(chg):,.2f} ({pct:+.2f}%)</div>
        </div>"""


def build_news_item(item: dict) -> str:
    title  = escape(item["title"])
    source = escape(item["source"])
    pub    = escape(fmt_time(item["pub"]))
    link   = escape(item["link"])
    return f"""
        <div class="news-item">
          <a href="{link}" target="_blank" rel="noopener">{title}</a>
          <div class="news-meta"><span class="source-tag">{source}</span>{pub}</div>
        </div>"""


def build_html(tw_indices, us_indices, tw_news, us_news) -> str:
    now = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M")

    tw_index_html = "".join(build_index_card(i, d) for i, d in tw_indices)
    us_index_html = "".join(build_index_card(i, d) for i, d in us_indices)
    tw_news_html  = "".join(build_news_item(n) for n in tw_news)
    us_news_html  = "".join(build_news_item(n) for n in us_news)

    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>台美股 Dashboard</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #0f1117; color: #e2e8f0; min-height: 100vh; }}
    header {{ background: #1a1d27; border-bottom: 1px solid #2d3148;
              padding: 16px 24px; display: flex; align-items: center; justify-content: space-between; }}
    header h1 {{ font-size: 1.3rem; font-weight: 700; letter-spacing: .5px; color: #fff; }}
    .updated {{ font-size: .8rem; color: #64748b; }}
    .main {{ padding: 24px; max-width: 1400px; margin: 0 auto; }}

    /* 指數區 */
    .section-label {{ font-size: .75rem; font-weight: 600; letter-spacing: 1px;
                      text-transform: uppercase; color: #64748b; margin-bottom: 12px; }}
    .indices {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 32px; }}
    .index-card {{ background: #1a1d27; border: 1px solid #2d3148; border-radius: 10px;
                   padding: 14px 18px; min-width: 160px; flex: 1; }}
    .index-card.up      {{ border-color: #166534; }}
    .index-card.down    {{ border-color: #7f1d1d; }}
    .index-card.up-tw   {{ border-color: #7f1d1d; }}
    .index-card.down-tw {{ border-color: #166534; }}
    .index-name  {{ font-size: .78rem; color: #94a3b8; margin-bottom: 6px; }}
    .index-price {{ font-size: 1.35rem; font-weight: 700; color: #f1f5f9; }}
    .index-price.na {{ color: #475569; font-size: 1rem; }}
    .index-change {{ font-size: .85rem; margin-top: 4px; }}
    .up      .index-change {{ color: #4ade80; }}
    .down    .index-change {{ color: #f87171; }}
    .up-tw   .index-change {{ color: #f87171; }}
    .down-tw .index-change {{ color: #4ade80; }}

    /* 新聞區 */
    .news-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
    @media (max-width: 900px) {{ .news-grid {{ grid-template-columns: 1fr; }} }}
    .news-col {{ background: #1a1d27; border: 1px solid #2d3148; border-radius: 12px; overflow: hidden; }}
    .col-header {{ padding: 14px 18px; background: #20243a; border-bottom: 1px solid #2d3148;
                   font-weight: 600; font-size: .9rem; display: flex; align-items: center; gap: 8px; }}
    .flag {{ font-size: 1.1rem; }}
    .news-item {{ padding: 12px 18px; border-bottom: 1px solid #1e2235; transition: background .15s; }}
    .news-item:last-child {{ border-bottom: none; }}
    .news-item:hover {{ background: #20243a; }}
    .news-item a {{ color: #c7d2fe; text-decoration: none; font-size: .88rem;
                    line-height: 1.5; display: block; }}
    .news-item a:hover {{ color: #fff; }}
    .news-meta {{ margin-top: 5px; font-size: .75rem; color: #475569; display: flex; align-items: center; gap: 8px; }}
    .source-tag {{ background: #1e2a3a; color: #7dd3fc; padding: 1px 7px;
                   border-radius: 4px; font-size: .72rem; white-space: nowrap; }}
    .divider {{ margin: 0 0 24px 0; border: none; border-top: 1px solid #2d3148; }}
  </style>
</head>
<body>
  <header>
    <h1>📈 台美股 Dashboard</h1>
    <span class="updated">新聞更新：{now} (台北) &nbsp;<span id="live-dot" style="display:none;color:#4ade80;font-size:.85rem;">● 指數即時</span></span>
  </header>
  <div class="main">

    <div class="section-label">🇹🇼 台灣市場指數</div>
    <div class="indices">{tw_index_html}</div>

    <div class="section-label">🇺🇸 美國市場指數</div>
    <div class="indices">{us_index_html}</div>

    <hr class="divider">

    <div class="news-grid">
      <div class="news-col">
        <div class="col-header"><span class="flag">🇹🇼</span> 台股新聞</div>
        {tw_news_html}
      </div>
      <div class="news-col">
        <div class="col-header"><span class="flag">🇺🇸</span> 美股新聞</div>
        {us_news_html}
      </div>
    </div>

  </div>
  <script>
    const TW_SYMS = new Set(["TWII","TWOII"]);

    function fmt(price) {{
      return price.toLocaleString("en-US", {{minimumFractionDigits:2, maximumFractionDigits:2}});
    }}

    async function updateIndices() {{
      try {{
        const resp = await fetch("/api/quote");
        if (!resp.ok) return;
        const data = await resp.json();
        for (const [rawSym, q] of Object.entries(data)) {{
          const sym = rawSym.replace("^","");
          const card   = document.getElementById("card-"   + sym);
          const priceEl= document.getElementById("price-"  + sym);
          const changeEl=document.getElementById("change-" + sym);
          if (!card || q.price == null) continue;
          const isTW  = TW_SYMS.has(sym);
          const up    = q.change >= 0;
          const color = isTW ? (up ? "up-tw" : "down-tw") : (up ? "up" : "down");
          const arrow = up ? "▲" : "▼";
          card.className    = "index-card " + color;
          priceEl.textContent = fmt(q.price);
          changeEl.textContent = arrow + " " + fmt(Math.abs(q.change)) + " (" + (q.pct >= 0 ? "+" : "") + q.pct.toFixed(2) + "%)";
        }}
        document.getElementById("live-dot").style.display = "inline";
      }} catch(e) {{
        console.warn("更新失敗", e);
      }}
    }}

    updateIndices();
    setInterval(updateIndices, 30000);
  </script>
</body>
</html>"""


# ── 主程式 ────────────────────────────────────────────────
def main():
    now = datetime.now(TW_TZ).strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 開始更新 Dashboard...")

    # 抓指數
    print("抓取指數資料...")
    tw_indices = [(i, fetch_index(i["symbol"])) for i in INDICES if i["region"] == "tw"]
    us_indices = [(i, fetch_index(i["symbol"])) for i in INDICES if i["region"] == "us"]

    # 抓台股新聞
    print("抓取台股新聞...")
    tw_news = []
    for name, url in TW_FEEDS:
        items = fetch_rss(name, url)
        tw_news.extend(items)
        print(f"  {name}: {len(items)} 則")

    # 抓美股新聞
    print("抓取美股新聞...")
    us_news = []
    for name, url in US_FEEDS:
        items = fetch_rss(name, url)
        us_news.extend(items)
        print(f"  {name}: {len(items)} 則")

    # 去重（依標題）
    def dedup(news):
        seen, result = set(), []
        for n in news:
            key = n["title"][:40]
            if key not in seen:
                seen.add(key)
                result.append(n)
        return result

    tw_news = dedup(tw_news)[:NEWS_TOTAL]
    us_news = dedup(us_news)[:NEWS_TOTAL]
    print(f"台股新聞共 {len(tw_news)} 則，美股新聞共 {len(us_news)} 則")

    # 生成 HTML
    html = build_html(tw_indices, us_indices, tw_news, us_news)
    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Dashboard 已生成：{OUTPUT_FILE}")

    # 本機執行時自動開啟瀏覽器
    import os
    if not os.getenv("CI"):
        import subprocess
        subprocess.run(["open", str(OUTPUT_FILE)])


if __name__ == "__main__":
    main()
