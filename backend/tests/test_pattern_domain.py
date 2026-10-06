import app.patterns.domain as pattern_domain


ORG_ID = "00000000-0000-0000-0000-000000000001"
SUBJECT_ID = "00000000-0000-0000-0000-000000000101"
EVIDENCE_ID = "90000000-0000-0000-0000-000000000001"
INTERPRETATION_ID = "90000000-0000-0000-0000-000000000002"
MEMBER_ID = "90000000-0000-0000-0000-000000000003"


def _evidence_set() -> dict:
    return {
        "organization_context_id": ORG_ID,
        "subject_person_id": SUBJECT_ID,
        "members": [
            {
                "evidence_case_id": EVIDENCE_ID,
                "interpretation_id": INTERPRETATION_ID,
                "interpretation_version": 1,
                "behaviour_code": "METRIC_REASONING",
                "signal": "POSITIVE",
                "scope": "RECOVERY_EXPERIMENT",
                "confidence": "HIGH",
                "context_difficulty": "HIGH",
                "prompt_contamination": "NONE",
                "source_independence_group": "MISSION_INSTANCE:mission-1",
                "accepted_at": "2026-10-06T07:00:00Z",
                "target_links": [
                    {
                        "target_type": "CAPABILITY",
                        "target_ref": "METRICS_EXPERIMENTATION",
                        "signal": "POSITIVE",
                        "scope": "RECOVERY_EXPERIMENT",
                        "relevance": "HIGH",
                        "confidence": "HIGH",
                    }
                ],
                "source_lineage": {
                    "source_observation_id": "observation-1",
                    "source_context": "MISSION_RUNTIME",
                    "source_reference": "MISSION_INSTANCE:mission-1",
                    "observation_type": "EXPERIMENT_RESULT_OBSERVED",
                },
            }
        ],
    }


def _pattern_candidate() -> dict:
    return {
        "behaviour_code": "METRIC_REASONING",
        "behaviour_description": "Uses experiment measurements to reason about outcomes.",
        "proposed_pattern_status": "EMERGING",
        "scope": "RECOVERY_EXPERIMENT",
        "rationale": "Accepted evidence supports a reviewable emerging pattern.",
        "evidence": [
            {
                "evidence_set_member_id": MEMBER_ID,
                "relationship": "SUPPORTING",
            }
        ],
    }


def test_pattern_status_vocabulary_matches_final_decision() -> None:
    assert {item.value for item in pattern_domain.PatternStatus} == {
        "EMERGING",
        "REPEATED",
        "STABLE",
        "CONTRADICTED",
        "REGRESSED",
        "RECOVERING",
    }
    assert {item.value for item in pattern_domain.PatternEvidenceRelationship} == {
        "SUPPORTING",
        "CONTRADICTORY",
    }


def test_evidence_set_contract_preserves_reviewed_evidence_lineage() -> None:
    assert pattern_domain.evidence_set_contract_valid(_evidence_set())

    duplicate = _evidence_set()
    duplicate["members"].append(dict(duplicate["members"][0]))
    assert not pattern_domain.evidence_set_contract_valid(duplicate)

    missing_lineage = _evidence_set()
    del missing_lineage["members"][0]["source_lineage"]["source_reference"]
    assert not pattern_domain.evidence_set_contract_valid(missing_lineage)


def test_pattern_candidate_requires_allowed_status_and_supporting_evidence() -> None:
    assert pattern_domain.pattern_candidate_contract_valid(_pattern_candidate())

    unknown_status = _pattern_candidate()
    unknown_status["proposed_pattern_status"] = "PROVEN"
    assert not pattern_domain.pattern_candidate_contract_valid(unknown_status)

    contradictory_only = _pattern_candidate()
    contradictory_only["evidence"][0]["relationship"] = "CONTRADICTORY"
    assert not pattern_domain.pattern_candidate_contract_valid(contradictory_only)


def test_pattern_candidate_rejects_duplicate_evidence_members() -> None:
    candidate = _pattern_candidate()
    candidate["evidence"].append(dict(candidate["evidence"][0]))
    assert not pattern_domain.pattern_candidate_contract_valid(candidate)
