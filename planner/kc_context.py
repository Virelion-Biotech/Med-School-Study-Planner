from __future__ import annotations

from dataclasses import dataclass

from .adaptive_db import AdaptiveDB
from .evidence import EvidenceSummary, summarize_question_evidence
from .kc_state import KCSignal, aggregate_topic_kc_signals, merge_topic_evidence
from .models import Topic


@dataclass(frozen=True)
class KCContext:
    knowledge_component_id: str
    signal: KCSignal
    evidence: EvidenceSummary
    mapped_topic_ids: tuple[str, ...]
    mapped_sources: tuple[str, ...]


def build_kc_context(adaptive_db: AdaptiveDB, kc_id: str, now) -> KCContext:
    kc = adaptive_db.load_knowledge_components_for_id(kc_id)
    if kc is None:
        raise KeyError(kc_id)
    mapped_topics = [kc.topic_id]
    mappings = adaptive_db.curriculum_mappings_for_kc(kc_id)
    topics = tuple(sorted(set(mapped_topics)))
    sources = tuple(sorted({m.source for m in mappings}))
    state = adaptive_db.get_knowledge_state(kc_id, kc.initial_mastery)
    evidence_values = []
    for topic_id in topics:
        summary = summarize_question_evidence(adaptive_db, topic_id, now)
        evidence_values.append((summary.attempts, summary.recent_accuracy, max(0.0, summary.confidence - summary.recent_accuracy)))
    attempts, accuracy, gap = merge_topic_evidence(evidence_values)
    evidence = EvidenceSummary(attempts=attempts, recent_accuracy=accuracy, accuracy=accuracy, confidence=min(1.0, accuracy + gap), error_rate=1.0 - accuracy, evidence_strength=1.0 if attempts else 0.0)
    signal = aggregate_topic_kc_signals([state], topics, sources)
    return KCContext(kc_id, signal, evidence, topics, sources)


def topic_kc_ids(topic: Topic) -> tuple[str, ...]:
    return tuple(dict.fromkeys(topic.knowledge_component_ids))
