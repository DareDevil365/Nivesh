import json
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services.local_store import connection, workspace

router = APIRouter(prefix="/api/reports", tags=["reports"])


class UserReportPayload(BaseModel):
    category: Literal[
        "data_inaccuracy",
        "supply_chain_error",
        "snowflake_anomaly",
        "chart_visual_bug",
        "feature_suggestion",
        "other",
    ] = "data_inaccuracy"
    description: str = Field(min_length=5, max_length=5000)
    ticker: Optional[str] = Field(default=None, max_length=30)
    route: Optional[str] = Field(default=None, max_length=300)
    tab: Optional[str] = Field(default=None, max_length=80)


@router.post("")
def submit_report(payload: UserReportPayload, owner=Depends(workspace)):
    if len(payload.description.strip()) < 5:
        raise HTTPException(422, "Please describe the issue in at least 5 characters.")
    report_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    with connection() as db:
        if db.execute("SELECT COUNT(*) FROM reports WHERE owner=?", (owner,)).fetchone()[0] >= 100:
            raise HTTPException(409, "Workspace report limit reached.")
        db.execute(
            "INSERT INTO reports VALUES(?,?,?,?)",
            (report_id, owner, json.dumps(payload.model_dump()), timestamp),
        )
    return {
        "success": True,
        "report_id": report_id,
        "message": "Feedback saved. Reports are visible only in this browser workspace.",
    }


@router.get("")
def get_reports(limit: int = Query(50, ge=1, le=100), owner=Depends(workspace)):
    with connection() as db:
        rows = db.execute(
            "SELECT id,payload,created_at FROM reports WHERE owner=? ORDER BY created_at DESC LIMIT ?",
            (owner, limit),
        ).fetchall()
    return {
        "reports": [
            {
                "id": row["id"],
                "timestamp": row["created_at"],
                **json.loads(row["payload"]),
            }
            for row in rows
        ]
    }
