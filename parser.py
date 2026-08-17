from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

TIME_RE = re.compile(r"^(\d+\s*(?:m|min|h|d|w)|yesterday|today|เมื่อวาน|วันนี้)$", re.IGNORECASE)
PINNED_TERMS = ("pinned", "ปักหมุด", "โพสต์ที่ปักหมุด")
SEE_MORE_TERMS = ("see more", "ดูเพิ่มเติม", "ดูเพิ่ม")

@dataclass
class ParsedPost:
    type: str
    text: str
    visible_text: str
    published_label: str | None = None
    post_url: str | None = None
    expanded: bool = False
    status: str = "partial"
    reactions: int | None = None
    comments: int | None = None
    warnings: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result.pop("reactions", None)
        result.pop("comments", None)
        result["warnings"] = result["warnings"] or []
        return result


def clean_text(value: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t]+", " ", value or "")).strip()


def is_time_label(value: str) -> bool:
    return bool(TIME_RE.match(value.strip()))


def contains_term(value: str, terms: Iterable[str]) -> bool:
    lowered = value.lower()
    return any(term.lower() in lowered for term in terms)


def parse_post_text(text: str) -> tuple[str, bool]:
    cleaned = clean_text(text)
    expanded = not any(term.lower() in cleaned.lower() for term in SEE_MORE_TERMS)
    return cleaned, expanded


def sort_posts(posts: list[ParsedPost]) -> list[ParsedPost]:
    # Facebook's visible relative labels are already ordered in feed order.
    # Preserve source order while placing explicit pinned posts first for callers.
    return posts


def build_payload(source: dict[str, Any], posts: list[ParsedPost], warnings: list[str], fetched_at: str) -> dict[str, Any]:
    return {
        "source": source,
        "fetchedAt": fetched_at,
        "runStatus": "success" if posts and not warnings else ("partial" if posts else "blocked"),
        "posts": [post.to_dict() for post in posts],
        "warnings": warnings,
    }
