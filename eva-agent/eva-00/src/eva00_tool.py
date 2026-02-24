#!/usr/bin/env python3
"""EVA-00 Query Tool — HTTP API that EVA-00 calls via exec/curl.

Run this as a service. EVA-00 queries it via:
  curl -s localhost:8100/query -d '{"action":"search_submittals","project":"BTV5","keyword":"HVAC"}'

This keeps the database layer clean and lets EVA-00 use it from any OpenClaw session.
"""

import json
import sys
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Any
import uvicorn

# Add parent to path
sys.path.insert(0, "/home/moby/.openclaw/workspace/eva-agent/eva-00/src")
import database as db

app = FastAPI(title="EVA-00 Query Service")


class QueryRequest(BaseModel):
    action: str
    project: Optional[str] = None
    project_id: Optional[int] = None
    keyword: Optional[str] = None
    spec_section: Optional[str] = None
    status: Optional[str] = None
    number: Optional[str] = None
    discipline: Optional[str] = None
    drawing_ref: Optional[str] = None
    company: Optional[str] = None
    trade: Optional[str] = None
    company_id: Optional[int] = None
    submittal_id: Optional[int] = None
    rfi_id: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: Optional[int] = 25
    query: Optional[str] = None  # For search_all


def resolve_project_id(req: QueryRequest) -> Optional[int]:
    """Resolve a project name to an ID."""
    if req.project_id:
        return req.project_id
    if req.project:
        proj = db.get_project(name=req.project)
        if proj:
            return proj["id"]
    return None


def format_response(data: Any, action: str) -> dict:
    """Format response for readability."""
    if isinstance(data, list):
        return {
            "action": action,
            "count": len(data),
            "results": data
        }
    return {"action": action, "result": data}


@app.post("/query")
async def query(req: QueryRequest):
    """Main query endpoint — routes to the appropriate database function."""
    try:
        pid = resolve_project_id(req)

        if req.action == "list_projects":
            data = db.list_projects()

        elif req.action == "get_project":
            data = db.get_project(project_id=pid, name=req.project)

        elif req.action == "project_stats":
            if not pid:
                return {"error": "Project not found"}
            data = db.get_project_stats(pid)

        elif req.action == "search_submittals":
            data = db.search_submittals(
                project_id=pid, spec_section=req.spec_section,
                keyword=req.keyword, status=req.status,
                number=req.number, limit=req.limit
            )

        elif req.action == "submittal_history":
            if not req.submittal_id:
                return {"error": "submittal_id required"}
            data = db.get_submittal_history(req.submittal_id)

        elif req.action == "similar_submittals":
            if not req.submittal_id:
                return {"error": "submittal_id required"}
            data = db.get_submittal_with_similar(req.submittal_id)

        elif req.action == "search_rfis":
            data = db.search_rfis(
                project_id=pid, keyword=req.keyword,
                status=req.status, number=req.number, limit=req.limit
            )

        elif req.action == "rfi_detail":
            if not req.rfi_id:
                return {"error": "rfi_id required"}
            data = db.get_rfi_with_responses(req.rfi_id)

        elif req.action == "similar_rfis":
            data = db.find_similar_rfis(
                rfi_id=req.rfi_id, keyword=req.keyword,
                spec_section=req.spec_section
            )

        elif req.action == "search_drawings":
            data = db.search_drawings(
                project_id=pid, discipline=req.discipline,
                number=req.number, keyword=req.keyword, limit=req.limit
            )

        elif req.action == "search_companies":
            data = db.search_companies(name=req.company, trade=req.trade)

        elif req.action == "company_history":
            if not req.company_id:
                return {"error": "company_id required"}
            data = db.get_company_history(req.company_id)

        elif req.action == "search_daily_reports":
            data = db.search_daily_reports(
                project_id=pid, date_from=req.date_from,
                date_to=req.date_to, keyword=req.keyword, limit=req.limit
            )

        elif req.action == "search_all":
            q = req.query or req.keyword
            if not q:
                return {"error": "query or keyword required"}
            data = db.search_all(q, project_id=pid, limit=req.limit)

        elif req.action == "database_stats":
            data = db.get_database_stats()

        else:
            return {"error": f"Unknown action: {req.action}"}

        return format_response(data, req.action)

    except Exception as e:
        return {"error": str(e)}


@app.get("/health")
async def health():
    try:
        stats = db.get_database_stats()
        return {"status": "ok", "tables": stats}
    except Exception as e:
        return {"status": "error", "error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100, log_level="info")
