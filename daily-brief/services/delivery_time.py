"""Prepare early; gate actual delivery to six AM IST without changing daily IDs."""

import os
import time
from datetime import datetime, timedelta, timezone

from services.news_bot import BotError

IST = timezone(timedelta(hours=5, minutes=30))


def seconds_until_six(now):
    local = now.astimezone(IST)
    target = local.replace(hour=6, minute=0, second=0, microsecond=0)
    return max(0, (target - local).total_seconds())


def wait_until_six(now=None, sleep=time.sleep):
    if os.getenv("NEWS_HOLD_UNTIL_6AM", "false").lower() != "true":
        return
    clock = now or (lambda: datetime.now(timezone.utc))
    first = clock()
    day = first.astimezone(IST).date()
    delay = seconds_until_six(first)
    if delay > 25 * 60:
        raise BotError("Early-delivery hold was requested outside its supported morning window.")
    if delay:
        print("Prepared; holding delivery until 06:00 IST.", flush=True)
    while delay > 0:
        sleep(min(delay, 30))
        current = clock()
        if current.astimezone(IST).date() != day:
            raise BotError("The delivery date changed during the morning hold.")
        delay = seconds_until_six(current)
