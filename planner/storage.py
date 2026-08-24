from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

from .memory import MemoryState
from .models import ActivityType, Exam, StudySession, Subject, Topic, UserProfile

CURRENT_USER: ContextVar[str] = ContextVar("planner_user", default="default")

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS user_profiles (
 id TEXT PRIMARY KEY, daily_available_minutes INTEGER NOT NULL,
 minimum_subject_minutes_week INTEGER NOT NULL, review_fraction REAL NOT NULL,
 max_session_minutes INTEGER NOT NULL, rest_weekdays_json TEXT NOT NULL,
 energy_pattern_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS subjects (
 id TEXT PRIMARY KEY, name TEXT NOT NULL, exam_weight REAL NOT NULL, category TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS topics (
 id TEXT PRIMARY KEY, subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
 name TEXT NOT NULL, complexity REAL NOT NULL, estimated_hours REAL NOT NULL,
 mastery REAL NOT NULL, last_studied TEXT, next_review_due TEXT,
 self_difficulty REAL NOT NULL, volume REAL NOT NULL, cognitive_load REAL NOT NULL,
 knowledge_component_ids_json TEXT NOT NULL DEFAULT '[]',
 curriculum_node_ids_json TEXT NOT NULL DEFAULT '[]',
 block_id TEXT,
 mastery_uncertainty REAL NOT NULL DEFAULT 1.0,
 memory_retrievability REAL,
 workload_confidence REAL NOT NULL DEFAULT 0.25);
CREATE TABLE IF NOT EXISTS exams (
 id TEXT PRIMARY KEY, exam_date TEXT NOT NULL, subject_ids_json TEXT NOT NULL,
 topic_ids_json TEXT NOT NULL, weight REAL NOT NULL);
CREATE TABLE IF NOT EXISTS study_sessions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, session_date TEXT NOT NULL,
 topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
 planned_minutes INTEGER NOT NULL, actual_minutes INTEGER,
 session_type TEXT NOT NULL, performance_score REAL,
 activity_type TEXT NOT NULL DEFAULT 'mixed',
 completed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS memory_states (
 topic_id TEXT PRIMARY KEY REFERENCES topics(id) ON DELETE CASCADE,
 repetitions INTEGER NOT NULL DEFAULT 0,
 interval_days INTEGER NOT NULL DEFAULT 0,
 ease_factor REAL NOT NULL DEFAULT 2.5,
 stability_days REAL NOT NULL DEFAULT 0,
 last_rating REAL);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON study_sessions(session_date);
CREATE INDEX IF NOT EXISTS idx_sessions_topic ON study_sessions(topic_id);
CREATE INDEX IF NOT EXISTS idx_topics_subject ON topics(subject_id);
"""

TOPIC_MIGRATION_COLUMNS = {
    "knowledge_component_ids_json": "TEXT NOT NULL DEFAULT '[]'",
    "curriculum_node_ids_json": "TEXT NOT NULL DEFAULT '[]'",
    "block_id": "TEXT",
    "mastery_uncertainty": "REAL NOT NULL DEFAULT 1.0",
    "memory_retrievability": "REAL",
    "workload_confidence": "REAL NOT NULL DEFAULT 0.25",
}
SESSION_MIGRATION_COLUMNS = {
    "activity_type": "TEXT NOT NULL DEFAULT 'mixed'",
}


class StudyDB:
    def __init__(self, path: str | Path = "study_planner.db") -> None:
        self.path = str(path)
        self.initialize()

    def _path_for_user(self) -> str:
        user_id = CURRENT_USER.get()
        if user_id == "default":
            return self.path
        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:32]
        base = Path(self.path)
        return str(base.with_name(f"{base.stem}-{digest}{base.suffix}"))

    @staticmethod
    def _migrate_table_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, definition in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    @classmethod
    def _migrate_schema(cls, conn: sqlite3.Connection) -> None:
        cls._migrate_table_columns(conn, "topics", TOPIC_MIGRATION_COLUMNS)
        cls._migrate_table_columns(conn, "study_sessions", SESSION_MIGRATION_COLUMNS)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        path = Path(self._path_for_user())
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.executescript(SCHEMA)
            self._migrate_schema(conn)
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA)
            self._migrate_schema(conn)

    def save_profile(self, profile: UserProfile, user_id: str = "default") -> None:
        with self.connection() as conn:
            conn.execute("""INSERT INTO user_profiles VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET daily_available_minutes=excluded.daily_available_minutes,
            minimum_subject_minutes_week=excluded.minimum_subject_minutes_week,
            review_fraction=excluded.review_fraction, max_session_minutes=excluded.max_session_minutes,
            rest_weekdays_json=excluded.rest_weekdays_json, energy_pattern_json=excluded.energy_pattern_json""",
            (user_id, profile.daily_available_minutes, profile.minimum_subject_minutes_week, profile.review_fraction,
             profile.max_session_minutes, json.dumps(profile.rest_weekdays), json.dumps(profile.energy_pattern)))

    def get_profile(self, user_id: str = "default") -> UserProfile:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM user_profiles WHERE id=?", (user_id,)).fetchone()
        if not row:
            return UserProfile()
        return UserProfile(row["daily_available_minutes"], row["minimum_subject_minutes_week"], row["review_fraction"],
                           row["max_session_minutes"], tuple(json.loads(row["rest_weekdays_json"])),
                           tuple(json.loads(row["energy_pattern_json"])))

    def upsert_subject(self, subject: Subject) -> None:
        with self.connection() as conn:
            conn.execute("INSERT INTO subjects VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, exam_weight=excluded.exam_weight, category=excluded.category",
                         (subject.id, subject.name, subject.exam_weight, subject.category))

    def delete_subject(self, subject_id: str) -> None:
        with self.connection() as conn:
            if conn.execute("SELECT 1 FROM subjects WHERE id=?", (subject_id,)).fetchone() is None:
                raise KeyError(subject_id)
            exam_rows = conn.execute("SELECT id, subject_ids_json FROM exams").fetchall()
            if any(subject_id in json.loads(row["subject_ids_json"] or "[]") for row in exam_rows):
                raise ValueError("subject is referenced by an exam; remove that exam coverage first")
            conn.execute("DELETE FROM subjects WHERE id=?", (subject_id,))

    def upsert_topic(self, topic: Topic) -> None:
        with self.connection() as conn:
            if conn.execute("SELECT 1 FROM subjects WHERE id=?", (topic.subject_id,)).fetchone() is None:
                raise ValueError("subject does not exist")
            conn.execute("""
                INSERT INTO topics (
                    id, subject_id, name, complexity, estimated_hours, mastery,
                    last_studied, next_review_due, self_difficulty, volume, cognitive_load,
                    knowledge_component_ids_json, curriculum_node_ids_json, block_id,
                    mastery_uncertainty, memory_retrievability, workload_confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    subject_id=excluded.subject_id,
                    name=excluded.name,
                    complexity=excluded.complexity,
                    estimated_hours=excluded.estimated_hours,
                    mastery=excluded.mastery,
                    last_studied=excluded.last_studied,
                    next_review_due=excluded.next_review_due,
                    self_difficulty=excluded.self_difficulty,
                    volume=excluded.volume,
                    cognitive_load=excluded.cognitive_load,
                    knowledge_component_ids_json=excluded.knowledge_component_ids_json,
                    curriculum_node_ids_json=excluded.curriculum_node_ids_json,
                    block_id=excluded.block_id,
                    mastery_uncertainty=excluded.mastery_uncertainty,
                    memory_retrievability=excluded.memory_retrievability,
                    workload_confidence=excluded.workload_confidence
            """, (
                topic.id, topic.subject_id, topic.name, topic.complexity, topic.estimated_hours, topic.mastery,
                topic.last_studied.isoformat() if topic.last_studied else None,
                topic.next_review_due.isoformat() if topic.next_review_due else None,
                topic.self_difficulty, topic.volume, topic.cognitive_load,
                json.dumps(topic.knowledge_component_ids), json.dumps(topic.curriculum_node_ids), topic.block_id,
                topic.mastery_uncertainty, topic.memory_retrievability, topic.workload_confidence,
            ))

    def delete_topic(self, topic_id: str) -> None:
        with self.connection() as conn:
            if conn.execute("SELECT 1 FROM topics WHERE id=?", (topic_id,)).fetchone() is None:
                raise KeyError(topic_id)
            exam_rows = conn.execute("SELECT id, topic_ids_json FROM exams").fetchall()
            if any(topic_id in json.loads(row["topic_ids_json"] or "[]") for row in exam_rows):
                raise ValueError("topic is referenced by an exam; remove that exam coverage first")
            conn.execute("DELETE FROM topics WHERE id=?", (topic_id,))

    def upsert_exam(self, exam: Exam) -> None:
        with self.connection() as conn:
            missing_subjects = [s for s in exam.subject_ids if conn.execute("SELECT 1 FROM subjects WHERE id=?", (s,)).fetchone() is None]
            missing_topics = [t for t in exam.topic_ids if conn.execute("SELECT 1 FROM topics WHERE id=?", (t,)).fetchone() is None]
            if missing_subjects or missing_topics:
                raise ValueError("exam coverage contains unknown subject/topic ids")
            conn.execute("INSERT INTO exams VALUES (?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET exam_date=excluded.exam_date,subject_ids_json=excluded.subject_ids_json,topic_ids_json=excluded.topic_ids_json,weight=excluded.weight",
                         (exam.id, exam.date.isoformat(), json.dumps(exam.subject_ids), json.dumps(exam.topic_ids), exam.weight))

    def delete_exam(self, exam_id: str) -> None:
        with self.connection() as conn:
            if conn.execute("SELECT 1 FROM exams WHERE id=?", (exam_id,)).fetchone() is None:
                raise KeyError(exam_id)
            conn.execute("DELETE FROM exams WHERE id=?", (exam_id,))

    def save_curriculum(self, subjects: list[Subject], topics: list[Topic], exams: list[Exam]) -> None:
        for subject in subjects:
            self.upsert_subject(subject)
        for topic in topics:
            self.upsert_topic(topic)
        for exam in exams:
            self.upsert_exam(exam)

    def load_curriculum(self) -> tuple[list[Subject], list[Topic], list[Exam]]:
        snap = self.snapshot()
        subjects = [Subject(s["id"], s["name"], s["exam_weight"], s["category"]) for s in snap["subjects"]]
        topics = [self._topic_from_row_dict(t) for t in snap["topics"]]
        exams = [Exam(e["id"], date.fromisoformat(e["exam_date"]), tuple(json.loads(e["subject_ids_json"])), tuple(json.loads(e["topic_ids_json"])), e["weight"]) for e in snap["exams"]]
        return subjects, topics, exams

    def save_sessions(self, sessions: list[StudySession]) -> list[int]:
        ids: list[int] = []
        with self.connection() as conn:
            for s in sessions:
                cur = conn.execute(
                    "INSERT INTO study_sessions (session_date, topic_id, planned_minutes, actual_minutes, session_type, performance_score, activity_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (s.date.isoformat(), s.topic_id, s.planned_minutes, s.actual_minutes, s.session_type.value, s.performance_score, s.activity.value),
                )
                ids.append(int(cur.lastrowid))
        return ids

    def reschedule_session(self, session_id: int, new_date: date) -> None:
        with self.connection() as conn:
            row = conn.execute("SELECT completed FROM study_sessions WHERE id=?", (session_id,)).fetchone()
            if not row:
                raise KeyError(f"session {session_id} not found")
            if row["completed"]:
                raise ValueError("completed sessions cannot be rescheduled")
            conn.execute("UPDATE study_sessions SET session_date=? WHERE id=?", (new_date.isoformat(), session_id))

    def delete_uncompleted_sessions_in_range(self, start: date, end: date, preserve_ids: set[int] | None = None) -> None:
        preserve_ids = preserve_ids or set()
        with self.connection() as conn:
            if preserve_ids:
                placeholders = ",".join("?" for _ in preserve_ids)
                conn.execute(f"DELETE FROM study_sessions WHERE completed=0 AND session_date>=? AND session_date<? AND id NOT IN ({placeholders})", [start.isoformat(), end.isoformat(), *sorted(preserve_ids)])
            else:
                conn.execute("DELETE FROM study_sessions WHERE completed=0 AND session_date>=? AND session_date<?", (start.isoformat(), end.isoformat()))

    def get_topic_for_session(self, session_id: int) -> Topic | None:
        with self.connection() as conn:
            row = conn.execute("SELECT t.* FROM study_sessions s JOIN topics t ON t.id=s.topic_id WHERE s.id=?", (session_id,)).fetchone()
        return self._topic_from_row(row) if row else None

    def complete_session(self, session_id: int, actual_minutes: int, performance_score: float) -> None:
        if actual_minutes < 0 or not 0 <= performance_score <= 1:
            raise ValueError("actual_minutes must be >= 0 and performance_score must be in [0, 1]")
        with self.connection() as conn:
            n = conn.execute("UPDATE study_sessions SET actual_minutes=?, performance_score=?, completed=1 WHERE id=? AND completed=0", (actual_minutes, performance_score, session_id)).rowcount
        if n != 1:
            with self.connection() as conn:
                exists = conn.execute("SELECT completed FROM study_sessions WHERE id=?", (session_id,)).fetchone()
            if exists is None:
                raise KeyError(f"session {session_id} not found")
            raise ValueError(f"session {session_id} is already completed")

    def get_memory_state(self, topic_id: str) -> MemoryState:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM memory_states WHERE topic_id=?", (topic_id,)).fetchone()
        if not row:
            return MemoryState()
        return MemoryState(row["repetitions"], row["interval_days"], row["ease_factor"], row["stability_days"], row["last_rating"])

    def save_memory_state(self, topic_id: str, state: MemoryState) -> None:
        with self.connection() as conn:
            conn.execute("""INSERT INTO memory_states VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(topic_id) DO UPDATE SET repetitions=excluded.repetitions,
            interval_days=excluded.interval_days,ease_factor=excluded.ease_factor,
            stability_days=excluded.stability_days,last_rating=excluded.last_rating""",
            (topic_id, state.repetitions, state.interval_days, state.ease_factor, state.stability_days, state.last_rating))

    @staticmethod
    def _topic_from_row_dict(row: dict) -> Topic:
        return Topic(
            id=row["id"], subject_id=row["subject_id"], name=row["name"], complexity=row["complexity"],
            estimated_hours=row["estimated_hours"], mastery=row["mastery"],
            last_studied=date.fromisoformat(row["last_studied"]) if row["last_studied"] else None,
            next_review_due=date.fromisoformat(row["next_review_due"]) if row["next_review_due"] else None,
            self_difficulty=row["self_difficulty"], volume=row["volume"], cognitive_load=row["cognitive_load"],
            knowledge_component_ids=tuple(json.loads(row.get("knowledge_component_ids_json") or "[]")),
            curriculum_node_ids=tuple(json.loads(row.get("curriculum_node_ids_json") or "[]")),
            block_id=row.get("block_id"), mastery_uncertainty=float(row.get("mastery_uncertainty") or 1.0),
            memory_retrievability=row.get("memory_retrievability"), workload_confidence=float(row.get("workload_confidence") or 0.25),
        )

    @classmethod
    def _topic_from_row(cls, row: sqlite3.Row) -> Topic:
        return cls._topic_from_row_dict(dict(row))

    def get_topic(self, topic_id: str) -> Topic | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
        return self._topic_from_row(row) if row else None

    def update_topic(self, topic: Topic) -> None:
        self.upsert_topic(topic)

    def weekly_completed_minutes(self, week_start: date, subject_id: str) -> int:
        week_end = week_start + timedelta(days=7)
        with self.connection() as conn:
            row = conn.execute("SELECT COALESCE(SUM(s.actual_minutes),0) minutes FROM study_sessions s JOIN topics t ON t.id=s.topic_id WHERE s.completed=1 AND t.subject_id=? AND s.session_date>=? AND s.session_date<?", (subject_id, week_start.isoformat(), week_end.isoformat())).fetchone()
        return int(row["minutes"])

    def snapshot(self) -> dict:
        with self.connection() as conn:
            return {name: [dict(r) for r in conn.execute(sql)] for name, sql in {
                "subjects":"SELECT * FROM subjects ORDER BY id",
                "topics":"SELECT * FROM topics ORDER BY subject_id,id",
                "exams":"SELECT * FROM exams ORDER BY exam_date",
                "sessions":"SELECT * FROM study_sessions ORDER BY session_date,id",
                "memory_states":"SELECT * FROM memory_states ORDER BY topic_id",
            }.items()}
