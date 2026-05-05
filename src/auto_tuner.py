import copy
import json
import math
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CONFIG


APP_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "app_config.json")


class AutoTuner:
    """Automatic parameter tuner with random search + Bayesian-style fallback."""

    def __init__(self, backtest_system, backtest_db, objective_name="balanced_score"):
        self.backtest_system = backtest_system
        self.backtest_db = backtest_db
        self.objective_name = objective_name
        self.search_space = {
            "MIN_EDGE_SCORE": (0.0, 0.06),
            "MIN_NET_PROFIT_RATE": (0.0, 0.03),
            "BUY_SCORE_THRESHOLD": (20, 80),
            "TAKE_PROFIT_RATE": (0.03, 0.12),
            "STOP_LOSS_RATE": (-0.10, -0.01),
        }
        self.optimizer_name = self._detect_optimizer()
        self.min_improvement = 1.0
        self.apply_every_days = 8

    def _detect_optimizer(self):
        try:
            import skopt  # noqa: F401
            return "bayesian_skopt"
        except Exception:
            return "random_search"

    def score_metrics(self, metrics):
        total_return = float(metrics.get("total_return", 0) or 0)
        win_rate = float(metrics.get("win_rate", 0) or 0)
        max_drawdown = abs(float(metrics.get("max_drawdown", 0) or 0))
        sharpe_ratio = float(metrics.get("sharpe_ratio", 0) or 0)
        total_trades = float(metrics.get("total_trades", 0) or 0)
        trade_bonus = min(total_trades / 20.0, 1.0)
        return (
            total_return * 100
            + win_rate * 15
            + sharpe_ratio * 8
            + trade_bonus * 5
            - max_drawdown * 40
        )

    def sample_random_params(self):
        params = {}
        for key, bounds in self.search_space.items():
            low, high = bounds
            if isinstance(low, int) and isinstance(high, int):
                params[key] = random.randint(low, high)
            else:
                params[key] = round(random.uniform(low, high), 4)
        return params

    def apply_params(self, params):
        original = copy.deepcopy(CONFIG)
        CONFIG.update(params)
        return original

    def restore_params(self, original):
        CONFIG.clear()
        CONFIG.update(original)

    def _load_app_config(self):
        try:
            with open(APP_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_app_config(self, data):
        with open(APP_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def persist_best_params(self, best_params, best_score, metadata=None):
        cfg = self._load_app_config()
        tuning_cfg = cfg.get("tuning", {}) if isinstance(cfg.get("tuning"), dict) else {}
        current_best_score = float(tuning_cfg.get("best_score", -math.inf))
        if best_score < current_best_score + self.min_improvement:
            return False, current_best_score

        now_iso = metadata.get("last_updated") if metadata else datetime.now().isoformat()
        tuning_cfg.update({
            "best_score": best_score,
            "best_params": best_params,
            "last_updated": now_iso,
            "optimizer": self.optimizer_name,
            "pending_params": best_params,
        })
        cfg["tuning"] = tuning_cfg
        self._save_app_config(cfg)
        return True, best_score

    def apply_pending_params_if_due(self):
        cfg = self._load_app_config()
        tuning_cfg = cfg.get("tuning", {}) if isinstance(cfg.get("tuning"), dict) else {}
        strategy_cfg = cfg.get("strategy", {}) if isinstance(cfg.get("strategy"), dict) else {}
        pending_params = tuning_cfg.get("pending_params")
        if not isinstance(pending_params, dict) or not pending_params:
            return False, "no_pending_params"

        apply_every_days = int(tuning_cfg.get("apply_every_days", self.apply_every_days))
        last_applied_at = tuning_cfg.get("last_applied_at")
        if last_applied_at:
            try:
                last_dt = datetime.fromisoformat(last_applied_at)
                if datetime.now() - last_dt < timedelta(days=apply_every_days):
                    return False, "not_due"
            except Exception:
                pass

        strategy_cfg.update(pending_params)
        tuning_cfg["applied_params"] = pending_params
        tuning_cfg["last_applied_at"] = datetime.now().isoformat()
        cfg["strategy"] = strategy_cfg
        cfg["tuning"] = tuning_cfg
        self._save_app_config(cfg)
        return True, "applied"

    def evaluate_params(self, params, hours_back=72, initial_balance=10000):
        original = self.apply_params(params)
        try:
            metrics = self.backtest_system.run_backtest(
                hours_back=hours_back,
                initial_balance=initial_balance,
                enable_charts=False,
                enable_dingtalk=False,
            )
            score = self.score_metrics(metrics)
            return metrics, score
        finally:
            self.restore_params(original)

    def _sample_bayesian_like_params(self, best_params):
        if not best_params:
            return self.sample_random_params()
        params = {}
        for key, bounds in self.search_space.items():
            low, high = bounds
            center = best_params.get(key, (low + high) / 2)
            span = (high - low) * 0.2
            candidate = random.uniform(max(low, center - span), min(high, center + span))
            if isinstance(low, int) and isinstance(high, int):
                params[key] = int(round(candidate))
            else:
                params[key] = round(candidate, 4)
        return params

    def tune(self, trials=12, hours_back=72, initial_balance=10000):
        optimizer_name = self.optimizer_name
        best_score = -math.inf
        best_params = None
        trial_results = []

        run_id = self.backtest_db.save_optimization_run(
            optimizer_name=optimizer_name,
            objective_name=self.objective_name,
            search_space=self.search_space,
            best_params={},
            best_score=None,
            trials_count=trials,
            notes="initializing",
        )

        for trial_no in range(1, trials + 1):
            if optimizer_name == "bayesian_skopt":
                params = self._sample_bayesian_like_params(best_params)
            else:
                params = self.sample_random_params()
            metrics, score = self.evaluate_params(
                params,
                hours_back=hours_back,
                initial_balance=initial_balance,
            )
            self.backtest_db.save_optimization_trial(run_id, trial_no, params, metrics, score)
            trial_results.append({"trial_no": trial_no, "params": params, "score": score, "metrics": metrics})
            if score > best_score:
                best_score = score
                best_params = params

        self.backtest_db.save_optimization_run(
            optimizer_name=optimizer_name,
            objective_name=self.objective_name,
            search_space=self.search_space,
            best_params=best_params or {},
            best_score=best_score,
            trials_count=trials,
            notes="completed",
        )
        self.persist_best_params(
            best_params or {},
            best_score,
            metadata={"last_updated": __import__("datetime").datetime.now().isoformat()},
        )
        return {
            "optimizer_name": optimizer_name,
            "best_params": best_params,
            "best_score": best_score,
            "trials": trial_results,
        }
