import sys
import json
import re
import urllib.request
from datetime import datetime, timezone, timedelta

TODAY = sys.argv[1]
API_KEY = sys.argv[2]
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
    except Exception as e:
        print(f"  fetch error {url}: {e}")
        return ""

# ── wosrewards.com 専用パーサー ──────────────────────────────────
def parse_wosrewards(html):
    """ACTIVE直後のコード名だけ抽出"""
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    # "ACTIVE ##### CODE" パターン
    codes = re.findall(r'ACTIVE\s+#{0,5}\s*([A-Za-z][A-Za-z0-9]{3,14})', text)
    # 重複除去・EXPIRED以降を除外
    result = []
    seen = set()
    for c in codes:
        if c not in seen and c.upper() not in ('ACTIVE', 'EXPIRED', 'WORKING'):
            seen.add(c)
            result.append(c)
    print(f"  wosrewards parsed: {result}")
    return result

# ── gamesradar / buffbuff などの補助パーサー ──────────────────────
EXPIRED_MARKERS = [
    "Expired Codes", "expired codes", "No Longer Working",
    "have expired", "codes have since expired",
    "Above are some of the more recent",
    "recently expired", "Codes That No Longer",
]

KNOWN_WORDS = {
    "Active","Allow","Also","Amazon","America","Android","Answer","Apple",
    "April","Arena","Article","Asia","Auto","About","Account","After","Again",
    "Back","Ball","Basic","Best","Beyond","Black","Blood","Blog","Build",
    "Call","Canada","Cards","Center","Century","Channel","Check","Chess",
    "Chief","City","Claim","Classic","Click","Close","Coal","Color","Community",
    "Conditions","Connection","Container","Content","Continue","Cookie","Copyright",
    "Codes","Charm","Confirm","Avatar","Player","These","Newest","Service",
    "Manuals","Mythic","Stamina","Raiders","Training","Policy","Speedup","Rewards",
    "Daily","Dark","Data","Date","Default","Design","Desktop","Deutsch","Disney",
    "Discount","Double","Download","Dragon","Duty","Manual","Expedition","Exploration",
    "Early","Earn","Edition","Email","English","Enter","Entertainment","Error",
    "Event","Every","Evil","Exclusive","Expert","Experts","Enhancement","Component",
    "Facebook","Fire","Find","First","Follow","Food","Footer","Force","Form",
    "Frame","Function","Full","Furnace",
    "Games","Gaming","Gate","Gear","Gears","General","Generator","Genshin",
    "Global","Goddess","Gold","Golden","Google","Grand","Guide","Guides",
    "Hard","Head","Header","Hello","Help","Heroes","High","History","Home",
    "Honkai","Horror","Human","Hunter","Hide",
    "Icon","Impact","India","Instagram","Internet","Info","Items",
    "January","Journey","Join","July",
    "Keep","Keys","Kingdom","Knowledge",
    "Language","Later","Launch","Layer","League","Learn","Legacy","Legends",
    "Level","Links","List","Login","Lucky",
    "Magic","Main","Make","Marvel","Math","Meat","Mecha","Meet","Member",
    "Members","Microsoft","Minecraft","Mobile","Monster","Movies","Mystery",
    "Navigation","Netflix","Network","News","Newsletter","Nintendo","Notice","Number",
    "Object","Official","Only","Open","Origin","Other","Overwatch",
    "Party","Path","Payment","Person","Plans","Play","Players","Plus","Pocket",
    "Points","Pokemon","Popular","Portal","Power","Prime","Privacy","Profile",
    "Program","Promise","Question",
    "Rail","Reddit","Redeem","Redeeming","Redemption","Region","Related",
    "Remove","Required","Research","Resources","Review","Reviews","Rivals",
    "Roblox","Save","Search","Season","Secure","Security","Select","Server",
    "Services","Settings","Seven","Share","Show","Simple","Since","Site",
    "Skip","Skin","Smooth","Social","Sports","Spotify","Stars","State","Stay",
    "Steam","Stone","Store","Strategy","Streaming","Strike","String",
    "Subscribe","Subscription","Support",
    "Table","Team","Teams","Tech","Telegram","Terms","There","Third","Three",
    "Tier","TikTok","Tips","Tower","Track","Trending","Twitter","Type",
    "Unit","Unknown","Unlock","Update","Updated","Valorant","Value","Video",
    "Videos","View","Visit","Want","Warcraft","Waves","Welcome","Where",
    "While","Widget","Wood","World","Working","Xbox","YouTube","Zone",
    "Whiteout","Survival","Kingshot","Discord","Minecraft","Warcraft",
    "LOGIN","SUCCESS","ACTIVE","EXPIRED","SPONSORED","START","SUBSCRIPTION",
    "GamesRadar","WhiteoutSurvival","Speedup","Manuals","Mythic","Stamina",
    "Raiders","Training","Policy","Rewards","Newest","Service","Charm",
    "Confirm","Avatar","Player","These","Codes","Chief","Furnace","Gear",
    "Enhancement","Component","Expedition","Exploration","Manual",
}

def is_gift_code(s):
    if len(s) < 4 or len(s) > 16:
        return False
    if s in KNOWN_WORDS or s.lower() in {w.lower() for w in KNOWN_WORDS}:
        return False
    has_digit = bool(re.search(r'\d', s))
    has_mixed = bool(re.search(r'[A-Z]', s[1:])) and bool(re.search(r'[a-z]', s))
    all_upper = s.isupper() and len(s) >= 5
    lower_start_upper = s[0].islower() and bool(re.search(r'[A-Z]', s))
    return has_digit or has_mixed or all_upper or lower_start_upper

def extract_codes_from_site(html):
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    for marker in EXPIRED_MARKERS:
        idx = text.find(marker)
        if idx > 0:
            text = text[:idx]
            break
    results = set()
    for token in text.split():
        c = token.strip('.,;:()[]"\'/\\#')
        if re.match(r'^[A-Za-z][A-Za-z0-9]{3,15}$', c) and is_gift_code(c):
            results.add(c)
    return results

# ── Reddit 速報取得 ───────────────────────────────────────────────
def fetch_reddit_alerts():
    """
    'gift code just dropped' / 'new gift code' タイトルの投稿を取得
    コード抽出は行わず、投稿情報（タイトル・URL・本文冒頭）をそのまま返す
    """
    alerts = []
    urls = [
        "https://www.reddit.com/r/whiteoutsurvival/search.json?q=gift+code+dropped&sort=new&restrict_sr=1&limit=10",
        "https://www.reddit.com/r/whiteoutsurvival/search.json?q=new+gift+code&sort=new&restrict_sr=1&limit=10",
        "https://www.reddit.com/r/whiteoutsurvival/new.json?limit=50",
    ]
    seen_ids = set()
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 WOSCodeTracker/1.0 (personal use)"
            })
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read().decode("utf-8"))
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                d = post.get("data", {})
                title = d.get("title", "").lower()
                post_id = d.get("id", "")
                if post_id in seen_ids:
                    continue
                # タイトルに「gift code」関連ワードが含まれるもの
                if any(w in title for w in [
                    "gift code", "giftcode", "new code", "code dropped",
                    "code just", "promo code", "redeem code"
                ]):
                    seen_ids.add(post_id)
                    alerts.append({
                        "title": d.get("title", ""),
                        "url": "https://www.reddit.com" + d.get("permalink", ""),
                        "body": d.get("selftext", "")[:200],
                        "created": d.get("created_utc", 0),
                    })
        except Exception as e:
            print(f"  reddit fetch error: {e}")

    # 新しい順にソート（最大10件）
    alerts.sort(key=lambda x: x["created"], reverse=True)
    print(f"  reddit alerts: {len(alerts)} posts found")
    return alerts[:10]

# ── メイン処理 ──────────────────────────────────────────────────
print("=== Fetching confirmed codes ===")

confirmed_codes = []

# 1) wosrewards.com（最優先・ACTIVE確定）
wos_html = fetch_url("https://wosrewards.com/")
wos_active = parse_wosrewards(wos_html) if wos_html else []

# 2) 補助サイトでクロスチェック
support_sources = [
    ("https://www.gamesradar.com/games/survival/whiteout-survival-codes-gift/", "gamesradar"),
    ("https://www.dexerto.com/codes/whiteout-survival-codes-3295120/", "dexerto"),
    ("https://buffbuff.com/blog/whiteout-survival-gift-codes", "buffbuff"),
    ("https://www.gamsgo.com/blog/whiteout-survival-gift-codes", "gamsgo"),
    ("https://lootbar.gg/blog/en/whiteout-survival-newest-codes.html", "lootbar"),
    ("https://www.eldorado.gg/blog/whiteout-survival-newest-codes/", "eldorado"),
    ("https://www.pockettactics.com/whiteout-survival/codes", "pockettactics"),
]

support_code_sets = {}
for url, name in support_sources:
    html = fetch_url(url)
    if html:
        codes = extract_codes_from_site(html)
        support_code_sets[name] = codes
        print(f"  {name}: {len(codes)} candidates")
    else:
        support_code_sets[name] = set()
        print(f"  {name}: blocked")

# 既存データ（報酬情報を引き継ぐ）
try:
    with open("codes.json", "r") as f:
        existing_data = json.load(f)
    existing_codes = {c["code"]: c for c in existing_data.get("codes", [])}
except:
    existing_codes = {}

# wosrewardsのACTIVEコードを確定リストに
for code in wos_active:
    entry = existing_codes.get(code, {})
    confirmed_codes.append({
        "code": code,
        "rewards": entry.get("rewards", "報酬情報を確認してください"),
        "deadline": entry.get("deadline"),
        "note": entry.get("note"),
        "verified": True,
    })

# wosrewardsで取れなかった場合のフォールバック：
# 補助サイト3つ以上で確認されたコードを追加
if not wos_active:
    print("  wosrewards fallback: using cross-check")
    from collections import defaultdict
    code_count = defaultdict(set)
    for name, codes in support_code_sets.items():
        for c in codes:
            code_count[c].add(name)
    for code, srcs in sorted(code_count.items(), key=lambda x: -len(x[1])):
        if len(srcs) >= 3:
            entry = existing_codes.get(code, {})
            confirmed_codes.append({
                "code": code,
                "rewards": entry.get("rewards", "報酬情報を確認してください"),
                "deadline": entry.get("deadline"),
                "note": entry.get("note"),
                "verified": False,
            })

print(f"\nConfirmed codes: {len(confirmed_codes)}")
for c in confirmed_codes:
    print(f"  {c['code']}")

# 3) Reddit速報
print("\n=== Fetching Reddit alerts ===")
reddit_alerts = fetch_reddit_alerts()

# 保存
output = {
    "updated": today_str,
    "codes": confirmed_codes,
    "reddit_alerts": reddit_alerts,
}
with open("codes.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\nDone: {len(confirmed_codes)} codes, {len(reddit_alerts)} reddit alerts")
