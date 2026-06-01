from persona_genesis.schema.voice import Voice


def test_voice_round_trips() -> None:
    voice = Voice(
        writing_style="casual, lots of emoji, short sentences",
        posting_cadence="2-3 times per day",
        typical_topics=["football", "coding", "cooking"],
        sample_paragraph="Just shipped a new feature, feeling good about it!",
    )
    restored = Voice.model_validate_json(voice.model_dump_json())
    assert restored == voice
