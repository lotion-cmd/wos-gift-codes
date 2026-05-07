import sys
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

TODAY = sys.argv[1]
API_KEY = sys.argv[2]
JST = timezone(timedelta(hours=9))

# APIリクエストのテスト（シンプルなプロンプトのみ）
prompt = "Today is " + TODAY + ". List active Whiteout Survival gift codes as JSON only: {\"codes\":[{\"code\":\"CODE\",\"rewards\":\"rewards\",\"deadline\":null,\"note\":null}]}"

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
        print("API OK:", data.get("stop_reason"))
        text = (data.get("content") or [{}])[0].get("text", "")
        print("Response:", text[:200])
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8")
    print("HTTP Error:", e.code, body[:300])
except Exception as e:
    print("Error:", e)
