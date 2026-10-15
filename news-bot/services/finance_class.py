"""Broad beginner finance course plus bounded, evidence-grounded current-event context."""

import html
import json
import math
import os
import re
import time
from datetime import date
from pathlib import Path

import httpx

from services import news_bot, news_reader
from services import telegram_delivery as tg
from services.news_bot import BotError

DATA = json.loads(Path(__file__).with_name("finance_foundations.json").read_text(encoding="utf-8"))
DEPTH = json.loads(
    Path(__file__).with_name("finance_lesson_depth.json").read_text(encoding="utf-8")
)
CLASS_VERSION = "finance-class-v2-"


def course():
    keys = ("id", "module", "title", "note", "example", "question", "answer", "source", "keywords")
    lessons = [dict(zip(keys, row, strict=True)) for row in DATA["lessons"]]
    if set(DEPTH) != {lesson["id"] for lesson in lessons}:
        raise BotError("Finance Class depth notes do not match the syllabus.")
    for lesson in lessons:
        depth = DEPTH[lesson["id"]]
        if (
            any(
                not isinstance(depth.get(key), str) or not depth[key].strip()
                for key in ("goal", "mistake", "transfer")
            )
            or any(
                not isinstance(depth.get(key), list)
                or len(depth[key]) < 3
                or any(not isinstance(value, str) or not value.strip() for value in depth[key])
                for key in ("terms", "steps", "worked")
            )
            or not isinstance(depth.get("exercise"), dict)
            or any(
                not isinstance(depth["exercise"].get(key), str)
                or not depth["exercise"][key].strip()
                for key in ("question", "answer")
            )
        ):
            raise BotError("Finance Class depth notes are incomplete.")
        lesson["depth"] = depth
    return lessons


def lesson_for_day(day, start=None):
    try:
        beginning = date.fromisoformat(
            start
            or os.getenv(
                "NEWS_FINANCE_START_DATE", os.getenv("NEWS_LEARNING_START_DATE", "2026-10-15")
            )
        )
        elapsed = (date.fromisoformat(day) - beginning).days
    except ValueError:
        raise BotError("Invalid Finance Class calendar date.") from None
    if elapsed < 0:
        raise BotError("Finance Class has not started yet.")
    lessons = course()
    return {
        **lessons[elapsed % len(lessons)],
        "day": elapsed + 1,
        "cycle": elapsed // len(lessons) + 1,
        "course_size": len(lessons),
        "source_info": DATA["sources"][lessons[elapsed % len(lessons)]["source"]],
    }


def lesson_source(lesson, day):
    return {
        "id": "lesson-" + lesson["id"],
        "title": lesson["title"],
        "publisher": "Nivesh curated teaching notes",
        "url": lesson["source_info"]["url"],
        "published_at": day + "T00:00:00+05:30",
        "read_status": "curated_teaching_notes",
        "categories": ["policy"],
        "evidence_text": "\n".join(
            lesson[key] for key in ("note", "example", "question", "answer")
        ),
    }


def generate(day, sources, purpose, enabled):
    if not enabled:
        return None
    pack = {
        "date_ist": day,
        "generated_at": day + "T00:00:00+05:30",
        "items": sources,
        "coverage": {
            "headlines": len(sources),
            "article_excerpts": 0,
            "feed_excerpts": 0,
            "headline_only": 0,
        },
        "feeds": [],
        "limitations": "Curated teaching and bounded news evidence.",
    }
    try:
        return news_bot.generate_section(pack, "policy", sources, purpose=purpose)
    except (ValueError, BotError, httpx.HTTPError):
        return None


def prepare(day, pack=None, use_ai=True):
    lesson = lesson_for_day(day)
    source = lesson_source(lesson, day)
    explanation = generate(
        day,
        [source],
        "The complete authored lesson is already provided separately to the learner. Add only an optional plain-language explanation of these supplied notes for a complete beginner, not a stock picker. Do not invent new facts, rules, current rates, real-world incidents or numerical examples. Use text for the explanation and why_it_matters for a learning tip. Do not claim to grade the learner or know their performance.",
        use_ai,
    )
    candidates = []
    for item in (pack or {}).get("items", []):
        if not set(item["categories"]) & {
            "world",
            "us",
            "india",
            "policy",
            "commodities",
            "events",
        }:
            continue
        if item["read_status"] == "headline_only" or len(item.get("evidence_text", "")) < 100:
            continue
        score = sum(
            word.casefold() in (item["title"] + " " + item["evidence_text"]).casefold()
            for word in lesson["keywords"]
        )
        candidates.append(
            (score, news_reader.priority(item)["reading_score"], item["published_at"], item)
        )
    candidates.sort(key=lambda entry: entry[:3], reverse=True)
    current = candidates[0][3] if candidates else None
    case_sources = [source]
    concepts = []
    if current:
        case_sources.insert(0, {**current, "categories": ["policy"]})
        text = current["title"] + " " + current["evidence_text"]
        matches = [
            (
                sum(
                    bool(re.search(r"\b" + re.escape(word) + r"s?\b", text, re.I))
                    for word in candidate["keywords"]
                ),
                candidate,
            )
            for candidate in course()
            if candidate["id"] != lesson["id"]
        ]
        matches.sort(key=lambda entry: entry[0], reverse=True)
        concepts = [candidate for score, candidate in matches[:2] if score]
        for concept in concepts:
            case_sources.append(
                lesson_source({**concept, "source_info": DATA["sources"][concept["source"]]}, day)
            )
    historical = None
    if current and any(
        word in (current["title"] + " " + current["evidence_text"]).casefold()
        for word in ("margin", "leverage", "bank", "crisis", "crash")
    ):
        historical = {
            "id": "historical-crisis-reference",
            "title": "Historical reference: the 2007–09 financial crisis",
            "publisher": "Federal Reserve History (curated teaching note)",
            "url": "https://www.federalreservehistory.org/essays/great-recession-and-its-aftermath",
            "published_at": "Historical event period: 2007–09; source publication date not recorded",
            "read_status": "curated_historical_reference",
            "categories": ["policy"],
            "evidence_text": "Historical reference, not current news: mortgage-related financial losses strained global markets before and during the 2007–09 financial crisis. Leverage, funding and interconnected exposures are mechanisms to investigate. This does not establish that a current event has the same cause or outcome.",
        }
        if any(
            word in (current["title"] + " " + current["evidence_text"]).casefold()
            for word in ("margin", "leverage", "hedge fund")
        ):
            historical = {
                "id": "historical-archegos-reference",
                "title": "Historical reference: Archegos margin pressure in March 2021",
                "publisher": "SEC April 2022 complaint account (curated historical note)",
                "url": "https://www.sec.gov/newsroom/press-releases/2022-70",
                "published_at": "2022-04-27T00:00:00+00:00",
                "read_status": "curated_historical_reference",
                "categories": ["policy"],
                "evidence_text": "Historical source account: in its April 2022 complaint announcement, the SEC alleged that price declines in concentrated Archegos positions triggered significant margin calls in March 2021 that it could not meet. This describes the SEC's dated allegations, not a new incident, a full legal-outcome history or proof of today's cause. Compare leverage, concentration and funding separately.",
            }
        case_sources.append(historical)
    context = generate(
        day,
        case_sources,
        "Prepare a separate finance case study for a beginner. In the first bullet distinguish the attributed current report from a possible mechanism using the supplied lesson. In the second bullet pose a clearly hypothetical alternative scenario and explain its assumptions. Use a historical comparison only if the historical source is supplied, explicitly dated and described as a comparison. Do not blame a person, infer a fund's holdings, identify an anecdote, invent a crash, or claim a causal explanation is established. Publication time is not event time. Explain unfamiliar words; a buy recommendation, call option and margin call are different. If no current report is supplied, provide a hypothetical learning exercise without claiming current news.",
        use_ai,
    )
    return {
        "lesson": lesson,
        "explanation": explanation,
        "case": context,
        "current": current,
        "historical": historical,
        "case_concepts": concepts,
        "recall": recall_questions(lesson),
    }


def recall_questions(lesson):
    """Calendar-based retrieval practice, without pretending to know learning performance."""
    lessons = course()
    return [
        {**lessons[(lesson["day"] - 1 - gap) % len(lessons)], "taught_day": lesson["day"] - gap}
        for gap in (1, 7)
        if lesson["day"] > gap
    ]


def source_link(source):
    url = news_reader.safe_link(source["url"])
    if not url:
        raise BotError("Unsafe finance teaching source.")
    label = source.get("publisher", source.get("label", "Further reading"))
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'


def class_messages(prepared):
    lesson, esc = prepared["lesson"], html.escape
    depth = lesson["depth"]
    review = " · review" if lesson["cycle"] > 1 else ""
    heading = f"<b>Finance Class · Today's learnings · Day {lesson['day']}{review}</b>"
    blocks = [f"<b>{esc(lesson['module'])}: {esc(lesson['title'])}</b>"]
    for recall in prepared.get("recall", []):
        blocks.append(
            f"<b>Recall · Day {recall['taught_day']}: {esc(recall['title'])}</b>\n"
            + esc(recall["question"])
            + "\nTry from memory, then tap: <tg-spoiler>"
            + esc(recall["answer"])
            + "</tg-spoiler>"
        )
    blocks.extend(
        [
            "<b>By the end</b>\n" + esc(depth["goal"]),
            "<b>The central idea</b>\n" + esc(lesson["note"]),
            "<b>Words you will use</b>\n" + "\n".join("• " + esc(term) for term in depth["terms"]),
        ]
    )
    blocks.extend(
        f"<b>How it works · Step {index}</b>\n" + esc(paragraph)
        for index, paragraph in enumerate(depth["steps"], 1)
    )
    blocks.extend(
        f"<b>Worked example · Step {index}</b>\n" + esc(paragraph)
        for index, paragraph in enumerate(depth["worked"], 1)
    )
    blocks.append("<b>Where people get confused</b>\n" + esc(depth["mistake"]))
    if prepared["explanation"]:
        blocks.extend(
            "<b>Optional AI explanation</b>\n" + esc(bullet["text"])
            for bullet in prepared["explanation"]["bullets"]
        )
    blocks.extend(
        [
            "<b>Quick check · answer before tapping</b>\n"
            + esc(lesson["question"])
            + "\n<tg-spoiler>"
            + esc(lesson["answer"])
            + "</tg-spoiler>",
            "<b>Your turn · apply the idea</b>\n"
            + esc(depth["exercise"]["question"])
            + "\nWrite your reasoning before revealing the solution.",
            "<b>Worked solution · tap after trying</b>\n<tg-spoiler>"
            + esc(depth["exercise"]["answer"])
            + "</tg-spoiler>",
            "<b>Use it outside this lesson</b>\n" + esc(depth["transfer"]),
            source_link(lesson["source_info"])
            + "\nOriginal teaching notes; linked source is further reading. Examples are hypothetical unless labelled historical.",
        ]
    )
    words = len(html.unescape(re.sub(r"<[^>]+>", " ", " ".join(blocks))).split())
    blocks.insert(
        1,
        f"<i>About {math.ceil(words / 160)} min reading + 3–5 min practice. Pause at the examples; no prior finance study needed.</i>",
    )
    chunks = pack_blocks(blocks)
    return [
        heading,
        *[
            f"<b>Finance Class · Part {index}/{len(chunks)}</b>\n\n" + chunk
            for index, chunk in enumerate(chunks, 1)
        ],
    ]


def pack_blocks(blocks):
    chunks, current = [], ""
    for block in blocks:
        if len(block.encode("utf-16-le")) // 2 > 3500:
            raise BotError("Finance teaching block is too long.")
        candidate = current + ("\n\n" if current else "") + block
        if len(candidate.encode("utf-16-le")) // 2 > 3500:
            chunks.append(current)
            current = block
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def case_messages(prepared):
    esc, current = html.escape, prepared["current"]
    blocks = []
    if current:
        blocks.append(
            "<b>Reported event</b>\n"
            + esc(current["title"])
            + "\n"
            + source_link(current)
            + "\nPublished: "
            + esc(current["published_at"])
            + " · "
            + esc(current["read_status"].replace("_", " "))
        )
    else:
        blocks.append(
            "<b>Hypothetical case</b>\nNo sufficiently detailed current report was selected. This exercise teaches a mechanism; it is not a claim that an incident occurred today."
        )
    if prepared["case"]:
        blocks.extend(
            "<b>Explanation / scenario to test</b>\n"
            + esc(bullet["text"])
            + "\n"
            + esc(bullet["why_it_matters"])
            for bullet in prepared["case"]["bullets"]
        )
    else:
        example_lesson = (prepared.get("case_concepts") or [prepared["lesson"]])[0]
        blocks.extend(
            [
                "<b>Concept to investigate — not a confirmed cause</b>\n"
                + esc(example_lesson["note"]),
                "<b>Counterfactual exercise</b>\nChange one assumption in today's example. What changes, and what information would you need?\n"
                + esc(example_lesson["example"]),
            ]
        )
    if prepared["historical"]:
        blocks.append(
            "<b>Historical comparison — not today's cause</b>\n"
            + esc(prepared["historical"]["evidence_text"])
            + "\n"
            + source_link(prepared["historical"])
        )
    relevant_call_terms = prepared["lesson"]["id"] in {"calls", "leverage"} or (
        current
        and re.search(
            r"margin|hedge fund|call option|buy call|leverage",
            current["title"] + " " + current["evidence_text"],
            re.I,
        )
    )
    if relevant_call_terms:
        blocks.append(
            "<b>Keep these terms separate</b>\n• Buy call: a recommendation in some commentary.\n• Call option: a contractual right to buy on stated terms.\n• Margin call: a demand to meet collateral/equity requirements.\n"
            + source_link(DATA["sources"]["options"])
            + " · "
            + source_link(DATA["sources"]["margin"])
            + "\nAn absent warning does not remove losses or automatically prevent contractual liquidation. Explanations are learning hypotheses, not proof of why a reported event happened."
        )
    blocks.append(
        "<b>Check the explanation</b>\nThe reported event, a possible mechanism, a historical comparison and a hypothetical alternative are different claims. The supplied evidence does not prove every causal interpretation."
    )
    return ["<b>Finance in context · News, history and what-if</b>", *pack_blocks(blocks)]


def deliver(day, config, ledger, prepared, context=False):
    key = ("finance-context-v1-" if context else CLASS_VERSION) + config.delivery_id(day)
    prior = tg.existing_id(key, ledger)
    if prior:
        return prior
    time.sleep(1.1)
    return tg.deliver_messages(
        day, case_messages(prepared) if context else class_messages(prepared), config, ledger, key
    )
