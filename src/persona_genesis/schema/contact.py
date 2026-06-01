"""Contact sub-model. Real-only: populated only from caller-supplied, owned data."""

from pydantic import BaseModel

from persona_genesis.schema.status import Status


class Contact(BaseModel):
    phone: str | None = None  # real-only
    phone_status: Status = "fake"
    email: str | None = None  # real-only
    email_status: Status = "fake"
