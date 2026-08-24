from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any

from .cross_curriculum import CurriculumMapping, deduplicate_mappings
from .models import clamp
from .state import CurriculumNode, KnowledgeComponent, StudentFSRSState, StudentKnowledgeState
from .storage import StudyDB


class AdaptiveDB:
    """Persistence boundary for V2 learning state."""

    def __init__(self, db: StudyDB) -> None:
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.db.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS curriculum_nodes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    parent_id TEXT,
                    source TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_curriculum_parent ON curriculum_nodes(parent_id);
                CREATE TABLE IF NOT EXISTS curriculum_snapshots (
                    source TEXT NOT NULL,
                    version TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    nodes_json TEXT NOT NULL,
                    issues_json TEXT NOT NULL,
                    PRIMARY KEY(source, version)
                );
                CREATE INDEX IF NOT EXISTS idx_curriculum_snapshot_source ON curriculum_snapshots(source, created_at);
                CREATE TABLE IF NOT EXISTS topic_curriculum_links (
                    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                    node_id TEXT NOT NULL REFERENCES curriculum_nodes(id) ON DELETE CASCADE,
                    PRIMARY KEY(topic_id,node_id)
                );
                CREATE INDEX IF NOT EXISTS idx_topic_curriculum_node ON topic_curriculum_links(node_id);
                CREATE TABLE IF NOT EXISTS knowledge_components (
                    id TEXT PRIMARY KEY,
                    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    initial_mastery REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_kc_topic ON knowledge_components(topic_id);
                CREATE TABLE IF NOT EXISTS knowledge_component_curriculum_links (
                    knowledge_component_id TEXT NOT NULL REFERENCES knowledge_components(id) ON DELETE CASCADE,
                    node_id TEXT NOT NULL REFERENCES curriculum_nodes(id) ON DELETE CASCADE,
                    source TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    relation TEXT NOT NULL DEFAULT 'covers',
                    PRIMARY KEY(knowledge_component_id,node_id,relation)
                );
                CREATE INDEX IF NOT EXISTS idx_kc_curriculum_node ON knowledge_component_curriculum_links(node_id);
                CREATE TABLE IF NOT EXISTS student_knowledge (
                    knowledge_component_id TEXT PRIMARY KEY REFERENCES knowledge_components(id) ON DELETE CASCADE,
                    mastery_probability REAL NOT NULL,
                    uncertainty REAL NOT NULL,
                    observations INTEGER NOT NULL,
                    last_observed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS student_fsrs (
                    topic_id TEXT PRIMARY KEY REFERENCES topics(id) ON DELETE CASCADE,
                    card_json TEXT,
                    stability REAL,
                    difficulty REAL,
                    retrievability REAL,
                    due TEXT,
                    last_review TEXT,
                    repetitions INTEGER NOT NULL,
                    state INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workload_estimates (
                    topic_id TEXT PRIMARY KEY REFERENCES topics(id) ON DELETE CASCADE,
                    predicted_minutes REAL NOT NULL,
                    lower_bound_minutes REAL NOT NULL,
                    upper_bound_minutes REAL NOT NULL,
                    confidence REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    source TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS question_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id TEXT NOT NULL,
                    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                    knowledge_component_id TEXT,
                    attempted_at TEXT NOT NULL,
                    correct INTEGER NOT NULL,
                    response_time_seconds REAL,
                    confidence REAL
                );
                CREATE INDEX IF NOT EXISTS idx_attempt_topic ON question_attempts(topic_id, attempted_at);
                CREATE TABLE IF NOT EXISTS planner_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    topic_id TEXT,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def save_curriculum_nodes(self, nodes: list[CurriculumNode]) -> None:
        with self.db.connection() as conn:
            for node in nodes:
                conn.execute(
                    """INSERT INTO curriculum_nodes(id,name,node_type,parent_id,source)
                    VALUES (?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET name=excluded.name,node_type=excluded.node_type,
                    parent_id=excluded.parent_id,source=excluded.source""",
                    (node.id, node.name, node.node_type, node.parent_id, node.source),
                )

    def save_curriculum_snapshot(self, snapshot: Any) -> None:
        nodes = [asdict(node) for node in snapshot.nodes]
        issues = [asdict(issue) for issue in snapshot.issues]
        with self.db.connection() as conn:
            conn.execute(
                """INSERT INTO curriculum_snapshots(source,version,fingerprint,nodes_json,issues_json)
                VALUES (?,?,?,?,?)
                ON CONFLICT(source,version) DO UPDATE SET fingerprint=excluded.fingerprint,
                nodes_json=excluded.nodes_json,issues_json=excluded.issues_json""",
                (snapshot.source, snapshot.version, snapshot.fingerprint,
                 json.dumps(nodes, sort_keys=True), json.dumps(issues, sort_keys=True)),
            )

    def list_curriculum_snapshots(self, source: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT source,version,fingerprint,created_at,nodes_json,issues_json FROM curriculum_snapshots"
        args: tuple[Any, ...] = ()
        if source:
            query += " WHERE source=?"
            args = (source,)
        query += " ORDER BY created_at DESC, source, version"
        with self.db.connection() as conn:
            rows = conn.execute(query, args).fetchall()
        return [
            {
                "source": row["source"],
                "version": row["version"],
                "fingerprint": row["fingerprint"],
                "created_at": row["created_at"],
                "node_count": len(json.loads(row["nodes_json"])),
                "issue_count": len(json.loads(row["issues_json"])),
            }
            for row in rows
        ]

    def load_curriculum_nodes(self) -> list[CurriculumNode]:
        with self.db.connection() as conn:
            rows = conn.execute("SELECT * FROM curriculum_nodes ORDER BY source,id").fetchall()
        return [CurriculumNode(r["id"], r["name"], r["node_type"], r["parent_id"], r["source"]) for r in rows]

    def link_topic_to_nodes(self, topic_id: str, node_ids: list[str]) -> None:
        with self.db.connection() as conn:
            conn.execute("DELETE FROM topic_curriculum_links WHERE topic_id=?", (topic_id,))
            for node_id in dict.fromkeys(node_ids):
                if conn.execute("SELECT 1 FROM curriculum_nodes WHERE id=?", (node_id,)).fetchone() is None:
                    raise ValueError(f"unknown curriculum node: {node_id}")
                conn.execute("INSERT INTO topic_curriculum_links(topic_id,node_id) VALUES (?,?)", (topic_id, node_id))

    def curriculum_nodes_for_topic(self, topic_id: str) -> list[CurriculumNode]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """SELECT n.* FROM curriculum_nodes n
                JOIN topic_curriculum_links l ON l.node_id=n.id
                WHERE l.topic_id=? ORDER BY n.source,n.id""",
                (topic_id,),
            ).fetchall()
        return [CurriculumNode(r["id"], r["name"], r["node_type"], r["parent_id"], r["source"]) for r in rows]

    def save_curriculum_mappings(self, mappings: list[CurriculumMapping]) -> None:
        clean = deduplicate_mappings(mappings)
        with self.db.connection() as conn:
            for mapping in clean:
                if conn.execute("SELECT 1 FROM knowledge_components WHERE id=?", (mapping.knowledge_component_id,)).fetchone() is None:
                    raise ValueError(f"unknown knowledge component: {mapping.knowledge_component_id}")
                if conn.execute("SELECT 1 FROM curriculum_nodes WHERE id=?", (mapping.curriculum_node_id,)).fetchone() is None:
                    raise ValueError(f"unknown curriculum node: {mapping.curriculum_node_id}")
                conn.execute(
                    """INSERT INTO knowledge_component_curriculum_links
                    (knowledge_component_id,node_id,source,confidence,relation)
                    VALUES (?,?,?,?,?)
                    ON CONFLICT(knowledge_component_id,node_id,relation) DO UPDATE SET
                    source=excluded.source,confidence=excluded.confidence""",
                    (mapping.knowledge_component_id, mapping.curriculum_node_id, mapping.source,
                     mapping.confidence, mapping.relation),
                )

    def curriculum_mappings_for_kc(self, knowledge_component_id: str) -> list[CurriculumMapping]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """SELECT knowledge_component_id,node_id,source,confidence,relation
                FROM knowledge_component_curriculum_links
                WHERE knowledge_component_id=? ORDER BY source,node_id,relation""",
                (knowledge_component_id,),
            ).fetchall()
        return [CurriculumMapping(r["knowledge_component_id"], r["node_id"], r["source"], r["confidence"], r["relation"]) for r in rows]

    def knowledge_components_for_node(self, node_id: str) -> list[KnowledgeComponent]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """SELECT k.* FROM knowledge_components k
                JOIN knowledge_component_curriculum_links l ON l.knowledge_component_id=k.id
                WHERE l.node_id=? ORDER BY k.topic_id,k.id""",
                (node_id,),
            ).fetchall()
        return [KnowledgeComponent(r["id"], r["topic_id"], r["name"], r["initial_mastery"]) for r in rows]

    def save_knowledge_components(self, components: list[KnowledgeComponent]) -> None:
        with self.db.connection() as conn:
            for kc in components:
                conn.execute(
                    """INSERT INTO knowledge_components(id,topic_id,name,initial_mastery)
                    VALUES (?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET topic_id=excluded.topic_id,name=excluded.name,
                    initial_mastery=excluded.initial_mastery""",
                    (kc.id, kc.topic_id, kc.name, clamp(kc.initial_mastery)),
                )

    def load_knowledge_components(self, topic_id: str | None = None) -> list[KnowledgeComponent]:
        query = "SELECT * FROM knowledge_components"
        args: tuple[Any, ...] = ()
        if topic_id is not None:
            query += " WHERE topic_id=?"
            args = (topic_id,)
        query += " ORDER BY topic_id,id"
        with self.db.connection() as conn:
            rows = conn.execute(query, args).fetchall()
        return [KnowledgeComponent(r["id"], r["topic_id"], r["name"], r["initial_mastery"]) for r in rows]

    def save_knowledge_state(self, state: StudentKnowledgeState) -> None:
        with self.db.connection() as conn:
            conn.execute(
                """INSERT INTO student_knowledge VALUES (?,?,?,?,?)
                ON CONFLICT(knowledge_component_id) DO UPDATE SET mastery_probability=excluded.mastery_probability,
                uncertainty=excluded.uncertainty,observations=excluded.observations,last_observed_at=excluded.last_observed_at""",
                (state.knowledge_component_id, clamp(state.mastery_probability), clamp(state.uncertainty),
                 state.observations, state.last_observed_at.isoformat() if state.last_observed_at else None),
            )

    def get_knowledge_state(self, kc_id: str, initial_mastery: float = 0.5) -> StudentKnowledgeState:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM student_knowledge WHERE knowledge_component_id=?", (kc_id,)).fetchone()
        if row is None:
            return StudentKnowledgeState(kc_id, clamp(initial_mastery))
        observed = datetime.fromisoformat(row["last_observed_at"]) if row["last_observed_at"] else None
        return StudentKnowledgeState(kc_id, row["mastery_probability"], row["uncertainty"], row["observations"], observed)

    def save_fsrs_state(self, state: StudentFSRSState) -> None:
        with self.db.connection() as conn:
            conn.execute(
                """INSERT INTO student_fsrs VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(topic_id) DO UPDATE SET card_json=excluded.card_json,stability=excluded.stability,
                difficulty=excluded.difficulty,retrievability=excluded.retrievability,due=excluded.due,
                last_review=excluded.last_review,repetitions=excluded.repetitions,state=excluded.state""",
                (state.topic_id, state.card_json, state.stability, state.difficulty, state.retrievability,
                 state.due.isoformat() if state.due else None, state.last_review.isoformat() if state.last_review else None,
                 state.repetitions, state.state),
            )

    def get_fsrs_state(self, topic_id: str) -> StudentFSRSState | None:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM student_fsrs WHERE topic_id=?", (topic_id,)).fetchone()
        if row is None:
            return None
        return StudentFSRSState(
            row["topic_id"], row["card_json"], row["stability"], row["difficulty"], row["retrievability"],
            datetime.fromisoformat(row["due"]) if row["due"] else None,
            datetime.fromisoformat(row["last_review"]) if row["last_review"] else None,
            row["repetitions"], row["state"],
        )

    def save_workload(self, estimate: Any) -> None:
        values = asdict(estimate)
        with self.db.connection() as conn:
            conn.execute(
                """INSERT INTO workload_estimates VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(topic_id) DO UPDATE SET predicted_minutes=excluded.predicted_minutes,
                lower_bound_minutes=excluded.lower_bound_minutes,upper_bound_minutes=excluded.upper_bound_minutes,
                confidence=excluded.confidence,sample_count=excluded.sample_count,source=excluded.source""",
                (values["topic_id"], values["predicted_minutes"], values["lower_bound_minutes"],
                 values["upper_bound_minutes"], values["confidence"], values["sample_count"], values["source"]),
            )

    def get_workload(self, topic_id: str) -> dict[str, Any] | None:
        with self.db.connection() as conn:
            row = conn.execute("SELECT * FROM workload_estimates WHERE topic_id=?", (topic_id,)).fetchone()
        return dict(row) if row else None

    def record_question_attempt(
        self,
        question_id: str,
        topic_id: str,
        attempted_at: datetime,
        correct: bool,
        knowledge_component_id: str | None = None,
        response_time_seconds: float | None = None,
        confidence: float | None = None,
    ) -> int:
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValueError("confidence must be in [0, 1]")
        with self.db.connection() as conn:
            cur = conn.execute(
                """INSERT INTO question_attempts(question_id,topic_id,knowledge_component_id,attempted_at,correct,response_time_seconds,confidence)
                VALUES (?,?,?,?,?,?,?)""",
                (question_id, topic_id, knowledge_component_id, attempted_at.isoformat(), int(correct), response_time_seconds, confidence),
            )
            return int(cur.lastrowid)

    def question_history(self, topic_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM question_attempts"
        args: tuple[Any, ...] = ()
        if topic_id:
            query += " WHERE topic_id=?"
            args = (topic_id,)
        query += " ORDER BY attempted_at"
        with self.db.connection() as conn:
            return [dict(r) for r in conn.execute(query, args)]

    def record_event(self, event_type: str, payload: dict[str, Any], topic_id: str | None = None) -> None:
        with self.db.connection() as conn:
            conn.execute(
                "INSERT INTO planner_events(event_type,topic_id,payload_json) VALUES (?,?,?)",
                (event_type, topic_id, json.dumps(payload, default=str, sort_keys=True)),
            )
