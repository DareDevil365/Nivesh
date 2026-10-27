"""Validated round-trip CSVs and FIFO matching for long-only broker executions."""

import csv
import io
import re
from collections import defaultdict, deque
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from services.data_fetcher import normalize_ticker
from services.nse_stock_master import NSE_MASTER_LIST


class Trade(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    ticker: str = Field(min_length=1, max_length=30)
    buy_date: date
    sell_date: date
    buy_price: float = Field(gt=0, le=1e12)
    sell_price: float = Field(gt=0, le=1e12)
    qty: float = Field(gt=0, le=1e9)
    costs: float = Field(default=0, ge=0, le=1e18)

    @model_validator(mode="after")
    def ordered(self):
        self.ticker = normalize_ticker(self.ticker)
        if self.sell_date < self.buy_date:
            raise ValueError("Sell date is earlier than buy date.")
        if self.sell_date > date.today():
            raise ValueError("Trade date is in the future.")
        return self


def key(value):
    return re.sub(r"[^a-z0-9]", "", value.lower().lstrip("\ufeff"))


def parse_date(value):
    from datetime import datetime

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError("Use YYYY-MM-DD, DD-MM-YYYY or DD/MM/YYYY dates.")


def parse_trade_csv(text, broker="auto"):
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    fields = {key(f) for f in (reader.fieldnames or [])}
    if not fields:
        raise ValueError("CSV needs a header row.")
    executions = {"tradetype", "quantity", "price"} <= fields or {
        "type",
        "quantity",
        "price",
    } <= fields
    closed = {"buydate", "buyprice", "selldate", "sellprice"} <= fields
    if not executions and not closed:
        raise ValueError(
            "Unsupported CSV headers. Use the downloadable closed-trade template or an execution export with symbol, trade_date, trade_type, quantity and price."
        )
    if broker == "zerodha" and not executions:
        raise ValueError("Zerodha tradebook exports must contain trade_type, quantity and price.")
    trades, errors, warnings, entries = [], [], [], []
    total = 0
    for line, raw in enumerate(reader, 2):
        if line > 20001:
            raise ValueError("CSV limit is 20,000 rows.")
        if not any(raw.values()):
            continue
        total += 1
        row = {key(k): (v or "").strip() for k, v in raw.items() if k is not None}

        def field(*names, row=row):
            return next((row.get(name) for name in names if row.get(name)), "")

        try:
            symbol = field("ticker", "symbol", "tradingsymbol", "stocksymbol", "scripname")
            if not symbol:
                name = field("stockname").lower()
                symbol = next(
                    (s for s, m in NSE_MASTER_LIST.items() if m["name"].lower() == name),
                    "",
                )
            if not symbol:
                raise ValueError("Missing recognizable symbol; add a ticker column.")
            symbol = normalize_ticker(symbol)
            if executions:
                side = field("tradetype", "type", "buysell").lower()
                if side not in {"buy", "sell"}:
                    raise ValueError("Trade type must be buy or sell.")
                qty = float(field("quantity", "qty").replace(",", ""))
                price = float(field("price", "tradeprice").replace(",", ""))
                date_str = parse_date(field("tradedate", "date", "executiondate"))
                valid = Trade(
                    ticker=symbol,
                    buy_date=date_str,
                    sell_date=date_str,
                    buy_price=price,
                    sell_price=price,
                    qty=qty,
                )
                entries.append(
                    {
                        "ticker": symbol,
                        "side": side,
                        "qty": valid.qty,
                        "price": valid.buy_price,
                        "date": date_str,
                        "line": line,
                    }
                )
            else:
                valid = Trade(
                    ticker=symbol,
                    buy_date=parse_date(field("buydate")),
                    sell_date=parse_date(field("selldate")),
                    buy_price=float(field("buyprice").replace(",", "")),
                    sell_price=float(field("sellprice").replace(",", "")),
                    qty=float(field("qty", "quantity").replace(",", "")),
                    costs=float(field("costs", "fees") or 0),
                )
                trades.append(valid.model_dump(mode="json"))
        except (ValueError, TypeError) as exc:
            errors.append({"line": line, "message": str(exc).splitlines()[0][:200]})
    if entries:
        lots = defaultdict(deque)
        unmatched_sells = 0.0
        for entry in sorted(entries, key=lambda e: (e["date"], e["line"])):
            ticker, remaining = entry["ticker"], entry["qty"]
            if entry["side"] == "buy":
                lots[ticker].append(dict(entry))
                continue
            while remaining > 1e-9 and lots[ticker]:
                buy = lots[ticker][0]
                qty = min(remaining, buy["qty"])
                trades.append(
                    Trade(
                        ticker=ticker,
                        buy_date=buy["date"],
                        sell_date=entry["date"],
                        buy_price=buy["price"],
                        sell_price=entry["price"],
                        qty=qty,
                    ).model_dump(mode="json")
                )
                remaining -= qty
                buy["qty"] -= qty
                if buy["qty"] <= 1e-9:
                    lots[ticker].popleft()
            unmatched_sells += remaining
        open_qty = sum(lot["qty"] for queue in lots.values() for lot in queue)
        if unmatched_sells:
            warnings.append(
                f"{unmatched_sells:g} sold units could not be matched to earlier buys. Short positions or missing opening holdings are excluded."
            )
        if open_qty:
            warnings.append(
                f"{open_qty:g} bought units remain open and are excluded from closed-trade statistics."
            )
        warnings.append(
            "FIFO matching uses file order within a day. Execution exports exclude fees unless supplied as closed trades with a costs column. Each matched lot is a statistical observation."
        )
    if errors:
        warnings.append(
            f"{len(errors)} invalid rows were excluded. Review the row errors before interpreting the analysis."
        )
    if not trades:
        raise ValueError(
            "No valid closed trades could be matched. Check the headers, dates, prices and buy/sell history."
        )
    return {
        "trades": trades,
        "trade_count": len(trades),
        "row_count": total,
        "errors": errors[:100],
        "warnings": warnings,
        "matching": "FIFO" if executions else "closed_trade_rows",
    }
