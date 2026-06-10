from persona_genesis.generators.narrative.payload import NarrativePayload


def test_payload_round_trips_and_has_no_status_fields() -> None:
    data = {
        "personality": {"ocean": {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5,
                                   "agreeableness": 0.5, "neuroticism": 0.5},
                        "traits": ["curious"], "values": ["honesty"], "quirks": ["hums"]},
        "appearance": {"description": "tall", "hair_color": "brown", "hair_style": "short",
                       "eye_color": "brown", "build": "average", "height_cm": 175,
                       "distinguishing_features": []},
        "backstory": {"bio": "b", "education": [], "key_life_events": []},
        "voice": {"writing_style": "casual", "posting_cadence": "daily",
                  "typical_topics": ["t"], "sample_paragraph": "p"},
    }
    p = NarrativePayload.model_validate(data)
    assert NarrativePayload.model_validate_json(p.model_dump_json()) == p
    assert "description_status" not in p.appearance.model_fields
