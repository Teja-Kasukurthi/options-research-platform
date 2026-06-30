"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # instruments
    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("exchange", sa.String(10), nullable=False),
        sa.Column("instrument_type", sa.String(10), nullable=False),
        sa.Column("underlying", sa.String(50), nullable=True),
        sa.Column("expiry", sa.Date, nullable=True),
        sa.Column("strike", sa.Float, nullable=True),
        sa.Column("option_type", sa.String(2), nullable=True),
        sa.Column("lot_size", sa.Integer, nullable=False, server_default="1"),
        sa.Column("kite_instrument_token", sa.Integer, nullable=True, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_instruments_symbol", "instruments", ["symbol"])
    op.create_index("ix_instruments_underlying", "instruments", ["underlying"])
    op.create_index("ix_instruments_expiry", "instruments", ["expiry"])

    # ohlcv_1min (TimescaleDB hypertable)
    op.create_table(
        "ohlcv_1min",
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Float, nullable=False),
        sa.Column("high", sa.Float, nullable=False),
        sa.Column("low", sa.Float, nullable=False),
        sa.Column("close", sa.Float, nullable=False),
        sa.Column("volume", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("oi", sa.BigInteger, nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("instrument_id", "time"),
    )
    op.create_index("ix_ohlcv_instrument_time", "ohlcv_1min", ["instrument_id", "time"])
    op.execute(
        "SELECT create_hypertable('ohlcv_1min', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('ohlcv_1min', INTERVAL '5 years', if_not_exists => TRUE)"
    )

    # options_chain_snapshot (TimescaleDB hypertable)
    op.create_table(
        "options_chain_snapshot",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("underlying", sa.String(50), nullable=False),
        sa.Column("expiry", sa.Date, nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("chain_data", postgresql.JSONB, nullable=False),
        sa.PrimaryKeyConstraint("id", "snapshot_time"),
    )
    op.create_index("ix_chain_snapshot_underlying", "options_chain_snapshot", ["underlying"])
    op.create_index("ix_chain_snapshot_expiry", "options_chain_snapshot", ["expiry"])
    op.execute(
        "SELECT create_hypertable('options_chain_snapshot', 'snapshot_time', chunk_time_interval => INTERVAL '4 hours', if_not_exists => TRUE)"
    )
    op.execute(
        "SELECT add_retention_policy('options_chain_snapshot', INTERVAL '2 years', if_not_exists => TRUE)"
    )

    # agent_runs
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("agent_name", sa.String(50), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_context", postgresql.JSONB, nullable=True),
        sa.Column("output", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("tokens_in", sa.Integer, nullable=True),
        sa.Column("tokens_out", sa.Integer, nullable=True),
        sa.Column("cost_usd", sa.Float, nullable=True),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_agent_runs_agent_name", "agent_runs", ["agent_name"])

    # signals
    op.create_table(
        "signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id"), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("strategy_type", sa.String(50), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("parameters", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
    )
    op.create_index("ix_signals_instrument_id", "signals", ["instrument_id"])
    op.create_index("ix_signals_status", "signals", ["status"])
    op.create_index("ix_signals_generated_at", "signals", ["generated_at"])

    # paper_trades
    op.create_table(
        "paper_trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("signals.id"), nullable=True),
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("action", sa.String(4), nullable=False),
        sa.Column("entry_price", sa.Float, nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("exit_price", sa.Float, nullable=True),
        sa.Column("exited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("realized_pnl", sa.Float, nullable=True),
        sa.Column("unrealized_pnl", sa.Float, nullable=True),
        sa.Column("exit_reason", sa.String(50), nullable=True),
        sa.Column("stop_loss", sa.Float, nullable=True),
        sa.Column("target", sa.Float, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_paper_trades_instrument_id", "paper_trades", ["instrument_id"])

    # positions
    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("paper_trade_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("paper_trades.id"), nullable=False, unique=True),
        sa.Column("current_price", sa.Float, nullable=True),
        sa.Column("delta", sa.Float, nullable=True),
        sa.Column("gamma", sa.Float, nullable=True),
        sa.Column("theta", sa.Float, nullable=True),
        sa.Column("vega", sa.Float, nullable=True),
        sa.Column("iv", sa.Float, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # backtest_runs
    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("strategy_name", sa.String(100), nullable=False),
        sa.Column("parameters", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("from_date", sa.Date, nullable=False),
        sa.Column("to_date", sa.Date, nullable=False),
        sa.Column("total_return", sa.Float, nullable=True),
        sa.Column("sharpe_ratio", sa.Float, nullable=True),
        sa.Column("sortino_ratio", sa.Float, nullable=True),
        sa.Column("max_drawdown", sa.Float, nullable=True),
        sa.Column("win_rate", sa.Float, nullable=True),
        sa.Column("total_trades", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("ran_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("full_metrics", postgresql.JSONB, nullable=True),
        sa.Column("equity_curve", postgresql.JSONB, nullable=True),
        sa.Column("trade_log", postgresql.JSONB, nullable=True),
    )
    op.create_index("ix_backtest_runs_strategy_name", "backtest_runs", ["strategy_name"])

    # market_research (with pgvector embedding)
    op.create_table(
        "market_research",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("underlying", sa.String(50), nullable=True),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("structured_analysis", postgresql.JSONB, nullable=True),
        sa.Column("embedding", sa.String, nullable=True),  # placeholder; real type added below
        sa.Column("sentiment", sa.String(20), nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Replace placeholder column with real vector type
    op.execute("ALTER TABLE market_research DROP COLUMN embedding")
    op.execute("ALTER TABLE market_research ADD COLUMN embedding vector(1536)")
    op.execute(
        "CREATE INDEX ix_market_research_embedding ON market_research USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.create_index("ix_market_research_created_at", "market_research", ["created_at"])
    op.create_index("ix_market_research_underlying", "market_research", ["underlying"])

    # TimescaleDB chunk compression (run after hypertables created)
    op.execute(
        "ALTER TABLE ohlcv_1min SET (timescaledb.compress, timescaledb.compress_segmentby = 'instrument_id')"
    )
    op.execute(
        "SELECT add_compression_policy('ohlcv_1min', INTERVAL '7 days', if_not_exists => TRUE)"
    )
    op.execute(
        "ALTER TABLE options_chain_snapshot SET (timescaledb.compress, timescaledb.compress_segmentby = 'underlying')"
    )
    op.execute(
        "SELECT add_compression_policy('options_chain_snapshot', INTERVAL '7 days', if_not_exists => TRUE)"
    )


def downgrade() -> None:
    op.drop_table("market_research")
    op.drop_table("backtest_runs")
    op.drop_table("positions")
    op.drop_table("paper_trades")
    op.drop_table("signals")
    op.drop_table("agent_runs")
    op.drop_table("options_chain_snapshot")
    op.drop_table("ohlcv_1min")
    op.drop_table("instruments")
