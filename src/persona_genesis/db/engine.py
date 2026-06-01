"""Build async engine/session factory + ORM registry from Config, and create the
schema (pgvector extension + tables). psycopg 3 serves the async engine via the
postgresql+psycopg dialect. No env reading — values come from Config."""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from persona_genesis.config import Config
from persona_genesis.db.models import EmbeddingDims, ModelRegistry, build_models
from persona_genesis.exceptions import ConfigError


@dataclass
class Persistence:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]
    registry: ModelRegistry


def build_persistence(config: Config) -> Persistence:
    if not config.database_url:
        raise ConfigError("database_url is required to build the persistence layer")
    dims = EmbeddingDims(
        face=config.face_embedding_dim,
        body=config.body_embedding_dim,
        voice=config.voice_embedding_dim,
        document=config.document_embedding_dim,
    )
    registry = build_models(dims)
    engine = create_async_engine(config.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return Persistence(engine=engine, session_factory=session_factory, registry=registry)


async def create_all(persistence: Persistence) -> None:
    async with persistence.engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(persistence.registry.base.metadata.create_all)


async def drop_all(persistence: Persistence) -> None:
    async with persistence.engine.begin() as conn:
        await conn.run_sync(persistence.registry.base.metadata.drop_all)
