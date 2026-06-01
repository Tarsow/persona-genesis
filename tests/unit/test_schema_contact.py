from persona_genesis.schema.contact import Contact


def test_contact_defaults_to_empty_with_fake_status() -> None:
    c = Contact()
    assert c.phone is None
    assert c.email is None
    assert c.phone_status == "fake"
    assert c.email_status == "fake"


def test_contact_round_trips() -> None:
    c = Contact(
        phone="+55 19 90000-0000", email="me@x.com",
        phone_status="real", email_status="real",
    )
    restored = Contact.model_validate_json(c.model_dump_json())
    assert restored == c


def test_contact_has_no_email_handle() -> None:
    assert "email_handle" not in Contact.model_fields
