from __future__ import annotations

import argparse
import json
from pathlib import Path

from collector import run_from_config

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect public Top Heroes Facebook posts without login or API")
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="Fetch pinned and two latest public posts")
    fetch.add_argument("--headed", action="store_true", help="Show Chromium while collecting")
    fetch.add_argument("--headless", action="store_true", help="Run Chromium headless (default)")
    fetch.add_argument("--config", default=str(ROOT / "config.json"))
    validate = sub.add_parser("validate", help="Validate latest JSON")
    validate.add_argument("--path", default=str(ROOT / "data" / "posts.json"))
    args = parser.parse_args()
    if args.command == "fetch":
        payload = run_from_config(args.config, headed=args.headed)
        print(json.dumps({"runStatus": payload["runStatus"], "posts": len(payload["posts"]), "warnings": payload["warnings"]}, ensure_ascii=False, indent=2))
        return 0 if payload["posts"] else 2
    data = json.loads(Path(args.path).read_text(encoding="utf-8"))
    assert isinstance(data.get("posts"), list)
    assert isinstance(data.get("warnings"), list)
    print(f"Valid JSON: {len(data['posts'])} posts, status={data.get('runStatus')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
