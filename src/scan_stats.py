"""Scan statistics tracker with heartbeat file.

Tracks scan progress, item counts, buy signals, errors,
and writes a heartbeat file that can be monitored remotely.
"""
import json
import os
import threading
import time
from datetime import datetime


class ScanStats:
    """Thread-safe scan statistics collector."""

    def __init__(self, heartbeat_path="heartbeat.json"):
        self._lock = threading.Lock()
        self.heartbeat_path = heartbeat_path
        self.reset()

    def reset(self):
        with self._lock:
            self.state = {
                "status": "idle",
                "pid": os.getpid(),
                "started_at": None,
                "last_heartbeat": None,
                "round_count": 0,
                "current_round": 0,
                "current_batch": 0,
                "total_batches": 0,
                "items_scanned": 0,
                "items_skipped_price": 0,
                "items_skipped_sales": 0,
                "items_skipped_blacklist": 0,
                "buy_signals": 0,
                "wait_signals": 0,
                "hold_signals": 0,
                "sell_signals": 0,
                "skip_signals": 0,
                "cooldown_skips": 0,
                "throttle_skips": 0,
                "errors": 0,
                "last_error": None,
                "last_error_time": None,
                "last_buy_signal": None,
                "recent_items": [],
            }

    def start_round(self, round_num, total_items):
        with self._lock:
            self.state["status"] = "scanning"
            self.state["started_at"] = datetime.now().isoformat()
            self.state["round_count"] = round_num
            self.state["current_round"] = round_num
            self.state["items_scanned"] = 0
            self.state["buy_signals"] = 0
            self.state["wait_signals"] = 0
            self.state["hold_signals"] = 0
            self.state["sell_signals"] = 0
            self.state["skip_signals"] = 0
            self.state["cooldown_skips"] = 0
            self.state["throttle_skips"] = 0
            self.state["errors"] = 0
            self.state["recent_items"] = []
            self.state["total_items"] = total_items
        self._heartbeat()

    def start_batch(self, batch_idx, total_batches):
        with self._lock:
            self.state["current_batch"] = batch_idx
            self.state["total_batches"] = total_batches
        self._heartbeat()

    def record_item(self, name, action, **kwargs):
        with self._lock:
            self.state["items_scanned"] += 1
            key = f"{action.lower()}_signals"
            if key in self.state:
                self.state[key] += 1
            else:
                self.state["errors"] += 1

            if action == "BUY":
                self.state["last_buy_signal"] = {
                    "time": datetime.now().isoformat(),
                    "name": name[:60],
                    **{k: v for k, v in kwargs.items() if k in (
                        "buy_price", "sell_price", "profit_rate", "score"
                    )},
                }

            entry = {
                "name": name[:40],
                "action": action,
                "time": datetime.now().strftime("%H:%M:%S"),
            }
            self.state["recent_items"] = (
                [entry] + self.state["recent_items"]
            )[:20]
        self._heartbeat()

    def record_skip(self, reason):
        with self._lock:
            key = f"items_skipped_{reason}"
            if key in self.state:
                self.state[key] += 1
        self._heartbeat()

    def record_cooldown(self):
        with self._lock:
            self.state["cooldown_skips"] += 1
        self._heartbeat()

    def record_throttle(self):
        with self._lock:
            self.state["throttle_skips"] += 1
        self._heartbeat()

    def record_error(self, error_msg):
        with self._lock:
            self.state["errors"] += 1
            self.state["last_error"] = str(error_msg)[:200]
            self.state["last_error_time"] = datetime.now().isoformat()
        self._heartbeat()

    def finish_round(self):
        with self._lock:
            self.state["status"] = "sleeping"
        self._heartbeat()

    def stop(self):
        with self._lock:
            self.state["status"] = "stopped"
        self._heartbeat()

    def get_snapshot(self):
        with self._lock:
            return dict(self.state)

    def _heartbeat(self):
        with self._lock:
            self.state["last_heartbeat"] = datetime.now().isoformat()
            try:
                with open(self.heartbeat_path, "w", encoding="utf-8") as f:
                    json.dump(self.state, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
