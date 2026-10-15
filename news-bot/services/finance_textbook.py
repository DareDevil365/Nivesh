"""Assemble authored textbook chapters from curated cases and connected concepts."""

import html
import json
import re
from pathlib import Path

from services.news_bot import BotError
from services.news_reader import safe_link

DATA = json.loads(Path(__file__).with_name("finance_textbook.json").read_text(encoding="utf-8"))
MIN_WORDS = 2400
MAX_WORDS = 3200


def word_count(blocks):
    return len(html.unescape(re.sub(r"<[^>]+>", " ", " ".join(blocks))).split())


def validate(lessons):
    ids = {lesson["id"] for lesson in lessons}
    covered = [key for module in DATA["modules"] for key in module["ids"]]
    if len(covered) != len(ids) or set(covered) != ids or set(DATA["connections"]) != ids:
        raise BotError("Textbook coverage does not match Finance Class.")
    for key, connections in DATA["connections"].items():
        if (
            len(connections) != 4
            or len(set(connections)) != 4
            or key in connections
            or not set(connections) <= ids
        ):
            raise BotError("Invalid textbook concept connections.")
    for module in DATA["modules"]:
        if len(module["pairs"]) != len(module["ids"]) or len(module["cases"]) != 4:
            raise BotError("Invalid textbook case plan.")
        for paragraphs in [module["foundation"], *[case["paragraphs"] for case in module["cases"]]]:
            if len(paragraphs) < 4 or any(
                not isinstance(p, str) or not p.strip() for p in paragraphs
            ):
                raise BotError("Incomplete textbook reading.")
        for pair in module["pairs"]:
            if (
                len(pair) != 2
                or len(set(pair)) != 2
                or any(type(i) is not int or i not in range(4) for i in pair)
            ):
                raise BotError("Invalid textbook case selection.")


def chapter_blocks(lesson, lessons, sources, base_words):
    """Add complete, related readings until the authored chapter meets its reading budget.

    No model padding or sentence repetition. Prerequisites may appear before their own
    main lesson and are explicitly labelled as reusable supporting readings.
    """
    validate(lessons)
    module = next(module for module in DATA["modules"] if lesson["id"] in module["ids"])
    index = module["ids"].index(lesson["id"])
    esc = html.escape
    blocks = [
        "<b>Textbook reading · " + esc(module["foundation_title"]) + "</b>\n"
        "The module foundation and cases are reused where relevant. Supporting readings connect today's topic to the wider system; some introduce ideas taught as main topics later."
    ]
    blocks.extend(esc(paragraph) for paragraph in module["foundation"])
    for number in module["pairs"][index]:
        case = module["cases"][number]
        blocks.append("<b>Extended hypothetical case · " + esc(case["title"]) + "</b>")
        blocks.extend(esc(paragraph) for paragraph in case["paragraphs"])
    by_id = {item["id"]: item for item in lessons}
    for key in DATA["connections"][lesson["id"]]:
        if base_words + word_count(blocks) >= MIN_WORDS:
            break
        connected = by_id[key]
        depth = connected["depth"]
        blocks.extend(
            [
                "<b>Supporting reading · "
                + esc(connected["title"])
                + "</b>\n"
                + esc(connected["note"]),
                "<b>Vocabulary for this connection</b>\n"
                + "\n".join("• " + esc(term) for term in depth["terms"]),
            ]
        )
        blocks.extend(esc(paragraph) for paragraph in depth["steps"])
        blocks.extend(
            "<b>Connection example · Step " + str(i) + "</b>\n" + esc(paragraph)
            for i, paragraph in enumerate(depth["worked"], 1)
        )
        blocks.append("<b>Connection to check</b>\n" + esc(depth["mistake"]))
        source = sources[connected["source"]]
        url = safe_link(source["url"])
        if not url:
            raise BotError("Unsafe textbook further-reading URL.")
        blocks.append('<a href="' + esc(url, quote=True) + '">' + esc(source["label"]) + "</a>")
    if not MIN_WORDS <= base_words + word_count(blocks) <= MAX_WORDS:
        raise BotError("Authored textbook chapter is outside its reading budget.")
    return blocks
