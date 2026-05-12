from http.server import BaseHTTPRequestHandler
import json
import yfinance as yf
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

SYMBOLS = ["^TWII", "^TWOII", "^DJI", "^GSPC", "^IXIC", "^RUT"]
TW_SYMS = {"^TWII", "^TWOII"}
TW_TZ   = ZoneInfo("Asia/Taipei")
ET_TZ   = ZoneInfo("America/New_York")


def market_open(sym):
    if sym in TW_SYMS:
        now = datetime.now(TW_TZ)
        if now.weekday() >= 5:
            return False
        return dtime(9, 0) <= now.time() < dtime(13, 30)
    else:
        now = datetime.now(ET_TZ)
        if now.weekday() >= 5:
            return False
        return dtime(9, 30) <= now.time() < dtime(16, 0)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            results = {}
            for sym in SYMBOLS:
                try:
                    t = yf.Ticker(sym)
                    daily = t.history(period="5d", interval="1d")
                    if len(daily) < 2:
                        continue
                    if market_open(sym):
                        intra = t.history(period="1d", interval="1m")
                        if not intra.empty:
                            price = float(intra["Close"].iloc[-1])
                            if intra.index[-1].date() == daily.index[-1].date():
                                prev = float(daily["Close"].iloc[-2])
                            else:
                                prev = float(daily["Close"].iloc[-1])
                        else:
                            price = float(daily["Close"].iloc[-1])
                            prev = float(daily["Close"].iloc[-2])
                    else:
                        price = float(daily["Close"].iloc[-1])
                        prev = float(daily["Close"].iloc[-2])
                    chg = price - prev
                    pct = chg / prev * 100
                    results[sym] = {"price": price, "change": chg, "pct": pct}
                except Exception:
                    continue

            body = json.dumps(results).encode()
            self.send_response(200)
        except Exception as e:
            body = json.dumps({"error": str(e)}).encode()
            self.send_response(500)

        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
