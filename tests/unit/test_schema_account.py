from uuid import uuid4

from persona_genesis.schema.account import Account


def test_account_round_trip_plaintext_in_memory() -> None:
    a = Account(persona_id=uuid4(), url="https://x", login="u", password="p")
    assert a.password == "p"
    assert a.session_token is None
    assert Account.model_validate_json(a.model_dump_json()) == a
