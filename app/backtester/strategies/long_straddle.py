"""Long Straddle strategy — buy ATM CE + PE before expiry week."""

from datetime import datetime

from app.backtester.strategies.base import BaseStrategy, Order


class LongStraddleStrategy(BaseStrategy):
    """
    Buy ATM CE and ATM PE when:
    - Days to expiry: 15-25
    - PCR in 0.7-1.3 range (market uncertainty)
    - No existing position on same underlying
    """

    def on_chain(self, chain: dict, timestamp: datetime) -> list[Order]:
        from datetime import date
        underlying = chain.get("underlying", "")
        expiry_str = chain.get("expiry", "")
        spot = chain.get("spot_price", 0)
        pcr = chain.get("pcr")
        strikes = chain.get("strikes", [])

        if not expiry_str or not spot:
            return []

        try:
            expiry = date.fromisoformat(expiry_str)
        except ValueError:
            return []

        days_to_expiry = (expiry - date.today()).days
        entry_window = self.parameters.get("entry_days_range", [15, 25])
        if not (entry_window[0] <= days_to_expiry <= entry_window[1]):
            return []

        if pcr and not (0.7 <= pcr <= 1.3):
            return []

        # Check no existing position
        if any(p.get("symbol", "").startswith(underlying) for p in self.open_positions):
            return []

        # Find ATM strike
        atm_strike_val = min((s["strike"] for s in strikes), key=lambda x: abs(x - spot))
        atm = next((s for s in strikes if s["strike"] == atm_strike_val), None)
        if not atm:
            return []

        lot_size = self.parameters.get("lot_size", 50)
        lots = self.parameters.get("lots", 1)
        orders = []

        if atm.get("ce") and atm["ce"].get("ltp", 0) > 0:
            orders.append(Order(
                instrument_id=f"{underlying}_CE_{atm_strike_val}_{expiry_str}",
                symbol=f"{underlying}{atm_strike_val}CE",
                action="BUY",
                quantity=lots * lot_size,
                order_time=timestamp,
                stop_loss=atm["ce"]["ltp"] * 0.5,
                target=atm["ce"]["ltp"] * 2.5,
            ))

        if atm.get("pe") and atm["pe"].get("ltp", 0) > 0:
            orders.append(Order(
                instrument_id=f"{underlying}_PE_{atm_strike_val}_{expiry_str}",
                symbol=f"{underlying}{atm_strike_val}PE",
                action="BUY",
                quantity=lots * lot_size,
                order_time=timestamp,
                stop_loss=atm["pe"]["ltp"] * 0.5,
                target=atm["pe"]["ltp"] * 2.5,
            ))

        return orders
