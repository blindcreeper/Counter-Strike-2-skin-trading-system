import time


class ExecutionEngine:
    """Simulated trading engine with position management and 7-day holding period."""

    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.fee_rate = float(config.get("PLATFORM_FEE_RATE", config.get("FEE_RATE", 0.025)))
        self.take_profit_rate = float(config.get("TAKE_PROFIT_RATE", 0.08))
        self.stop_loss_rate = float(config.get("STOP_LOSS_RATE", -0.05))
        self.max_holding_hours = int(config.get("HOLDING_PERIOD_HOURS", 168))

    def on_signal(self, name, action, signal_payload):
        signal_id = self.db.record_signal_event(signal_payload)
        if action != "BUY":
            return signal_id, None

        position = self.db.get_open_position(name)
        if position:
            return signal_id, position

        entry_price = float(signal_payload.get("buy_price") or 0)
        now_ts = int(signal_payload.get("signal_time") or time.time())
        self.db.upsert_position({
            "hash_name": name,
            "status": "OPEN",
            "quantity": 1,
            "entry_time": now_ts,
            "entry_price": entry_price,
            "last_price": entry_price,
            "last_mark_time": now_ts,
            "take_profit_rate": self.take_profit_rate,
            "stop_loss_rate": self.stop_loss_rate,
            "max_holding_hours": self.max_holding_hours,
            "signal_id": signal_id,
            "notes": "opened_by_trend_buy",
        })
        position = self.db.get_open_position(name)
        self.db.record_execution({
            "position_id": position.get("position_id") if position else None,
            "signal_id": signal_id,
            "hash_name": name,
            "side": "BUY",
            "exec_time": now_ts,
            "price": entry_price,
            "quantity": 1,
            "gross_amount": entry_price,
            "fee_amount": entry_price * self.fee_rate,
            "net_amount": entry_price * (1 + self.fee_rate),
            "realized_return": None,
            "reason": "trend_buy_signal",
        })
        return signal_id, position

    def mark_position(self, name, current_price, note="mark"):
        position = self.db.get_open_position(name)
        if not position:
            return None
        self.db.upsert_position({
            **position,
            "last_price": current_price,
            "last_mark_time": int(time.time()),
            "notes": note,
        })
        return self.db.get_open_position(name)

    def maybe_close_position(self, name, current_price, now_ts=None):
        """Check take-profit/stop-loss/timeout. Records signal but does not
        actually close during the 7-day lock period — that is handled by
        check_all_positions which runs at end of each scan round."""
        position = self.db.get_open_position(name)
        if not position:
            return None

        now_ts = int(now_ts or time.time())
        entry_price = float(position["entry_price"])
        holding_hours = (now_ts - int(position["entry_time"])) / 3600
        gross_return = (float(current_price) - entry_price) / entry_price if entry_price > 0 else 0
        net_return = gross_return - (2 * self.fee_rate)

        max_hours = int(position.get("max_holding_hours") or self.max_holding_hours)
        if holding_hours >= max_hours:
            return self._close_position(position, current_price, now_ts, "timeout_sell")

        if net_return >= float(position.get("take_profit_rate") or self.take_profit_rate):
            return self._close_position(position, current_price, now_ts, "take_profit")

        if net_return <= float(position.get("stop_loss_rate") or self.stop_loss_rate):
            return self._close_position(position, current_price, now_ts, "stop_loss")

        self.mark_position(name, current_price, note="holding")
        return None

    def check_all_positions(self, current_prices_map):
        """Check all open positions, mark prices, and close expired ones.
        Called at the end of each scan round.
        Returns list of closed position results for notification.
        """
        closed = []
        positions = self.db.get_all_open_positions()
        now_ts = int(time.time())

        for pos in positions:
            name = pos["hash_name"]
            # Try to find current price from scan data
            platforms = current_prices_map.get(name)
            if isinstance(platforms, dict):
                # Pick the higher sell price (best exit)
                prices = [v for v in platforms.values() if v and float(v) > 0]
                current_price = max(float(p) for p in prices) if prices else float(pos["last_price"])
            else:
                current_price = float(pos["last_price"])

            entry_price = float(pos["entry_price"])
            holding_hours = (now_ts - int(pos["entry_time"])) / 3600
            gross_return = (current_price - entry_price) / entry_price if entry_price > 0 else 0
            net_return = gross_return - (2 * self.fee_rate)

            # Update last price
            self.mark_position(name, current_price, note=f"holding_return={net_return:.2%}")

            # Close if holding period exceeded
            if holding_hours >= int(pos.get("max_holding_hours") or self.max_holding_hours):
                result = self._close_position(pos, current_price, now_ts, "simulated_sell")
                if result:
                    # Update signal with simulated sell data
                    signal_id = pos.get("signal_id")
                    if signal_id:
                        self.db.update_signal_simulated_sell(
                            signal_id, current_price, net_return, now_ts
                        )
                    closed.append(result)

        return closed

    def _close_position(self, position, current_price, now_ts, reason):
        """Close a position and record the execution."""
        name = position["hash_name"]
        entry_price = float(position["entry_price"])
        gross_return = (float(current_price) - entry_price) / entry_price if entry_price > 0 else 0
        net_return = gross_return - (2 * self.fee_rate)
        fee_amount = float(current_price) * self.fee_rate
        net_amount = float(current_price) * (1 - self.fee_rate)

        self.db.record_execution({
            "position_id": position.get("position_id"),
            "signal_id": position.get("signal_id"),
            "hash_name": name,
            "side": "SELL",
            "exec_time": now_ts,
            "price": current_price,
            "quantity": position.get("quantity", 1),
            "gross_amount": current_price,
            "fee_amount": fee_amount,
            "net_amount": net_amount,
            "realized_return": net_return,
            "reason": reason,
        })
        self.db.close_position(name, current_price, now_ts, note=reason)
        return {
            "name": name,
            "reason": reason,
            "entry_price": entry_price,
            "sell_price": current_price,
            "net_return": net_return,
            "holding_hours": (now_ts - int(position["entry_time"])) / 3600,
        }
