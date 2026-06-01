import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from PIL import Image as PILImage
from sqlalchemy import text

from persona_genesis.builder import PersonaBuilder
from persona_genesis.config import Config
from persona_genesis.db.engine import Persistence, build_persistence, create_all, drop_all
from persona_genesis.db.repository import AsyncPersonaRepository, PersonaRepository
from persona_genesis.schema.account import Account
from persona_genesis.schema.biometrics import Face
from persona_genesis.schema.document import Document
from persona_genesis.schema.partial import PartialPersona
from persona_genesis.schema.persona import Persona
from persona_genesis.schema.relationship import Relationship

DIM = 8


def _cfg(database_url: str) -> Config:
    return Config.from_dict(
        {
            "database_url": database_url,
            "face_embedding_dim": DIM,
            "body_embedding_dim": DIM,
            "voice_embedding_dim": DIM,
            "document_embedding_dim": DIM,
        }
    )


def _partial() -> PartialPersona:
    return PartialPersona(id=uuid.uuid4(), seed=7, locale="pt_BR")


def _repo(p: Persistence, vault_key: bytes) -> AsyncPersonaRepository:
    return AsyncPersonaRepository(p.session_factory, p.registry, vault_key=vault_key)


@pytest_asyncio.fixture
async def persistence(database_url: str) -> AsyncIterator[Persistence]:
    p = build_persistence(_cfg(database_url))
    await drop_all(p)
    await create_all(p)
    yield p
    await drop_all(p)
    await p.engine.dispose()


async def test_save_and_get_partial(persistence: Persistence, vault_key: bytes) -> None:
    repo = _repo(persistence, vault_key)
    partial = _partial()
    await repo.save(partial)
    loaded = await repo.get_partial(partial.id)
    assert loaded is not None
    assert loaded.locale == "pt_BR"
    assert loaded.seed == 7


async def test_complete_persona_round_trips(
    persistence: Persistence, vault_key: bytes, sample_persona: Persona
) -> None:
    repo = _repo(persistence, vault_key)
    await repo.save(sample_persona)
    loaded = await repo.get(sample_persona.id)
    assert loaded == sample_persona


async def test_face_store_and_search(persistence: Persistence, vault_key: bytes) -> None:
    repo = _repo(persistence, vault_key)
    partial = _partial()
    await repo.save(partial)
    near = Face(persona_id=partial.id, embedding=[1.0] + [0.0] * (DIM - 1))
    far = Face(persona_id=partial.id, embedding=[0.0] * (DIM - 1) + [1.0])
    await repo.add_face(near)
    await repo.add_face(far)
    got = await repo.get_faces(partial.id)
    assert {f.id for f in got} == {near.id, far.id}
    ranked = await repo.search_faces([1.0] + [0.0] * (DIM - 1), k=1)
    assert ranked[0].id == near.id


async def test_document_rag_is_persona_scoped(persistence: Persistence, vault_key: bytes) -> None:
    repo = _repo(persistence, vault_key)
    a, b = _partial(), _partial()
    await repo.save(a)
    await repo.save(b)
    doc_a = Document(content="A's event", embedding=[1.0] + [0.0] * (DIM - 1))
    doc_b = Document(content="B's event", embedding=[0.0] * (DIM - 1) + [1.0])
    await repo.add_document(doc_a, persona_ids=(a.id,))
    await repo.add_document(doc_b, persona_ids=(b.id,))
    a_docs = await repo.get_documents(a.id)
    assert {d.id for d in a_docs} == {doc_a.id}
    hits = await repo.search_documents([0.0] * (DIM - 1) + [1.0], k=5, persona_id=a.id)
    assert {d.id for d in hits} == {doc_a.id}


async def test_account_ciphertext_at_rest(persistence: Persistence, vault_key: bytes) -> None:
    repo = _repo(persistence, vault_key)
    partial = _partial()
    await repo.save(partial)
    await repo.add_account(
        Account(persona_id=partial.id, url="https://m", login="u", password="s3cret")
    )
    got = await repo.get_accounts(partial.id)
    assert got[0].password == "s3cret"
    async with persistence.session_factory() as session:
        raw = (await session.execute(text("select password_enc from accounts"))).all()
    assert raw[0][0] != "s3cret"


async def test_relationship_surfaces_for_both(persistence: Persistence, vault_key: bytes) -> None:
    repo = _repo(persistence, vault_key)
    a, b = _partial(), _partial()
    await repo.save(a)
    await repo.save(b)
    rel = Relationship(person_1_id=a.id, person_2_id=b.id, relationship="friend")
    await repo.add_relationship(rel)
    assert {r.id for r in await repo.get_relationships(a.id)} == {rel.id}
    assert {r.id for r in await repo.get_relationships(b.id)} == {rel.id}


async def test_save_draft_persists_entities_and_links(
    persistence: Persistence, vault_key: bytes, tmp_path: Path
) -> None:
    repo = _repo(persistence, vault_key)
    b = PersonaBuilder(locale="pt_BR", media_dir=tmp_path)
    face = b.add_face(embedding=[1.0] + [0.0] * (DIM - 1))
    img = b.add_image(PILImage.new("RGB", (8, 8), "white"), type="face", link_faces=[face])
    b.add_account(url="https://m", login="u", password="pw")
    b.add_document(content="ev", embedding=[0.0] * DIM)
    draft = b.build()
    await repo.save_draft(draft)
    pid = draft.persona.id
    assert {f.id for f in await repo.get_faces(pid)} == {face.id}
    assert {i.id for i in await repo.get_images_for_persona(pid)} == {img.id}
    assert {a.url for a in await repo.get_accounts(pid)} == {"https://m"}
    assert {d.content for d in await repo.get_documents(pid)} == {"ev"}


def test_sync_facade(database_url: str, vault_key: bytes) -> None:
    import anyio

    p = build_persistence(_cfg(database_url))
    anyio.run(drop_all, p)
    anyio.run(create_all, p)
    partial = _partial()
    with PersonaRepository(p.session_factory, p.registry, vault_key=vault_key) as repo:
        repo.save(partial)
        loaded = repo.get_partial(partial.id)
        assert loaded is not None
        assert loaded.locale == "pt_BR"
    anyio.run(drop_all, p)
    anyio.run(p.engine.dispose)
