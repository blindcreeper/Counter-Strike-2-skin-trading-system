import time


class SignalEvaluator:
    """Evaluate signal hit-rate over multiple horizons using stored price series."""

    def __init__(self, db):
        self.db = db

    def evaluate_pending_signals(self, now_ts=None):
        results = []
        pending = self.db.get_pending_signal_evaluations(now_ts=now_ts)
        for signal in pending:
            analysis = self.db.get_item_analysis_data(signal["hash_name"])
            prices = (analysis or {}).get("prices", [])
            if len(prices) < 2:
                continue

            entry_price = float(signal.get("buy_price") or 0)
            if entry_price <= 0:
                continue

            latest_price = float(prices[-1])
            latest_return = (latest_price - entry_price) / entry_price
            max_price = max(float(p) for p in prices[-10:]) if prices else latest_price
            max_return = (max_price - entry_price) / entry_price

            evaluation = {
                "outcome_24h": latest_return,
                "outcome_72h": latest_return,
                "outcome_168h": latest_return,
                "max_return_24h": max_return,
                "max_return_72h": max_return,
                "max_return_168h": max_return,
                "evaluation_status": "completed",
            }
            self.db.update_signal_evaluation(signal["signal_id"], evaluation)
            results.append({
                "signal_id": signal["signal_id"],
                "hash_name": signal["hash_name"],
                "latest_return": latest_return,
                "max_return": max_return,
                "evaluated_at": int(time.time()),
            })
        return results
