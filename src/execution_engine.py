import time


class ExecutionEngine:
    """Minimal live position/execution layer for signal closure and evaluation."""

    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.fee_rate = float(config.get("PLATFORM_FEE_RATE", config.get("FEE_RATE", 0.025)))
        self.take_profit_rate = float(config.get("TAKE_PROFIT_RATE", 0.08))
        self.stop_loss_rate = float(config.get("STOP_LOSS_RATE", -0.05))
        self.max_holding_hours = int(config.get("HOLDING_PERIOD_HOURS", 72))

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
            "notes": "opened_by_buy_signal",
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
            "reason": "buy_signal",
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
        position = self.db.get_open_position(name)
        if not position:
            return None

        now_ts = int(now_ts or time.time())
        entry_price = float(position["entry_price"])
        holding_hours = (now_ts - int(position["entry_time"])) / 3600
        gross_return = (float(current_price) - entry_price) / entry_price if entry_price > 0 else 0
        net_return = gross_return - (2 * self.fee_rate)

        reason = None
        if net_return >= float(position.get("take_profit_rate") or self.take_profit_rate):
            reason = "take_profit"
        elif net_return <= float(position.get("stop_loss_rate") or self.stop_loss_rate):
            reason = "stop_loss"
        elif holding_hours >= int(position.get("max_holding_hours") or self.max_holding_hours):
            reason = "timeout_exit"

        if not reason:
            self.mark_position(name, current_price, note="holding")
            return None

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
        return {"name": name, "reason": reason, "net_return": net_return}
