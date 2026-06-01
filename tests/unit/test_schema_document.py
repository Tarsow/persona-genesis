from persona_genesis.schema.document import Document


def test_document_defaults() -> None:
    d = Document(content="An event happened.")
    assert d.metadata == {}
    assert d.embedding is None
    assert d.status == "real"
    assert Document.model_validate_json(d.model_dump_json()) == d
