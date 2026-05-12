from http.server import BaseHTTPRequestHandler
import json
import yfinance as yf

SYMBOLS = ["^TWII", "^TWOII", "^DJI", "^GSPC", "^IXIC", "^RUT"]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            results = {}
            for sym in SYMBOLS:
                try:
                    t = yf.Ticker(sym)
                    intra = t.history(period="1d", interval="1m")
                    daily = t.history(period="2d", interval="1d")
                    if not intra.empty and len(daily) >= 2:
                        price = float(intra["Close"].iloc[-1])
                        prev  = float(daily["Close"].iloc[-2])
                    elif not daily.empty:
                        price = float(daily["Close"].iloc[-1])
                        prev  = float(daily["Close"].iloc[-2]) if len(daily) >= 2 else price
                    else:
                        continue
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
