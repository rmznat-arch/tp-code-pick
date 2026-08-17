from pathlib import Path

required = {
    ".github/workflows/collect.yml": [
        'cron: "0 2,8,14,20 * * *"',
        "python cli.py fetch --headless",
        "actions/deploy-pages@v4",
        "site/api/posts.json",
    ],
    ".github/workflows/pages.yml": [
        "actions/upload-pages-artifact@v3",
        "actions/deploy-pages@v4",
        'path: "./site"',
    ],
}
for name, needles in required.items():
    text = Path(name).read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{name}: missing {missing}")
    print(name, "OK")
