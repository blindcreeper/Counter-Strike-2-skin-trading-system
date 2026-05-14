import numpy as np


class QuantStrategy:
    """
    Trend-prediction strategy using daily K-line data for 7-day price forecasting.
    K-line factors: multi-scale momentum, MA deviation, volatility, position in range.
    Falls back to sampled price series when K-line is unavailable.
    """

    def __init__(self, config):
        self.config = config
        self.min_net_profit_gate = float(
            config.get("MIN_NET_PROFIT_RATE", config.get("MIN_PROFIT", 0.03))
        )
        self.buy_score_threshold = float(config.get("BUY_SCORE_THRESHOLD", 62))
        self.trend_score_threshold = float(config.get("TREND_SCORE_THRESHOLD", 50))

        # 数据驱动的过滤阈值（基于 1317 商品回测分析）
        self.min_slope_threshold = float(config.get("MIN_SLOPE_THRESHOLD", 0.0))
        self.min_ma_ratio = float(config.get("MIN_MA_RATIO", -999))
        self.max_price_data = float(config.get("MAX_PRICE_DATA_DRIVEN", 99999))

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

    def predict_7d_trend(self, kline_data):
        """
        Predict 7-day price trend using daily K-line data.
        kline_data: list of [timestamp, close, open, high, low]
        Returns trend_score in [-100, +100]. Positive = bullish.
        """
        if not kline_data or len(kline_data) < 20:
            return 0.0

        closes = np.array([float(k[1]) for k in kline_data], dtype=float)
        n = len(closes)
        score = 0.0

        # Factor 1: Short-term slope (10 days)
        short = closes[-10:]
        short_slope = (short[-1] - short[0]) / short[0] if short[0] > 0 else 0
        score += np.clip(short_slope * 500, -25, 25)

        # Factor 2: Medium-term slope (30 days)
        if n >= 30:
            mid = closes[-30:]
            mid_slope = (mid[-1] - mid[0]) / mid[0] if mid[0] > 0 else 0
            score += np.clip(mid_slope * 300, -25, 25)
        else:
            mid_slope = short_slope

        # Factor 3: Momentum acceleration
        accel = short_slope - mid_slope
        score += np.clip(accel * 400, -15, 15)

        # Factor 4: Price vs MA20
        if n >= 20:
            ma20 = np.mean(closes[-20:])
            deviation = (closes[-1] - ma20) / ma20 if ma20 > 0 else 0
            score += np.clip(deviation * 300, -15, 15)

        # Factor 5: Price vs MA60
        if n >= 60:
            ma60 = np.mean(closes[-60:])
            dev60 = (closes[-1] - ma60) / ma60 if ma60 > 0 else 0
            score += np.clip(dev60 * 200, -10, 10)

        # Factor 6: Volatility (low vol = stable uptrend)
        if n >= 20:
            returns = np.diff(closes[-20:]) / closes[-20:-1]
            vol = np.std(returns)
            if vol < 0.01:
                score += 10
            elif vol < 0.02:
                score += 5
            elif vol > 0.05:
                score -= 10
            else:
                score -= 3

        # Factor 7: Price position in 30-day range
        if n >= 30:
            high30 = np.max(closes[-30:])
            low30 = np.min(closes[-30:])
            rng = high30 - low30
            if rng > 0:
                position = (closes[-1] - low30) / rng
                score += np.clip((position - 0.5) * 30, -15, 15)

        # Factor 8: MA crossover (MA5 vs MA20)
        if n >= 20:
            ma5 = np.mean(closes[-5:])
            ma20_val = np.mean(closes[-20:])
            cross = (ma5 - ma20_val) / ma20_val if ma20_val > 0 else 0
            score += np.clip(cross * 400, -10, 10)

        return round(float(np.clip(score, -100, 100)), 2)

    def predict_7d_trend_fallback(self, prices, sales=None):
        """Fallback using sampled price series when kline is unavailable."""
        if not prices or len(prices) < 15:
            return 0.0
        p = np.array(prices, dtype=float)
        short = p[-10:]
        short_slope = (short[-1] - short[0]) / short[0] if short[0] > 0 else 0
        score = np.clip(short_slope * 400, -40, 40)
        if len(p) >= 20:
            ma20 = np.mean(p[-20:])
            dev = (p[-1] - ma20) / ma20 if ma20 > 0 else 0
            score += np.clip(dev * 200, -20, 20)
        return round(float(np.clip(score, -100, 100)), 2)

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

    def _spread_score(self, price_edge_rate, buy_from, sell_to):
        """
        Increase opportunity score when cross-platform spread is large.
        Higher spread carries much more weight in V2.1.
        """
        p = self._safe_float(price_edge_rate, -1.0)
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
        except (TypeError, ValueError):
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
        price_edge_rate = self._safe_float(trade_ctx.get("price_edge_rate"), -1.0)

        # 综合分主要由动量因子和平台价差构成，辅助考虑价格区间、平台对和关键词。
        score = 0.0
        score += self.calculate_momentum_score(slope, er, hurst_val, changes) * self.momentum_weight
        score += self._spread_score(price_edge_rate, buy_from, sell_to) * self.spread_weight
        score += self._pair_score(buy_from, sell_to) * self.pair_weight
        score += self._price_bucket_score(buy_price) * self.price_weight
        score += self._keyword_score(name) * self.keyword_weight
        return round(max(0.0, min(99.0, score)), 2)

    def analyze(self, item_data, trade_ctx=None, collect_mode=False):
        """
        item_data: {"prices": [], "sales": [], "series_trend": float, ...}
        trade_ctx: {
          "name": str, "buy_price": float, "buy_from": str,
          "sell_to": str, "price_edge_rate": float, "estimated_net_return": float
        }
        collect_mode: 数据采集模式，跳过所有策略过滤，只记录评分
        """
        trade_ctx = trade_ctx or {}

        kline_data = trade_ctx.get("kline")
        has_kline = kline_data and len(kline_data) >= 20

        if not item_data and not has_kline:
            return {"action": "WAIT", "msg": "暂无历史数据"}

        prices = item_data.get("prices", []) if item_data else []
        sales = item_data.get("sales", []) if item_data else []
        series_trend = self._safe_float(item_data.get("series_trend", 0), 0.0) if item_data else 0.0
        if not has_kline and len(prices) < 15:
            return {"action": "WAIT", "msg": f"数据积累中({len(prices)}/15)"}

        # Compute old-style indicators if we have sampled data
        if len(prices) >= 10:
            start_p = prices[-10]
            end_p = prices[-1]
            if not start_p:
                return {"action": "WAIT", "msg": "价格数据异常(0)"}
            changes = sum(1 for i in range(len(prices) - 9, len(prices)) if prices[i] != prices[i - 1])
            slope = (end_p - start_p) / start_p
            total_change = abs(prices[-1] - prices[-10])
            vol_sum = sum(abs(prices[i] - prices[i - 1]) for i in range(len(prices) - 9, len(prices)))
            er = total_change / vol_sum if vol_sum else 0.0
            hurst_val = self.calculate_hurst(prices)
        else:
            slope, er, hurst_val, changes = 0.0, 0.0, 0.5, 0

        momentum_score = self.calculate_momentum_score(slope, er, hurst_val, changes)
        composite_score = self.calculate_opportunity_score(slope, er, hurst_val, changes, trade_ctx)

        if has_kline:
            trend_score = self.predict_7d_trend(kline_data)
        else:
            trend_score = self.predict_7d_trend_fallback(prices, sales)

        estimated_net_return = self._safe_float(
            trade_ctx.get("estimated_net_return", trade_ctx.get("net_profit_rate")),
            -1.0,
        )

        base_result = {
            "score": composite_score,
            "score1": momentum_score,
            "score2": composite_score,
            "trend_score": trend_score,
            "slope": f"{slope:.2%}",
            "er": round(er, 2),
            "changes": changes,
            "hurst": round(hurst_val, 2),
        }

        # collect 模式：只算分不过滤，所有商品都记录为 TRACK
        if collect_mode:
            base_result["action"] = "HOLD"
            base_result["msg"] = (
                f"[采集] score={composite_score:.2f} trend={trend_score:.1f} "
                f"slope={slope:.2%} net={estimated_net_return:.2%}"
            )
            return base_result

        # --- 以下是 trade 模式的趋势预测逻辑 ---

        # 数据驱动过滤（基于 1317 商品回测分析，区分度 top3）
        # 1. slope 过滤（区分度 0.92，最关键指标）
        if slope < self.min_slope_threshold:
            base_result["action"] = "HOLD"
            base_result["msg"] = f"斜率不足({slope:.2%} < {self.min_slope_threshold:.2%})"
            return base_result

        # 2. 价格必须在 MA10 上方（区分度 0.80）
        ma10 = sum(prices[-10:]) / 10
        ma_ratio = (prices[-1] - ma10) / ma10 if ma10 > 0 else 0
        if ma_ratio < self.min_ma_ratio:
            base_result["action"] = "HOLD"
            base_result["msg"] = f"低于MA10({ma_ratio:.2%} < {self.min_ma_ratio:.2%})"
            return base_result

        # 3. 低价品优先（区分度 0.59，涨组 75% 在 446 元以下）
        buy_price = self._safe_float(trade_ctx.get("buy_price"), 0.0)
        if buy_price > self.max_price_data:
            base_result["action"] = "HOLD"
            base_result["msg"] = f"价格过高({buy_price:.0f} > {self.max_price_data:.0f})"
            return base_result

        if changes >= 7 and slope < 0:
            base_result["action"] = "HOLD"
            base_result["msg"] = "近期变价过于频繁且趋势向下，先观察"
            return base_result

        # 核心判断：7天趋势预测评分
        if trend_score >= self.trend_score_threshold:
            base_result["action"] = "BUY"
            base_result["msg"] = f"趋势看涨 (trend={trend_score:.1f}, slope={slope:.2%})"
            return base_result

        if len(prices) >= 10 and prices[-1] < ma10:
            base_result["action"] = "SELL"
            base_result["msg"] = "跌破 MA10"
            return base_result

        base_result["action"] = "HOLD"
        base_result["msg"] = f"观察中 (trend={trend_score:.1f}, score={composite_score:.2f})"
        return base_result
