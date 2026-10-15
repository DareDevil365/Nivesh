"""A calendar-paced beginner course; deterministic teaching, no extra AI calls."""

import html
import json
import os
import re
import time
from datetime import date
from pathlib import Path

from services import news_reader, telegram_delivery
from services.news_bot import BotError

CURRICULUM = json.loads(
    Path(__file__).with_name("finance_curriculum.json").read_text(encoding="utf-8")
)
EXAMPLES = {
    "business": "Hypothetical: a cement maker sells tonnes to dealers. Demand depends on construction, but its profit also depends on price, fuel, freight and competing capacity. More construction alone does not settle the stock pitch.",
    "evidence": "Hypothetical: a company bids for a ₹100 crore contract. A bid is not an award. Even an award is not ₹100 crore of immediate sales or cash; execution, accounting and collection still matter.",
    "statements": "Hypothetical: goods worth ₹100 are sold on credit with ₹70 of costs. Simplified profit is ₹30 before tax, but the customer's ₹100 has not yet arrived. Profit and cash are different questions.",
    "drivers": "Hypothetical: 100 units at ₹10 produce ₹1,000 revenue. If units rise 10% and price falls 5%, revenue becomes 110 × ₹9.50 = ₹1,045: 4.5% growth, not 10%.",
    "news": "Hypothetical: a fuel tax rises. Trace exposure → delivered cost → ability to raise prices → margins → expectations. A company with no relevant fuel exposure may have little direct effect; an exposed firm may have hedges.",
    "valuation": "Hypothetical: EPS grows from ₹10 to ₹11 but P/E falls from 20 to 16. Price implied by those assumptions moves from ₹200 to ₹176, a 12% fall despite 10% earnings growth. This is arithmetic, not a price forecast.",
    "risk": "Hypothetical: five steel companies are five tickers but share demand, energy and steel-price risks. Count economic exposures as well as the number of holdings.",
    "strategies": "Hypothetical: a backtest uses only today's surviving companies. Firms that failed are missing, so the reported historical result may be too optimistic even if the arithmetic is correct.",
    "pitch": "Hypothetical thesis: receivable days should fall over the next two results. Record the starting figure, accounting basis and review date. A missed milestone is a reason to re-examine the thesis.",
    "Revenue": "A hypothetical ₹100 credit sale may be revenue today while customer cash arrives later. Read the revenue-recognition policy.",
    "Net profit / PAT": "Hypothetical revenue of ₹100 less all recognised costs and tax of ₹85 gives PAT of ₹15; a one-off gain may make this unrepresentative.",
    "Balance sheet": "Hypothetical assets of ₹150 financed by liabilities of ₹90 leave ₹60 equity. This is a dated accounting snapshot, not a market valuation.",
    "Operating cash flow / CFO": "Hypothetical profit of ₹20 plus ₹5 non-cash depreciation less a ₹15 working-capital cash increase gives ₹10 operating cash before other adjustments.",
    "EPS": "Hypothetical ₹100 crore attributable profit / 10 crore weighted-average shares = ₹10 basic EPS. Dilution may change the denominator.",
    "P/E": "Hypothetical price ₹200 / EPS ₹10 = 20× P/E. A loss-making company does not become cheap because this ratio is negative.",
    "Net margin": "Hypothetical PAT ₹15 / revenue ₹100 = 15% net margin. Compare matching periods, accounting basis and units.",
    "Debt": "Two hypothetical firms both borrow ₹100, but one repays next month and the other in five years. Maturity and cash available change the risk.",
    "Working capital": "Hypothetical operating receivables ₹30 plus inventory ₹20 less trade payables ₹15 ties up ₹35. This operating definition differs from total current assets less current liabilities.",
    "Capex": "Hypothetical ₹50 spent replacing worn machines maintains capacity; ₹50 spent on a new plant aims to expand it. Both consume cash, with different purposes.",
    "Free cash flow": "Hypothetical CFO ₹40 less capex ₹25 leaves ₹15 under the simple CFO-minus-capex convention. Define your convention before comparing firms.",
    "ROE": "Hypothetical profit ₹10 / average equity ₹50 = 20% ROE. Added leverage can lift this ratio while increasing risk.",
    "ROCE": "Hypothetical EBIT ₹20 / defined capital employed ₹100 = 20% ROCE. State whether capital and profit are average, pre-tax and consistently defined.",
    "Enterprise value": "Hypothetical equity market value ₹200 + debt ₹60 − cash ₹20 = ₹240 simple enterprise value; leases and other claims may need adjustments.",
    "Dilution": "Hypothetical profit stays ₹100 while shares rise from 10 to 12. Simplified EPS falls from ₹10 to about ₹8.33 before considering how raised capital is used.",
    "Consolidated": "A parent and its subsidiaries can differ from the parent's standalone accounts. Do not pair consolidated sales with standalone profit.",
    "YoY / QoQ": "A hypothetical festival-heavy quarter may beat the previous quarter but trail the same quarter last year. Seasonality changes the comparison.",
    "Order book": "A hypothetical ₹500 crore order book scheduled over three years is not ₹500 crore of next-quarter revenue. Check cancellations, execution and margins.",
    "Related-party transaction": "A hypothetical company rents property from a promoter-owned entity. Check pricing, approvals and disclosure; the relationship alone does not prove wrongdoing.",
    "Catalyst": "A hypothetical plant opening might change earnings expectations. Approval, commissioning, utilisation and market expectations are separate checks.",
    "Inflation": "A hypothetical price index rising from 100 to 105 is 5% inflation over that comparison period. A household or company's own costs can change differently.",
    "Policy rate": "A hypothetical central-bank rate cut may influence funding costs, but a firm's loan reset dates, credit spread and debt mix determine transmission.",
    "Basis point": "A hypothetical rate move from 6.00% to 6.25% is 25 basis points, or 0.25 percentage point. It is not a 25% increase.",
    "Currency exposure": "A hypothetical exporter receives dollars but also imports inputs and has dollar debt. Look at net exposure and hedges before assuming a weaker rupee helps.",
    "Fiscal deficit": "Hypothetical government spending ₹120 less non-borrowed receipts ₹100 leaves a ₹20 deficit under this simplified example.",
    "Allocation vs expenditure": "A hypothetical ₹1,000 crore budget allocation does not establish spending, a company's contract award or recognised company revenue.",
    "Diversification": "Two hypothetical funds may own the same large stocks. Two fund names do not automatically mean two independent sets of risk.",
    "Liquidity": "A hypothetical holding worth ₹1 lakh at the last traded price may realise less if there are few buyers when you need to sell.",
    "Index fund": "A hypothetical index gains 10% while its fund gains 9.7% over the same period. Inspect fees, cash and tracking; the index return is not your guaranteed return.",
    "Benchmark": "Compare hypothetical Indian-equity returns with a relevant total-return benchmark in the same currency and period, rather than mixing price and dividend-inclusive returns.",
    "Momentum": "A hypothetical rule buys recent relative winners. Specify the lookback and rebalance rules; a reversal can hurt, and past strength is not a prediction.",
    "Drawdown": "A hypothetical ₹100 holding falls to ₹50: a 50% drawdown. It must rise 100% from ₹50 to return to ₹100, before fees or dividends.",
}


def course():
    lessons = []
    for foundation in CURRICULUM["foundations"]:
        lessons.append(
            {
                **foundation,
                "title": re.sub(r"^\d+\.\s*", "", foundation["title"]),
                "example": EXAMPLES[foundation["id"]],
                "phase": "Foundations",
            }
        )
    for index, term in enumerate(CURRICULUM["terms"]):
        lessons.append(
            {
                "id": f"term-{index}",
                "title": term["term"],
                "note": term["meaning"],
                "example": EXAMPLES[term["term"]],
                "source": term["source"],
                "phase": "Terms in practice",
                "task": "Find this term in an official company report or original economic release. Record the date, definition, units and one limitation before using it in a pitch.",
                "question": "Explain the example to a clubmate. Which assumption or missing detail would you verify first?",
                "explanation": term["meaning"]
                + " No single metric or headline establishes whether a stock is worth buying.",
            }
        )
    for index, strategy in enumerate(CURRICULUM["strategies"]):
        lessons.append(
            {
                "id": f"strategy-{index}",
                "title": strategy["name"],
                "note": strategy["idea"],
                "example": "Evidence to inspect: "
                + strategy["evidence"]
                + " Failure condition: "
                + strategy["failure"],
                "source": strategy["source"],
                "phase": "Strategies and failure cases",
                "task": strategy["task"],
                "question": "What could make this strategy fail even when the company appears attractive?",
                "explanation": strategy["failure"],
            }
        )
    return lessons


def lesson_for_day(day, start=None):
    try:
        current = date.fromisoformat(day)
        beginning = date.fromisoformat(start or os.getenv("NEWS_LEARNING_START_DATE", "2026-10-15"))
    except ValueError:
        raise BotError("Invalid finance course start/report date.") from None
    elapsed = (current - beginning).days
    if elapsed < 0:
        raise BotError("The finance course start date is in the future.")
    lessons = course()
    lesson = lessons[elapsed % len(lessons)]
    return {
        **lesson,
        "day": elapsed + 1,
        "course_size": len(lessons),
        "cycle": elapsed // len(lessons) + 1,
        "source_info": CURRICULUM["sources"][lesson["source"]],
    }


def heading(lesson):
    review = " · review cycle " + str(lesson["cycle"]) if lesson["cycle"] > 1 else ""
    return f"<b>Stock Daddy · Day {lesson['day']}{review}</b>"


def render(lesson, digest=None):
    esc = html.escape
    parts = [
        f"{esc(lesson['phase'])} · {lesson['course_size']}-lesson course",
        f"<b>{esc(lesson['title'])}</b>\n{esc(lesson['note'])}",
        "<b>Worked example / research case</b>\n" + esc(lesson["example"]),
        "<b>Try it in your research</b>\n" + esc(lesson["task"]),
    ]
    # An optional practice link is never represented as a verified company impact.
    if digest:
        keywords = {
            "business": ("company", "customer", "sales", "cement", "bank"),
            "evidence": ("project", "order", "contract", "bid"),
            "statements": ("earnings", "profit", "cash", "revenue"),
            "drivers": ("demand", "supply", "price", "capacity"),
            "news": ("policy", "tariff", "rate", "tax"),
            "valuation": ("stock", "earnings", "valuation"),
            "risk": ("risk", "debt", "war", "crisis"),
        }.get(lesson["id"], ())
        candidates = [
            bullet
            for section in digest["sections"]
            for bullet in section["bullets"]
            if any(
                re.search(r"\b" + re.escape(word) + r"\b", bullet["text"], re.I)
                for word in keywords
            )
        ]
        if candidates and candidates[0].get("sources"):
            source = candidates[0]["sources"][0]
            url = news_reader.safe_link(source["url"])
            if url:
                parts.append(
                    f'<b>Optional news exercise</b>\n<a href="{esc(url, quote=True)}">{esc(source["title"])}</a>\nAccess: {esc(source["read_status"].replace("_", " "))}. Use this as a practice question; no company impact is established by the match.'
                )
    question = lesson["question"]
    if lesson.get("options"):
        question += "\n" + "\n".join(
            f"{index}. {option}" for index, option in enumerate(lesson["options"], 1)
        )
        answer = (
            str(lesson["answer"] + 1)
            + ". "
            + lesson["options"][lesson["answer"]]
            + " — "
            + lesson["explanation"]
        )
    else:
        answer = lesson["explanation"]
    parts.append(
        "<b>Quick check — think before revealing</b>\n"
        + esc(question)
        + "\n<tg-spoiler>"
        + esc(answer)
        + "</tg-spoiler>"
    )
    source = lesson["source_info"]
    url = news_reader.safe_link(source["url"])
    if not url:
        raise BotError("Invalid finance lesson source.")
    parts.append(
        f'<a href="{esc(url, quote=True)}">Further reading: {esc(source["label"])}</a>\nOriginal teaching notes and hypothetical examples; no live stock forecast. The course advances by calendar day; it does not grade replies or adapt to them.'
    )
    text = "\n\n".join(parts)
    if len(text.encode("utf-16-le")) // 2 > 4096:
        raise BotError("Finance lesson exceeds Telegram limits; refusing a cut-off lesson.")
    return text


def deliver(day, config, ledger, digest=None):
    identifier = "stock-daddy-v1-" + config.delivery_id(day)
    previous = telegram_delivery.existing_id(identifier, ledger)
    if previous:
        return previous
    lesson = lesson_for_day(day)
    message = render(lesson, digest)
    time.sleep(1.1)
    return telegram_delivery.deliver_messages(
        day, [heading(lesson), message], config, ledger, identifier
    )
