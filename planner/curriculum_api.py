from __future__ import annotations

from dataclasses import asdict

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .adaptive_db import AdaptiveDB
from .api import app, db
from .curriculum_ingest import CurriculumRecord, ingest_records, validate_snapshot

_adaptive_db = AdaptiveDB(db)


class CurriculumImportRecord(BaseModel):
    external_id: str | None = None
    name: str = Field(min_length=1, max_length=300)
    node_type: str = Field(min_length=1, max_length=100)
    parent_external_id: str | None = None


class CurriculumImportRequest(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)
    dry_run: bool = False
    records: list[CurriculumImportRecord] = Field(min_length=1, max_length=50000)


@app.get("/v2/curriculum/snapshots")
def curriculum_snapshots(source: str | None = None):
    return {"snapshots": _adaptive_db.list_curriculum_snapshots(source)}


@app.post("/v2/curriculum/import")
def import_curriculum(request: CurriculumImportRequest):
    records = [
        CurriculumRecord(request.source, r.external_id, r.name, r.node_type, r.parent_external_id)
        for r in request.records
    ]
    snapshot = ingest_records(request.source, request.version, records)
    issues = validate_snapshot(snapshot)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors and not request.dry_run:
        raise HTTPException(
            status_code=400,
            detail={"message": "curriculum validation failed", "issues": [asdict(issue) for issue in issues]},
        )
    if not request.dry_run:
        _adaptive_db.save_curriculum_snapshot(snapshot)
        _adaptive_db.save_curriculum_nodes(list(snapshot.nodes))
    return {
        "source": snapshot.source,
        "version": snapshot.version,
        "fingerprint": snapshot.fingerprint,
        "dry_run": request.dry_run,
        "node_count": len(snapshot.nodes),
        "issues": [asdict(issue) for issue in issues],
    }


@app.post("/v2/curriculum/import/validate")
def validate_curriculum_import(request: CurriculumImportRequest):
    request = request.model_copy(update={"dry_run": True})
    return import_curriculum(request)
