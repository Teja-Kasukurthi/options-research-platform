"""Agent memory — short-term (Redis) + long-term (pgvector RAG) + episodic (PostgreSQL)."""

import json
from datetime import datetime

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from models.market_research import MarketResearch

logger = structlog.get_logger(__name__)

EMBEDDING_DIM = 1536  # text-embedding-ada-002 / compatible


async def store_short_term(run_id: str, key: str, value: dict, ttl: int = 7200) -> None:
    redis = await get_redis()
    full_key = f"agent:context:{run_id}:{key}"
    await redis.setex(full_key, ttl, json.dumps(value))


async def get_short_term(run_id: str, key: str) -> dict | None:
    redis = await get_redis()
    data = await redis.get(f"agent:context:{run_id}:{key}")
    return json.loads(data) if data else None


async def store_research(
    db: AsyncSession,
    source_type: str,
    summary: str,
    underlying: str | None,
    sentiment: str | None,
    structured_analysis: dict | None,
    agent_run_id: str | None,
    embedding: list[float] | None = None,
) -> MarketResearch:
    row = MarketResearch(
        source_type=source_type,
        underlying=underlying,
        summary=summary,
        structured_analysis=structured_analysis,
        sentiment=sentiment,
        agent_run_id=agent_run_id,
    )
    db.add(row)
    await db.flush()

    if embedding:
        await db.execute(
            text("UPDATE market_research SET embedding = :emb WHERE id = :id"),
            {"emb": str(embedding), "id": str(row.id)},
        )

    await db.commit()
    return row


async def retrieve_similar(
    db: AsyncSession,
    query_embedding: list[float],
    underlying: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """pgvector cosine similarity search."""
    try:
        where_clause = "WHERE embedding IS NOT NULL"
        params: dict = {"emb": str(query_embedding), "k": top_k}
        if underlying:
            where_clause += " AND underlying = :underlying"
            params["underlying"] = underlying

        result = await db.execute(
            text(f"""
                SELECT id, created_at, source_type, underlying, summary, sentiment,
                       1 - (embedding <=> :emb::vector) AS similarity
                FROM market_research
                {where_clause}
                ORDER BY similarity DESC
                LIMIT :k
            """),
            params,
        )
        return [dict(row._mapping) for row in result]
    except Exception:
        logger.exception("pgvector_search_error")
        return []
