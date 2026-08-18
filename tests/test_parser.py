from parser import ParsedPost, build_payload, clean_text, parse_post_text


def test_clean_text_collapses_whitespace():
    assert clean_text("a   b\n\n\n c") == "a b\n\n c"


def test_expanded_text_has_no_see_more_marker():
    text, expanded = parse_post_text("Title\nFull body")
    assert text == "Title\nFull body"
    assert expanded is True


def test_visible_text_with_see_more_is_not_complete():
    text, expanded = parse_post_text("Title\nShort text\nSee more")
    assert "See more" in text
    assert expanded is False


def test_to_dict_excludes_reaction_and_comment_fields():
    post = ParsedPost(type="latest", text="hello", visible_text="hello", reactions=10, comments=3)
    output = post.to_dict()
    assert "reactions" not in output
    assert "comments" not in output
    assert output["text"] == "hello"


def test_payload_has_source_posts_and_warnings():
    payload = build_payload(
        {"access": "public_no_login"},
        [ParsedPost(type="latest", text="hello", visible_text="hello", status="complete")],
        [],
        "2026-08-17T00:00:00Z",
        run_started_at="2026-08-16T23:59:00Z",
        fetched_at_bangkok="2026-08-17T07:00:00+07:00",
    )
    assert payload["runStatus"] == "success"
    assert payload["fetchedAt"] == "2026-08-17T00:00:00Z"
    assert payload["fetchedAtTimezone"] == "UTC"
    assert payload["runStartedAt"] == "2026-08-16T23:59:00Z"
    assert payload["fetchedAtBangkok"] == "2026-08-17T07:00:00+07:00"
    assert payload["posts"][0]["type"] == "latest"
