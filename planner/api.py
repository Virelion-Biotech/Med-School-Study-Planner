from fastapi import FastAPI
from pydantic import BaseModel, Field
from datetime import date

from .models import Exam, PriorityWeights, Subject, Topic, UserProfile
from .scheduler import generate_week

app = FastAPI(title="Med School Study Planner", version="0.1.0")


class PlanRequest(BaseModel):
    subjects: list[Subject]
    topics: list[Topic]
    exams: list[Exam] = []
    profile: UserProfile = UserProfile()
    start_date: date
    days: int = Field(default=7, ge=1, le=31)
    weights: PriorityWeights = PriorityWeights()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "rule-based-v1"}


@app.post("/plan")
def plan(request: PlanRequest):
    sessions = generate_week(
        request.subjects, request.topics, request.exams, request.profile,
        request.start_date, request.days, request.weights,
    )
    return {"sessions": [s.__dict__ | {"session_type": s.session_type.value} for s in sessions]}
