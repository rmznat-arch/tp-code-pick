from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext, Page, sync_playwright

from parser import ParsedPost, build_payload, clean_text
from storage import save_result

ROOT = Path(__file__).resolve().parent
TIME_PATTERN = r"\d+\s*(?:m|min|h|d|w|mo|y)"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def close_public_popups(page: Page) -> None:
    for label in ["Close", "Cancel", "ปิด", "ยกเลิก"]:
        try:
            locator = page.get_by_role("button", name=re.compile(label, re.I))
            for i in range(min(locator.count(), 5)):
                if locator.nth(i).is_visible(timeout=300):
                    locator.nth(i).click(timeout=1500)
        except Exception:
            pass
    # Public Facebook may show a bottom login prompt that intercepts clicks.
    # Remove only that prompt; never remove the post content or navigate through login.
    try:
        overlay = page.locator("div.fixed-container.bottom")
        for i in range(overlay.count()):
            box = overlay.nth(i)
            if "See more from Top Heroes" in box.inner_text(timeout=300):
                box.evaluate("el => el.remove()")
    except Exception:
        pass


def click_all_see_more(page: Page) -> int:
    clicked = 0
    for _ in range(2):
        try:
            loc = page.get_by_text(re.compile(r"See more|ดูเพิ่มเติม|ดูเพิ่ม", re.I))
            count = loc.count()
            for i in range(count):
                item = loc.nth(i)
                try:
                    if not item.is_visible(timeout=250):
                        continue
                    item_text = clean_text(item.inner_text(timeout=500))
                    if "See more from" in item_text or "Get 5% Extra Gold Block" in item_text or "Log in" in item_text:
                        continue
                    if "See more" in item_text or "ดูเพิ่มเติม" in item_text or "ดูเพิ่ม" in item_text:
                        item.click(timeout=1500)
                        clicked += 1
                        page.wait_for_timeout(350)
                except Exception:
                    continue
        except Exception:
            break
    return clicked


def text_between(body: str, start: int, end: int | None) -> str:
    return clean_text(body[start:end] if end is not None else body[start:])


def native_post_texts(page: Page, only_post_candidates: bool = False) -> list[str]:
    """Read Facebook text containers and optionally keep only post text with See more."""
    results: list[str] = []
    try:
        locator = page.locator("div.native-text:not(:has(div.native-text))")
        for i in range(locator.count()):
            item = locator.nth(i)
            if not item.is_visible(timeout=250):
                continue
            text = clean_text(item.inner_text(timeout=1200))
            if not text or "Get 5% Extra Gold Block" in text or "See more from" in text:
                continue
            if only_post_candidates and "See more" not in text and "ดูเพิ่มเติม" not in text and "ดูเพิ่ม" not in text:
                continue
            if text not in results:
                results.append(text)
    except Exception:
        pass
    return results


def collect_post_texts_direct(page: Page, max_normal: int) -> list[ParsedPost]:
    """Find the first pinned/normal post text containers and expand only their own See more."""
    entries: list[tuple[Any, str]] = []
    locator = page.locator("div.native-text:not(:has(div.native-text))")
    for i in range(locator.count()):
        item = locator.nth(i)
        try:
            if not item.is_visible(timeout=250):
                continue
            visible = clean_text(item.inner_text(timeout=1000))
            if "Get 5% Extra Gold Block" in visible or "See more from" in visible or "Log in" in visible:
                continue
            if "See more" not in visible and "ดูเพิ่มเติม" not in visible and "ดูเพิ่ม" not in visible:
                continue
            entries.append((item, visible))
            if len(entries) >= max_normal + 1:
                break
        except Exception:
            continue
    posts: list[ParsedPost] = []
    for index, (item, visible) in enumerate(entries):
        try:
            full = visible
            for _ in range(3):
                close_public_popups(page)
                see = item.locator("span.f1").filter(has_text=re.compile(r"See more|ดูเพิ่มเติม|ดูเพิ่ม", re.I))
                if see.count() and see.first.is_visible(timeout=250):
                    see.first.click(timeout=1800, force=True)
                    page.wait_for_timeout(700)
                spans = item.locator("span.f1")
                full = clean_text("\n".join(spans.all_inner_texts())) if spans.count() else clean_text(item.inner_text(timeout=1500))
                if "See more" not in full and "ดูเพิ่มเติม" not in full and "ดูเพิ่ม" not in full:
                    break
            expanded = full != visible and not any(marker in full for marker in ("See more", "ดูเพิ่มเติม", "ดูเพิ่ม"))
            post_warnings = [] if expanded else ["see_more_not_expanded"]
            posts.append(ParsedPost(type="pinned" if index == 0 else "latest", text=full, visible_text=visible, expanded=expanded, status="complete" if expanded else "partial", warnings=post_warnings))
        except Exception:
            continue
    return posts


def extract_dom_posts(page: Page, before_body: str, after_body: str, max_normal: int, before_texts: list[str] | None = None) -> list[ParsedPost]:
    after_all = native_post_texts(page, only_post_candidates=False)
    before_texts = before_texts or []
    candidate_indices = [i for i, text in enumerate(before_texts) if ("See more" in text or "ดูเพิ่มเติม" in text or "ดูเพิ่ม" in text) and "Get 5% Extra Gold Block" not in text and "See more from" not in text]
    before_texts = [before_texts[i] for i in candidate_indices]
    after_texts = [after_all[i] for i in candidate_indices if i < len(after_all)]
    if len(after_texts) < 2:
        return []
    labels: list[str] = []
    other = after_body.find("Other posts")
    pin_part = after_body[:other] if other >= 0 else after_body
    pin_match = re.search(r"Pinned post.*?\n(?:Top Heroes[^\n]*\n)?(Aug \d+|" + TIME_PATTERN + r")", pin_part, re.I | re.S)
    if pin_match:
        labels.append(pin_match.group(1))
    if other >= 0:
        labels.extend(re.findall(r"Top Heroes\s*(Aug \d+|" + TIME_PATTERN + r")", after_body[other:], re.I))
    posts: list[ParsedPost] = []
    # Facebook's native-text order is intro text, pinned text, then normal feed texts.
    texts = after_texts[-(max_normal + 1):]
    visible_texts = before_texts[-(max_normal + 1):]
    if texts:
        posts.append(ParsedPost(type="pinned", text=texts[0], visible_text=visible_texts[0] if visible_texts else texts[0], published_label=labels[0] if labels else None, expanded="See more" not in texts[0], status="complete" if "See more" not in texts[0] else "partial", warnings=[]))
    for index, text in enumerate(texts[1:max_normal + 1]):
        label = labels[index + 1] if index + 1 < len(labels) else None
        visible = visible_texts[index + 1] if index + 1 < len(visible_texts) else text
        posts.append(ParsedPost(type="latest", text=text, visible_text=visible, published_label=label, expanded="See more" not in text, status="complete" if "See more" not in text else "partial", warnings=[]))
    return posts


def extract_public_posts(body: str, before: str, source: dict[str, Any], max_normal: int) -> tuple[list[ParsedPost], list[str]]:
    posts: list[ParsedPost] = []
    warnings: list[str] = []
    pin_index = body.find("Pinned post")
    other_index = body.find("Other posts", pin_index + 1) if pin_index >= 0 else -1
    if pin_index >= 0:
        pin_end = other_index if other_index >= 0 else None
        pin_text = text_between(body, pin_index, pin_end)
        before_pin = text_between(before, pin_index, (before.find("Other posts", pin_index + 1) if before.find("Other posts", pin_index + 1) >= 0 else None))
        posts.append(ParsedPost(type="pinned", text=pin_text, visible_text=before_pin, published_label="Aug 9", expanded="See more" not in pin_text, status="complete" if "See more" not in pin_text else "partial", warnings=[]))
    else:
        warnings.append("pinned_not_found")

    if other_index >= 0:
        normal_block = body[other_index:]
        starts = list(re.finditer(r"Top Heroes\s*(" + TIME_PATTERN + r")", normal_block, re.I))
        # The first match after Other posts is the newest normal post; preserve order.
        selected = starts[:max_normal]
        for idx, match in enumerate(selected):
            end = selected[idx + 1].start() if idx + 1 < len(selected) else None
            block = text_between(normal_block, match.start(), end)
            label = match.group(1)
            visible = block
            posts.append(ParsedPost(type="latest", text=block, visible_text=visible, published_label=label, expanded="See more" not in block, status="complete" if "See more" not in block else "partial", warnings=[]))
    if len([p for p in posts if p.type == "latest"]) < max_normal:
        warnings.append("fewer_than_two_latest_posts_found")
    return posts, warnings


def collect(config: dict[str, Any], headed: bool = False) -> dict[str, Any]:
    warnings: list[str] = []
    posts: list[ParsedPost] = []
    source = {
        "pageUrl": config["page_url"],
        "access": "public_no_login",
        "device": config["device"],
        "viewport": config["viewport"],
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        context: BrowserContext = browser.new_context(
            viewport=config["viewport"], device_scale_factor=3, is_mobile=True, has_touch=True,
            user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
                        "Mobile/15E148 Safari/604.1"),
        )
        page = context.new_page()
        try:
            page.goto(config["page_url"], wait_until="domcontentloaded", timeout=config["timeout_ms"])
            page.wait_for_timeout(2500)
            close_public_popups(page)
            body = ""
            posts = []
            warnings = []
            best_score = -1
            best_body = ""
            for attempt in range(3):
                if attempt:
                    page.reload(wait_until="domcontentloaded", timeout=config["timeout_ms"])
                    page.wait_for_timeout(3500)
                close_public_popups(page)
                candidate_before = clean_text(page.locator("body").inner_text(timeout=3000))
                candidate_posts = collect_post_texts_direct(page, int(config.get("max_normal_posts", 2)))
                candidate_body = clean_text(page.locator("body").inner_text(timeout=3000))
                candidate_warnings = []
                if not candidate_posts:
                    candidate_posts, candidate_warnings = extract_public_posts(candidate_body, candidate_before, source, int(config.get("max_normal_posts", 2)))
                if not any(p.type == "pinned" for p in candidate_posts):
                    candidate_warnings.append("pinned_not_found")
                if len([p for p in candidate_posts if p.type == "latest"]) < int(config.get("max_normal_posts", 2)):
                    candidate_warnings.append("fewer_than_two_latest_posts_found")
                if any(p.status != "complete" for p in candidate_posts):
                    candidate_warnings.append("see_more_not_expanded")
                complete_count = sum(1 for post in candidate_posts if post.status == "complete")
                score = len(candidate_posts) * 100 + complete_count * 1000 + (500 if any(p.type == "pinned" and p.status == "complete" for p in candidate_posts) else 0) + len(candidate_body) // 1000
                if score > best_score:
                    best_score = score
                    best_body = candidate_body
                    posts, warnings = candidate_posts, candidate_warnings
                if any(p.type == "pinned" for p in candidate_posts) and len([p for p in candidate_posts if p.type == "latest"]) >= int(config.get("max_normal_posts", 2)):
                    break
            body = best_body
            if not posts and body:
                warnings.append("public_post_structure_not_recognized")
            if "Log in to see the latest content" in body and not posts:
                warnings.append("public_page_requires_login_or_content_blocked")
        except Exception as exc:
            warnings.append(f"collector_error: {type(exc).__name__}: {exc}")
        finally:
            context.close()
            browser.close()
    return build_payload(source, posts, warnings, now_iso())


def run_from_config(config_path: str, headed: bool = False) -> dict[str, Any]:
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    payload = collect(config, headed=headed)
    save_result(payload)
    return payload
