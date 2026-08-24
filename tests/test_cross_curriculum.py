from planner.cross_curriculum import CurriculumMapping, deduplicate_mappings


def test_mapping_deduplication_preserves_distinct_relations():
    mappings = [
        CurriculumMapping("kc-heart-failure", "school-cardiology", "school", 0.95),
        CurriculumMapping("kc-heart-failure", "school-cardiology", "school", 0.95),
        CurriculumMapping("kc-heart-failure", "usmle-cardiovascular", "usmle", 0.90),
        CurriculumMapping("kc-heart-failure", "usmle-cardiovascular", "usmle", 0.90, relation="prerequisite"),
    ]
    result = deduplicate_mappings(mappings)
    assert len(result) == 3
    assert {m.source for m in result} == {"school", "usmle"}
    assert any(m.relation == "prerequisite" for m in result)


def test_mapping_confidence_is_bounded():
    result = deduplicate_mappings([CurriculumMapping("kc", "node", "personal", 2.0)])
    assert result[0].confidence == 1.0
