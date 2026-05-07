import sys
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

TODAY = sys.argv[1]
API_KEY = sys.argv[2]
JST = timezone(timedelta(hours=9))

def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")
    except:
        return ""

def extract_codes(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    matches = re.findall(r".{0,120}[A-Z][A-Za-z0-9]{4,15}\s*[-]\s*.{0,120}", text)
    return matches[:20]

def fetch_rss(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            tree = ET.parse(r)
            root = tree.getroot()
            items = []
            for item in root.findall(".//item")[:5]:
                title = item.findtext("title") or ""
                desc = item.findtext("description") or ""
                items.append(title + " " + desc)
            return items
    except:
        return []

all_results = []

for url in [
    "https://www.gamesradar.com/games/survival/whiteout-survival-codes-gift/",
    "https://www.pockettactics.com/whiteout-survival/codes",
    "https://www.mrguider.org/codes/whiteout-survival-codes-gift/",
]:
    html = fetch_url(url)
    if html:
        all_results.extend(extract_codes(html))

for q in [
    "Whiteout Survival gift code active 2026",
    "Whiteout Survival gift code new today",
    "whiteout survival gift code reddit 2026",
    "Whiteout Survival gift code " + TODAY,
]:
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=en&gl=US&ceid=US:en"
    all_results.extend(fetch_rss(url))

seen = set()
unique = []
for r in all_results:
    key = r[:60]
    if key not in seen and len(r) > 10:
        seen.add(key)
        unique.append(r[:300])

search_text = json.dumps(unique[:30], ensure_ascii=False)

prompt = (
    "今日は" + TODAY + "（日本時間）です。"
    "以下はWhiteout Survivalのギフトコードに関する最新情報です:\n\n"
    + search_text +
    "\n\n上記を精査して" + TODAY + "時点でアクティブなコードのみ抽出してください。"
    "期限切れは絶対に含めないでください。"
    "JSON形式のみで返答（説明不要）: "
    "{\"codes\":[{\"code\":\"コード\",\"rewards\":\"報酬（日本語）\","
    "\"deadline\":\"JST ISO8601またはnull\",\"note\":\"補足またはnull\"}]}"
)

payload = json.dumps({
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 1500,
    "messages": [{"role": "user", "content": prompt}]
}).encode("utf-8")

req = urllib.request.Request(
    "https://api.anthropic.com/v1/messages",
    data=payload,
    headers={
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
        "x-api-key": API_KEY,
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
except Exception as e:
    print("API error:", e)
    try:
        with open("codes.json", "r") as f:
            existing = json.load(f)
        existing["updated"] = datetime.now(JST).strftime("%Y-%m-%d %H:%M JST")
        with open("codes.json", "w") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except:
        pass
    sys.exit(0)

text = ""
for block in data.get("content", []):
    if block.get("type") == "text":
        text += block["text"]

now = datetime.now(JST)
today_str = now.strftime("%Y-%m-%d %H:%M JST")

parsed = None
for pattern in [r"```(?:json)?\s*([\s\S]*?)\s*```", r"\{[\s\S]*?\"codes\"[\s\S]*?\}"]:
    m = re.search(pattern, text)
    if m:
        candidate = m.group(1) if m.lastindex else m.group(0)
        try:
            parsed = json.loads(candidate)
            break
        except:
            pass
if not parsed:
    try:
        parsed = json.loads(text.strip())
    except:
        pass

if not parsed or not isinstance(parsed.get("codes"), list) or len(parsed["codes"]) == 0:
    try:
        with open("codes.json", "r") as f:
            existing = json.load(f)
        existing["updated"] = today_str
        with open("codes.json", "w") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
    except:
        pass
    sys.exit(0)

valid = []
for c in parsed["codes"]:
    if c.get("deadline"):
        try:
            dl = datetime.fromisoformat(c["deadline"].replace("Z", "+00:00"))
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=JST)
            if dl <= now:
                continue
        except:
            pass
    valid.append(c)

output = {"updated": today_str, "codes": valid}
with open("codes.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("Updated:", len(valid), "codes")
