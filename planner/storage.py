from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

from .models import Exam, StudySession, Subject, Topic, UserProfile

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
 self_difficulty REAL NOT NULL, volume REAL NOT NULL, cognitive_load REAL NOT NULL);
CREATE TABLE IF NOT EXISTS exams (
 id TEXT PRIMARY KEY, exam_date TEXT NOT NULL, subject_ids_json TEXT NOT NULL,
 topic_ids_json TEXT NOT NULL, weight REAL NOT NULL);
CREATE TABLE IF NOT EXISTS study_sessions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, session_date TEXT NOT NULL,
 topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
 planned_minutes INTEGER NOT NULL, actual_minutes INTEGER,
 session_type TEXT NOT NULL, performance_score REAL,
 completed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON study_sessions(session_date);
CREATE INDEX IF NOT EXISTS idx_sessions_topic ON study_sessions(topic_id);
CREATE INDEX IF NOT EXISTS idx_topics_subject ON topics(subject_id);
"""

class StudyDB:
    def __init__(self, path: str | Path = "study_planner.db") -> None:
        self.path = str(path)
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    def save_profile(self, profile: UserProfile, user_id: str = "default") -> None:
        with self.connection() as conn:
            conn.execute(
                """INSERT INTO user_profiles VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET daily_available_minutes=excluded.daily_available_minutes,
                minimum_subject_minutes_week=excluded.minimum_subject_minutes_week,
                review_fraction=excluded.review_fraction, max_session_minutes=excluded.max_session_minutes,
                rest_weekdays_json=excluded.rest_weekdays_json, energy_pattern_json=excluded.energy_pattern_json""",
                (user_id, profile.daily_available_minutes, profile.minimum_subject_minutes_week,
                 profile.review_fraction, profile.max_session_minutes, json.dumps(profile.rest_weekdays),
                 json.dumps(profile.energy_pattern)),
            )

    def save_curriculum(self, subjects: list[Subject], topics: list[Topic], exams: list[Exam]) -> None:
        with self.connection() as conn:
            for s in subjects:
                conn.execute("INSERT OR REPLACE INTO subjects VALUES (?, ?, ?, ?)",
                             (s.id, s.name, s.exam_weight, s.category))
            for t in topics:
                conn.execute("INSERT OR REPLACE INTO topics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (t.id, t.subject_id, t.name, t.complexity, t.estimated_hours, t.mastery,
                              t.last_studied.isoformat() if t.last_studied else None,
                              t.next_review_due.isoformat() if t.next_review_due else None,
                              t.self_difficulty, t.volume, t.cognitive_load))
            for e in exams:
                conn.execute("INSERT OR REPLACE INTO exams VALUES (?, ?, ?, ?, ?)",
                             (e.id, e.date.isoformat(), json.dumps(e.subject_ids), json.dumps(e.topic_ids), e.weight))

    def save_sessions(self, sessions: list[StudySession]) -> None:
        with self.connection() as conn:
            for s in sessions:
                conn.execute(
                    "INSERT INTO study_sessions (session_date, topic_id, planned_minutes, actual_minutes, session_type, performance_score) VALUES (?, ?, ?, ?, ?, ?)",
                    (s.date.isoformat(), s.topic_id, s.planned_minutes, s.actual_minutes, s.session_type.value, s.performance_score),
                )

    def get_topic_for_session(self, session_id: int) -> Topic | None:
        with self.connection() as conn:
            row = conn.execute("SELECT t.* FROM study_sessions s JOIN topics t ON t.id=s.topic_id WHERE s.id=?", (session_id,)).fetchone()
        return self._topic_from_row(row) if row else None

    def complete_session(self, session_id: int, actual_minutes: int, performance_score: float) -> None:
        if actual_minutes < 0 or not 0 <= performance_score <= 1:
            raise ValueError("actual_minutes must be >= 0 and performance_score must be in [0, 1]")
        with self.connection() as conn:
            updated = conn.execute("UPDATE study_sessions SET actual_minutes=?, performance_score=?, completed=1 WHERE id=?", (actual_minutes, performance_score, session_id)).rowcount
        if updated != 1:
            raise KeyError(f"session {session_id} not found")

    @staticmethod
    def _topic_from_row(row: sqlite3.Row) -> Topic:
        return Topic(
            id=row["id"], subject_id=row["subject_id"], name=row["name"], complexity=row["complexity"],
            estimated_hours=row["estimated_hours"], mastery=row["mastery"],
            last_studied=date.fromisoformat(row["last_studied"]) if row["last_studied"] else None,
            next_review_due=date.fromisoformat(row["next_review_due"]) if row["next_review_due"] else None,
            self_difficulty=row["self_difficulty"], volume=row["volume"], cognitive_load=row["cognitive_load"],
        )

    def get_topic(self, topic_id: str) -> Topic | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM topics WHERE id=?", (topic_id,)).fetchone()
        return self._topic_from_row(row) if row else None

    def update_topic(self, topic: Topic) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE topics SET complexity=?, estimated_hours=?, mastery=?, last_studied=?, next_review_due=?, self_difficulty=?, volume=?, cognitive_load=? WHERE id=?",
                (topic.complexity, topic.estimated_hours, topic.mastery,
                 topic.last_studied.isoformat() if topic.last_studied else None,
                 topic.next_review_due.isoformat() if topic.next_review_due else None,
                 topic.self_difficulty, topic.volume, topic.cognitive_load, topic.id),
            )

    def weekly_completed_minutes(self, week_start: date, subject_id: str) -> int:
        week_end = week_start + timedelta(days=7)
        with self.connection() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(s.actual_minutes), 0) minutes FROM study_sessions s JOIN topics t ON t.id=s.topic_id WHERE s.completed=1 AND t.subject_id=? AND s.session_date>=? AND s.session_date<?",
                (subject_id, week_start.isoformat(), week_end.isoformat()),
            ).fetchone()
        return int(row["minutes"])

    def snapshot(self) -> dict:
        with self.connection() as conn:
            return {name: [dict(r) for r in conn.execute(sql)] for name, sql in {
                "subjects": "SELECT * FROM subjects ORDER BY id",
                "topics": "SELECT * FROM topics ORDER BY subject_id, id",
                "exams": "SELECT * FROM exams ORDER BY exam_date",
                "sessions": "SELECT * FROM study_sessions ORDER BY session_date, id",
            }.items()}
