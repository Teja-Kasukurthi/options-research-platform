"""Event-driven backtest engine — reads TimescaleDB chain snapshots."""

from datetime import date, datetime, timedelta

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtester.broker import simulate_fill
from app.backtester.clock import SimulatedClock, set_clock
from app.backtester.metrics import compute_all_metrics
from app.backtester.strategies.base import BaseStrategy, Order
from app.backtester.strategies.long_straddle import LongStraddleStrategy

logger = structlog.get_logger(__name__)

STRATEGY_MAP: dict[str, type[BaseStrategy]] = {
    "long_straddle": LongStraddleStrategy,
}


class BacktestEngine:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def run(
        self,
        strategy_name: str,
        parameters: dict,
        from_date: date,
        to_date: date,
        initial_capital: float | None = None,
    ) -> dict:
        from models.options_chain import OptionsChainSnapshot

        initial_capital = initial_capital or parameters.get("initial_capital", 500_000.0)
        strategy_cls = STRATEGY_MAP.get(strategy_name)
        if not strategy_cls:
            raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(STRATEGY_MAP)}")

        strategy = strategy_cls(parameters, initial_capital)
        equity_curve: list[float] = [initial_capital]

        # Fetch chain snapshots in time order
        snapshots_q = await self._db.execute(
            select(OptionsChainSnapshot)
            .where(
                OptionsChainSnapshot.snapshot_time >= datetime.combine(from_date, datetime.min.time()),
                OptionsChainSnapshot.snapshot_time <= datetime.combine(to_date, datetime.max.time()),
            )
            .order_by(OptionsChainSnapshot.snapshot_time)
        )
        snapshots = snapshots_q.scalars().all()

        if not snapshots:
            logger.warning("no_chain_snapshots", from_date=from_date, to_date=to_date)
            return {"error": "no data"}

        clock = SimulatedClock(snapshots[0].snapshot_time)
        set_clock(clock)

        for snapshot in snapshots:
            clock.advance(snapshot.snapshot_time)
            chain = snapshot.chain_data
            chain["underlying"] = snapshot.underlying
            chain["expiry"] = snapshot.expiry.isoformat()

            orders = strategy.on_chain(chain, snapshot.snapshot_time)

            for order in orders:
                strike_data = self._find_strike(chain, order)
                if not strike_data:
                    continue

                opt_type = "ce" if "CE" in order.symbol else "pe"
                opt = strike_data.get(opt_type, {}) or {}
                bid = opt.get("bid", opt.get("ltp", 0))
                ask = opt.get("ask", opt.get("ltp", 0))
                oi = opt.get("oi", 0) or 0

                fill = simulate_fill(
                    instrument_id=order.instrument_id,
                    symbol=order.symbol,
                    action=order.action,
                    quantity=order.quantity,
                    lot_size=parameters.get("lot_size", 50),
                    bid=bid or 0,
                    ask=ask or 0,
                    oi=oi,
                    fill_time=snapshot.snapshot_time,
                )
                strategy.on_fill(order, fill.fill_price, fill.commission)

            # Check stop-losses and targets for open positions
            self._check_exits(strategy, chain, snapshot.snapshot_time)
            equity_curve.append(strategy.capital)

        # Close all remaining positions at last snapshot price
        if snapshots:
            last_chain = snapshots[-1].chain_data
            last_chain["underlying"] = snapshots[-1].underlying
            for pos in list(strategy.open_positions):
                strike_data = self._find_strike_by_symbol(last_chain, pos["symbol"])
                if strike_data:
                    opt_type = "ce" if "CE" in pos["symbol"] else "pe"
                    ltp = (strike_data.get(opt_type) or {}).get("ltp", 0)
                    strategy.close_position(pos, ltp or 0, snapshots[-1].snapshot_time, "backtest_end")

        metrics = compute_all_metrics(strategy.trades, equity_curve, initial_capital)
        metrics["trades"] = strategy.trades
        metrics["equity_curve"] = equity_curve

        logger.info("backtest_run_complete", strategy=strategy_name, **{k: v for k, v in metrics.items() if k not in ("trades", "equity_curve")})
        return metrics

    def _find_strike(self, chain: dict, order: Order) -> dict | None:
        strikes = chain.get("strikes", [])
        for s in strikes:
            if s.get("strike") and order.symbol.replace("CE", "").replace("PE", "").endswith(str(int(s["strike"]))):
                return s
        return None

    def _find_strike_by_symbol(self, chain: dict, symbol: str) -> dict | None:
        return self._find_strike(chain, type("O", (), {"symbol": symbol})())  # type: ignore[arg-type]

    def _check_exits(self, strategy: BaseStrategy, chain: dict, ts: datetime) -> None:
        for pos in list(strategy.open_positions):
            strike_data = self._find_strike_by_symbol(chain, pos["symbol"])
            if not strike_data:
                continue
            opt_type = "ce" if "CE" in pos["symbol"] else "pe"
            ltp = (strike_data.get(opt_type) or {}).get("ltp", 0) or 0

            if pos.get("stop_loss") and ltp <= pos["stop_loss"] and pos["action"] == "BUY":
                strategy.close_position(pos, ltp, ts, "stop_loss")
            elif pos.get("target") and ltp >= pos["target"] and pos["action"] == "BUY":
                strategy.close_position(pos, ltp, ts, "target")
