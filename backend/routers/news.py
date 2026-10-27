import re

from fastapi import APIRouter, HTTPException, Query

from services import news_digest, news_reader
from services.data_fetcher import get_company_profile

router = APIRouter(tags=["news"])


@router.get("/api/news/digest/latest")
def get_latest_digest():
    return {"digest": news_digest.latest()}


@router.get("/api/news/reading-desk")
def get_reading_desk(refresh: bool = False):
    return news_reader.reading_desk(refresh)


@router.get("/api/news/topic")
def get_topic(topic: str = Query(min_length=3, max_length=100), refresh: bool = False):
    phrase = " ".join(re.findall(r"[\w&.-]+", topic))
    if len(phrase) < 3:
        raise HTTPException(422, "Enter a topic with at least three letters or numbers.")
    return news_reader.feed('"' + phrase + '"', days=7, locale="IN", refresh=refresh)


@router.get("/api/companies/{ticker}/news")
def get_company_news(ticker: str, refresh: bool = False):
    return news_reader.company_news(get_company_profile(ticker), refresh=refresh)


@router.get("/api/companies/{ticker}/community")
def get_community(ticker: str, refresh: bool = False):
    return news_reader.community(get_company_profile(ticker), refresh)
