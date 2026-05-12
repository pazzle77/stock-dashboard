from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse

SYMBOLS = "^TWII,^TWOII,^DJI,^GSPC,^IXIC,^RUT"
YF_URL = (
    "https://query1.finance.yahoo.com/v7/finance/quote"
    f"?symbols={urllib.parse.quote(SYMBOLS)}"
    "&fields=regularMarketPrice,regularMarketChange,regularMarketChangePercent"
)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            req = urllib.request.Request(
                YF_URL,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                raw = json.load(r)

            results = {}
            for q in raw.get("quoteResponse", {}).get("result", []):
                sym = q["symbol"]
                results[sym] = {
                    "price": q.get("regularMarketPrice"),
                    "change": q.get("regularMarketChange"),
                    "pct": q.get("regularMarketChangePercent"),
                }

            body = json.dumps(results).encode()
            self.send_response(200)
        except Exception as e:
            body = json.dumps({"error": str(e)}).encode()
            self.send_response(500)

        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
