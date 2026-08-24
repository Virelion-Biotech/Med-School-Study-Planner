from __future__ import annotations

from dataclasses import asdict

from fastapi import HTTPException
from pydantic import BaseModel, Field

from .adaptive_db import AdaptiveDB
from .api import app, db
from .cross_curriculum import CurriculumMapping

_adaptive_db = AdaptiveDB(db)


class CurriculumMappingRequest(BaseModel):
    knowledge_component_id: str = Field(min_length=1, max_length=200)
    curriculum_node_id: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=100)
    confidence: float = Field(default=1.0, ge=0, le=1)
    relation: str = Field(default="covers", min_length=1, max_length=100)


@app.post("/v2/curriculum/mappings")
def save_curriculum_mapping(request: CurriculumMappingRequest):
    if not _adaptive_db.load_knowledge_components_for_id(request.knowledge_component_id):
        raise HTTPException(status_code=404, detail="Knowledge component not found")
    if not any(node.id == request.curriculum_node_id for node in _adaptive_db.load_curriculum_nodes()):
        raise HTTPException(status_code=404, detail="Curriculum node not found")
    mapping = CurriculumMapping(
        request.knowledge_component_id,
        request.curriculum_node_id,
        request.source,
        request.confidence,
        request.relation,
    )
    _adaptive_db.save_curriculum_mappings([mapping])
    return {"status": "saved", "mapping": asdict(mapping)}


@app.get("/v2/curriculum/mappings/kc/{knowledge_component_id}")
def get_kc_curriculum_mappings(knowledge_component_id: str):
    if not _adaptive_db.load_knowledge_components_for_id(knowledge_component_id):
        raise HTTPException(status_code=404, detail="Knowledge component not found")
    mappings = _adaptive_db.curriculum_mappings_for_kc(knowledge_component_id)
    return {"knowledge_component_id": knowledge_component_id, "mappings": [asdict(m) for m in mappings]}


@app.get("/v2/curriculum/mappings/node/{curriculum_node_id}")
def get_node_knowledge_components(curriculum_node_id: str):
    if not any(node.id == curriculum_node_id for node in _adaptive_db.load_curriculum_nodes()):
        raise HTTPException(status_code=404, detail="Curriculum node not found")
    components = _adaptive_db.knowledge_components_for_node(curriculum_node_id)
    return {"curriculum_node_id": curriculum_node_id, "knowledge_components": [asdict(k) for k in components]}


@app.get("/v2/topic/{topic_id}/cross-curriculum")
def get_topic_cross_curriculum(topic_id: str):
    if db.get_topic(topic_id) is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    components = _adaptive_db.load_knowledge_components(topic_id)
    result = []
    for component in components:
        result.append({
            "knowledge_component": asdict(component),
            "mappings": [asdict(m) for m in _adaptive_db.curriculum_mappings_for_kc(component.id)],
        })
    return {"topic_id": topic_id, "knowledge_components": result}
