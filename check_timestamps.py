import json
from datetime import datetime
from zoneinfo import ZoneInfo

payload = json.loads(open("data/posts.json", encoding="utf-8").read())
utc = datetime.fromisoformat(payload["fetchedAt"].replace("Z", "+00:00"))
bangkok = datetime.fromisoformat(payload["fetchedAtBangkok"])
expected = utc.astimezone(ZoneInfo("Asia/Bangkok"))
assert expected.strftime("%Y-%m-%dT%H:%M:%S") == bangkok.strftime("%Y-%m-%dT%H:%M:%S")
print("runStartedAt:", payload["runStartedAt"])
print("fetchedAt UTC:", payload["fetchedAt"])
print("fetchedAtBangkok:", payload["fetchedAtBangkok"])
print("timestamp consistency passed")
