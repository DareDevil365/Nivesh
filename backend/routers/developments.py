from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from services import company_events
from services.data_fetcher import normalize_ticker
from services.local_store import workspace
from services.research_workflow import cached_research

router = APIRouter(prefix="/api/companies", tags=["developments"])


class ProjectObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    stage: str = Field(min_length=1, max_length=50)
    source_url: HttpUrl
    source_quote: str = Field(min_length=12, max_length=2000)
    source_date: date | None = None
    expected_date: date | None = None
    expected_date_kind: Literal["source_stated", "researcher_estimate"] | None = None
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def validate_source(self):
        if len(str(self.source_url)) > 2048 or not company_events.public_link(self.source_url):
            raise ValueError("Use a public HTTPS source link without embedded credentials.")
        if self.source_date and self.source_date > company_events.today_india():
            raise ValueError("Source publication date cannot be in the future.")
        if bool(self.expected_date) != bool(self.expected_date_kind):
            raise ValueError(
                "An expected date needs an explicit source-stated or researcher-estimate label."
            )
        return self


class ProjectCreate(ProjectObservation):
    title: str = Field(min_length=3, max_length=180)
    kind: Literal["tender", "expansion", "approval", "acquisition", "other"]
    reference: str = Field(default="", max_length=160)

    @model_validator(mode="after")
    def validate_stage(self):
        if self.stage not in company_events.LIFECYCLES[self.kind]:
            raise ValueError("Stage does not belong to this project type.")
        return self


class ProjectUpdate(ProjectObservation):
    expected_version: int = Field(ge=1)


@router.get("/{ticker}/developments")
def get_developments(ticker: str):
    symbol = normalize_ticker(ticker)
    return company_events.developments(symbol, cached_research(symbol))


@router.get("/{ticker}/pending-items")
def get_pending(ticker: str, response: Response, owner=Depends(workspace)):
    response.headers["Cache-Control"] = "no-store"
    return company_events.list_projects(owner, normalize_ticker(ticker))


@router.post("/{ticker}/pending-items", status_code=201)
def create_pending(
    ticker: str, payload: ProjectCreate, response: Response, owner=Depends(workspace)
):
    response.headers["Cache-Control"] = "no-store"
    return company_events.create_project(
        owner, normalize_ticker(ticker), payload.model_dump(mode="json")
    )


@router.post("/{ticker}/pending-items/{identifier}/observations")
def update_pending(
    ticker: str,
    identifier: str,
    payload: ProjectUpdate,
    response: Response,
    owner=Depends(workspace),
):
    response.headers["Cache-Control"] = "no-store"
    return company_events.update_project(
        owner, normalize_ticker(ticker), identifier, payload.model_dump(mode="json")
    )


@router.delete("/{ticker}/pending-items/{identifier}")
def remove_pending(
    ticker: str,
    identifier: str,
    response: Response,
    version: int = Query(ge=1),
    owner=Depends(workspace),
):
    response.headers["Cache-Control"] = "no-store"
    return company_events.delete_project(owner, normalize_ticker(ticker), identifier, version)
