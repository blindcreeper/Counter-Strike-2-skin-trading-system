import numpy as np


class QuantStrategy:
    """
    V2 strategy tuned for cross-platform spread picks.
    It keeps the original momentum factors (slope/ER/Hurst) and
    adds context-aware features from real opportunity logs:
    price bucket, platform pair, item keyword, and recent price-change frequency.
    """

    def __init__(self, config):
        self.config = config
        self.min_profit_gate = float(config.get("MIN_PROFIT", 0.03))
        self.buy_score_threshold = float(config.get("BUY_SCORE_THRESHOLD", 62))

        # 从配置读取权重，如果没有则使用默认值
        self.momentum_weight = float(config.get("momentum_weight", 0.65))
        self.spread_weight = float(config.get("spread_weight", 1.15))
        self.pair_weight = float(config.get("pair_weight", 0.75))
        self.price_weight = float(config.get("price_weight", 0.35))
        self.keyword_weight = float(config.get("keyword_weight", 0.6))

        # 平台对权重 - 从配置读取或使用默认
        self.pair_weights = config.get("pair_weights", {
            ("C5", "HALOSKINS"): -16,
            ("C5", "BUFF"): -11,
            ("HALOSKINS", "YOUPIN"): -9,
            ("YOUPIN", "BUFF"): 10,
            ("BUFF", "YOUPIN"): 7,
            ("BUFF", "HALOSKINS"): 6,
            ("YOUPIN", "HALOSKINS"): 5,
            ("C5", "YOUPIN"): 8,
        })

        # 关键词权重 - 从配置读取或使用默认
        self.keyword_weights = config.get("keyword_weights", {
            "MAC-10": 6,
            "KNIFE": 6,
            "AWP": 4,
            "M4A1-S": 3,
            "USP-S": -7,
            "GLOVES": -8,
            "AK-47": -3,
            "GLOCK-18": -2,
        })

    def calculate_hurst(self, prices):
        """R/S-based Hurst estimation with guard rails for short/noisy series."""
        if len(prices) < 4:
            return 0.5

        y = np.array(prices, dtype=float)
        n = len(y)
        max_lag = max(2, n // 2)
        if max_lag <= 2:
            return 0.5

        lags = range(2, max_lag)
        tau = []
        for lag in lags:
            diff = y[lag:] - y[:-lag]
            std = np.std(diff)
            tau.append(np.sqrt(std if std > 0 else 1e-9))

        if len(tau) < 2:
            return 0.5

        try:
            m = np.polyfit(np.log(list(lags)), np.log(tau), 1)
            return float(m[0])
        except Exception:
            return 0.5

    @staticmethod
    def _price_bucket_score(price):
        if price is None:
            return 0
        if price < 100:
            return 10
        if price < 300:
            return 6
        if price < 700:
            return 0
        if price < 1500:
            return -4
        if price < 3000:
            return -8
        return -12

    @staticmethod
    def _slope_score(slope):
        # Empirically: 0.06~0.08 performed best for >3% hit-rate.
        if slope < 0.045:
            return -10
        if slope < 0.06:
            return 2
        if slope < 0.08:
            return 4
        if slope < 0.10:
            return 1
        if slope < 0.12:
            return -3
        if slope < 0.15:
            return 2
        if slope < 0.20:
            return 3
        return 1

    @staticmethod
    def _er_score(er):
        if er >= 0.9:
            return 5
        if er >= 0.8:
            return -1
        if er >= 0.7:
            return 2
        if er >= 0.5:
            return -1
        return 3

    @staticmethod
    def _hurst_score(hurst_val):
        # Empirically: 0.17~0.21 was stronger than very high Hurst.
        if hurst_val < 0.17:
            return -4
        if hurst_val < 0.21:
            return 3
        if hurst_val < 0.24:
            return -1
        return -2

    @staticmethod
    def _changes_score(changes):
        # Bell-shaped preference:
        # too low may indicate stale quotes; too high means noisy market.
        if changes <= 1:
            return -2
        if changes <= 4:
            return 7
        if changes <= 6:
            return 3
        if changes <= 8:
            return -3
        return -6

    def _keyword_score(self, name):
        if not name:
            return 0
        u = name.upper()
        score = 0
        for keyword, weight in self.keyword_weights.items():
            if keyword in u:
                score += weight
        return score

    def _pair_score(self, buy_from, sell_to):
        return self.pair_weights.get((str(buy_from or "").upper(), str(sell_to or "").upper()), 0)

    def _spread_score(self, net_profit_rate, buy_from, sell_to):
        """
        Increase opportunity score when cross-platform spread is large.
        Higher spread carries much more weight in V2.1.
        """
        p = self._safe_float(net_profit_rate, -1.0)
        if p < 0:
            return -12
        if p < 0.03:
            return -10
        if p < 0.05:
            return 0
        if p < 0.08:
            base = 7
        elif p < 0.12:
            base = 13
        elif p < 0.20:
            base = 20
        else:
            base = 24

        pair = (str(buy_from or "").upper(), str(sell_to or "").upper())
        good_pairs = {
            ("BUFF", "HALOSKINS"),
            ("YOUPIN", "HALOSKINS"),
            ("YOUPIN", "BUFF"),
            ("BUFF", "YOUPIN"),
            ("C5", "YOUPIN"),
        }
        if p >= 0.08 and pair in good_pairs:
            base += 4
        return base

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def calculate_momentum_score(self, slope, er, hurst_val, changes):
        """
        Momentum score redesigned to reduce score saturation:
        lower coefficients + frequency penalty.
        """
        raw = ((slope / 0.1) * 22) + (er * 26) + (hurst_val * 18) + ((10 - min(changes, 10)) * 2)
        return round(max(0.0, min(99.0, raw)), 2)

    def calculate_opportunity_score(self, slope, er, hurst_val, changes, trade_ctx):
        buy_price = self._safe_float(trade_ctx.get("buy_price"), 0.0)
        buy_from = str(trade_ctx.get("buy_from", "")).upper()
        sell_to = str(trade_ctx.get("sell_to", "")).upper()
        name = trade_ctx.get("name", "")
        net_profit_rate = self._safe_float(trade_ctx.get("net_profit_rate"), -1.0)

        # 综合分主要由动量因子和平台价差构成，辅助考虑价格区间、平台对和关键词。
        score = 0.0
        score += self.calculate_momentum_score(slope, er, hurst_val, changes) * self.momentum_weight
        score += self._spread_score(net_profit_rate, buy_from, sell_to) * self.spread_weight
        score += self._pair_score(buy_from, sell_to) * self.pair_weight
        score += self._price_bucket_score(buy_price) * self.price_weight
        score += self._keyword_score(name) * self.keyword_weight
        return round(max(0.0, min(99.0, score)), 2)

    def analyze(self, item_data, trade_ctx=None):
        """
        item_data: {"prices": [], "sales": [], "series_trend": float, ...}
        trade_ctx: {
          "name": str, "buy_price": float, "buy_from": str,
          "sell_to": str, "net_profit_rate": float
        }
        """
        trade_ctx = trade_ctx or {}

        if not item_data:
            return {"action": "WAIT", "msg": "暂无历史数据"}

        prices = item_data.get("prices", [])
        series_trend = self._safe_float(item_data.get("series_trend", 0), 0.0)
        if len(prices) < 15:
            return {"action": "WAIT", "msg": f"数据积累中({len(prices)}/15)"}

        if series_trend < -2:
            return {"action": "SKIP", "msg": "板块趋势低迷"}

        start_p = prices[-10]
        end_p = prices[-1]
        if not start_p:
            return {"action": "WAIT", "msg": "价格数据异常(0)"}

        changes = 0
        for i in range(len(prices) - 9, len(prices)):
            if prices[i] != prices[i - 1]:
                changes += 1

        slope = (end_p - start_p) / start_p
        total_change = abs(prices[-1] - prices[-10])
        volatility = sum(abs(prices[i] - prices[i - 1]) for i in range(len(prices) - 9, len(prices)))
        er = total_change / volatility if volatility else 0.0
        hurst_val = self.calculate_hurst(prices)

        momentum_score = self.calculate_momentum_score(slope, er, hurst_val, changes)
        composite_score = self.calculate_opportunity_score(slope, er, hurst_val, changes, trade_ctx)

        net_profit_rate = self._safe_float(trade_ctx.get("net_profit_rate"), -1.0)
        if net_profit_rate < self.min_profit_gate:
            return {
                "action": "HOLD",
                "score": composite_score,
                "score1": momentum_score,
                "score2": composite_score,
                "slope": f"{slope:.2%}",
                "er": round(er, 2),
                "changes": changes,
                "hurst": round(hurst_val, 2),
                "msg": f"预期净利不足({net_profit_rate:.2%} < {self.min_profit_gate:.2%})",
            }

        # Hard risk control from observed weak zones.
        buy_from = str(trade_ctx.get("buy_from", "")).upper()
        sell_to = str(trade_ctx.get("sell_to", "")).upper()
        if (buy_from, sell_to) == ("C5", "HALOSKINS") and net_profit_rate < 0.09:
            return {
                "action": "HOLD",
                "score": composite_score,
                "score1": momentum_score,
                "score2": composite_score,
                "slope": f"{slope:.2%}",
                "er": round(er, 2),
                "changes": changes,
                "hurst": round(hurst_val, 2),
                "msg": "C5->HALOSKINS 组合仅保留高净利样本",
            }

        if (buy_from, sell_to) == ("C5", "BUFF") and net_profit_rate < 0.07:
            return {
                "action": "HOLD",
                "score": composite_score,
                "score1": momentum_score,
                "score2": composite_score,
                "slope": f"{slope:.2%}",
                "er": round(er, 2),
                "changes": changes,
                "hurst": round(hurst_val, 2),
                "msg": "C5->BUFF 组合仅保留高净利样本",
            }

        if self._safe_float(trade_ctx.get("buy_price"), 0.0) >= 1500 and net_profit_rate < 0.08:
            return {
                "action": "HOLD",
                "score": composite_score,
                "score1": momentum_score,
                "score2": composite_score,
                "slope": f"{slope:.2%}",
                "er": round(er, 2),
                "changes": changes,
                "hurst": round(hurst_val, 2),
                "msg": "高价品需更高净利空间(>=8%)",
            }

        if changes >= 7 and net_profit_rate < 0.08:
            return {
                "action": "HOLD",
                "score": composite_score,
                "score1": momentum_score,
                "score2": composite_score,
                "slope": f"{slope:.2%}",
                "er": round(er, 2),
                "changes": changes,
                "hurst": round(hurst_val, 2),
                "msg": "近期变价过于频繁，先观察",
            }

        min_trend = max(self.config.get("FEE_RATE", 0.025) + 0.02, 0.045)
        if slope >= min_trend and composite_score >= self.buy_score_threshold:
            return {
                "action": "BUY",
                "score": composite_score,
                "score1": momentum_score,
                "score2": composite_score,
                "slope": f"{slope:.2%}",
                "er": round(er, 2),
                "changes": changes,
                "hurst": round(hurst_val, 2),
                "msg": f"复合评分通过 (score={composite_score:.2f})",
            }

        ma10 = sum(prices[-10:]) / 10
        if prices[-1] < ma10:
            return {
                "action": "SELL",
                "score": composite_score,
                "score1": momentum_score,
                "score2": composite_score,
                "slope": f"{slope:.2%}",
                "er": round(er, 2),
                "changes": changes,
                "hurst": round(hurst_val, 2),
                "msg": "跌破 MA10",
            }

        return {
            "action": "HOLD",
            "score": composite_score,
            "score1": momentum_score,
            "score2": composite_score,
            "slope": f"{slope:.2%}",
            "er": round(er, 2),
            "changes": changes,
            "hurst": round(hurst_val, 2),
            "msg": f"观察中 (score={composite_score:.2f})",
        }
