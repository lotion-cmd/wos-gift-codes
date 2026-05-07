import sys
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from collections import defaultdict

TODAY = sys.argv[1]
API_KEY = sys.argv[2]  # 未使用だが引数として受け取る
JST = timezone(timedelta(hours=9))
now = datetime.now(JST)
today_str = now.strftime("%Y-%m-%d %H:%M JST")

def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")
    except:
        return ""

def fetch_rss(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            tree = ET.parse(r)
            root = tree.getroot()
            items = []
            for item in root.findall(".//item")[:8]:
                title = item.findtext("title") or ""
                desc = item.findtext("description") or ""
                items.append(title + " " + desc)
            return items
    except:
        return []

def fetch_reddit(url):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 WOSCodeTracker/1.0 (personal use)"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
            posts = data.get("data", {}).get("children", [])
            results = []
            for post in posts:
                d = post.get("data", {})
                title = d.get("title", "")
                body = d.get("selftext", "")
                if any(w in (title + body).lower() for w in ["gift code", "giftcode", "code"]):
                    results.append(title + " " + body[:300])
            return results
    except:
        return []

# コードパターン（4〜16文字の英数字）
CODE_PATTERN = re.compile(r'\b([A-Z][A-Za-z0-9]{3,15})\b')

# 期限切れを示すワード
EXPIRED_WORDS = [
    "expired", "expire", "no longer", "invalid", "not working",
    "期限切れ", "無効", "使用不可", "終了", "期限終了"
]

def extract_codes_from_text(text, source_name):
    """テキストからコードを抽出し、期限切れ判定も行う"""
    results = []
    # 期限切れセクションを除去
    expired_section = False
    lines = text.split(" ")
    
    for i, line in enumerate(lines):
        # 期限切れセクションに入ったらスキップ
        if any(w in line.lower() for w in ["expired codes", "expired:", "no longer work", "期限切れ"]):
            expired_section = True
        if any(w in line.lower() for w in ["active codes", "working codes", "アクティブ"]):
            expired_section = False
        
        if expired_section:
            continue
            
        # コードらしい文字列を探す
        codes = CODE_PATTERN.findall(line)
        for code in codes:
            # 短すぎる・一般的な英単語は除外
            if len(code) < 4:
                continue
            skip_words = {"HTTP", "URL", "API", "HTML", "JSON", "CSS", "The", "This", "That", 
                         "With", "From", "Your", "Have", "When", "What", "Will", "Here",
                         "Free", "More", "Also", "Just", "Come", "Some", "Each", "Into"}
            if code in skip_words:
                continue
            
            # 周辺テキストに期限切れワードがないか確認
            context = " ".join(lines[max(0,i-3):i+3])
            is_expired = any(w in context.lower() for w in EXPIRED_WORDS)
            
            if not is_expired:
                results.append((code, source_name))
    
    return results

# 各ソースからコードを収集
code_sources = defaultdict(set)  # code -> set of source names

print("Fetching sources...")

# ソース定義（url, source_name）
sources = [
    ("https://wosrewards.com/", "wosrewards"),
    ("https://www.gamesradar.com/games/survival/whiteout-survival-codes-gift/", "gamesradar"),
    ("https://www.dexerto.com/codes/whiteout-survival-codes-3295120/", "dexerto"),
    ("https://buffbuff.com/blog/whiteout-survival-gift-codes", "buffbuff"),
    ("https://www.pockettactics.com/whiteout-survival/codes", "pockettactics"),
    ("https://www.mrguider.org/codes/whiteout-survival-codes-gift/", "mrguider"),
    ("https://www.gamsgo.com/blog/whiteout-survival-gift-codes", "gamsgo"),
    ("https://lootbar.gg/blog/en/whiteout-survival-newest-codes.html", "lootbar"),
    ("https://www.eldorado.gg/blog/whiteout-survival-newest-codes/", "eldorado"),
    ("https://www.whiteoutsurvival.wiki/giftcodes/", "wiki"),
    ("https://digitalrevenuestudio.co", "digitalrevenuestudio"),
    ("https://whiteoutsurvival.app/gift-code/", "wosapp"),
]

for url, name in sources:
    html = fetch_url(url)
    if html:
        # HTMLタグを除去してテキスト化
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        codes = extract_codes_from_text(text, name)
        for code, src in codes:
            code_sources[code].add(src)
        print(f"  {name}: {len(codes)} candidates")
    else:
        print(f"  {name}: blocked")

# Reddit
reddit_results = []
for url in [
    "https://www.reddit.com/r/whiteoutsurvival/search.json?q=gift+code&sort=new&restrict_sr=1&limit=10",
    "https://www.reddit.com/r/whiteoutsurvival/new.json?limit=25",
]:
    posts = fetch_reddit(url)
    reddit_results.extend(posts)

for text in reddit_results:
    codes = extract_codes_from_text(text, "reddit")
    for code, src in codes:
        code_sources[code].add(src)

print(f"Reddit: {len(reddit_results)} posts")

# Google検索RSS
for q in [
    "Whiteout Survival gift code active " + TODAY,
    "Whiteout Survival gift code new today",
    "whiteout survival gift code reddit " + TODAY,
]:
    rss_url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q) + "&hl=en&gl=US&ceid=US:en"
    items = fetch_rss(rss_url)
    for text in items:
        codes = extract_codes_from_text(text, "google_rss")
        for code, src in codes:
            code_sources[code].add(src)

# クロスチェック：2ソース以上で確認されたコードのみ採用
print(f"\nAll candidates: {len(code_sources)}")
valid_codes = []
for code, srcs in code_sources.items():
    if len(srcs) >= 2:
        valid_codes.append({
            "code": code,
            "rewards": "報酬情報を確認してください",
            "deadline": None,
            "note": f"{len(srcs)}ソース確認済み: {', '.join(sorted(srcs))}"
        })
        print(f"  VALID ({len(srcs)} sources): {code}")

print(f"\nValid codes (2+ sources): {len(valid_codes)}")

# 既存データとマージ（報酬情報を保持）
try:
    with open("codes.json", "r") as f:
        existing = json.load(f)
    existing_map = {c["code"]: c for c in existing.get("codes", [])}
except:
    existing_map = {}

# 既存の報酬情報を引き継ぐ
final_codes = []
for c in valid_codes:
    if c["code"] in existing_map:
        existing_entry = existing_map[c["code"]]
        c["rewards"] = existing_entry.get("rewards", c["rewards"])
        c["deadline"] = existing_entry.get("deadline", None)
    final_codes.append(c)

output = {"updated": today_str, "codes": final_codes}
with open("codes.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Updated: {len(final_codes)} codes saved")
