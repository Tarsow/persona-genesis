from sqlalchemy.ext.asyncio import AsyncEngine

from persona_genesis.config import Config
from persona_genesis.db.engine import build_persistence


def test_build_persistence_from_config() -> None:
    cfg = Config.from_dict(
        {"database_url": "postgresql+psycopg://u:p@localhost:5432/db",
         "face_embedding_dim": 16}
    )
    p = build_persistence(cfg)
    assert isinstance(p.engine, AsyncEngine)
    assert p.registry.FaceRow.__table__.columns["embedding"] is not None
    assert p.session_factory is not None
