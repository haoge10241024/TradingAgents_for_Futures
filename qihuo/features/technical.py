from __future__ import annotations

import math
from typing import Dict, List, Tuple

import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def add_basic_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    输入: df 包含列 ["时间","开盘","最高","最低","收盘","成交量","持仓量"]，索引为递增时间。
    输出: 增加 MA/EMA/ATR 等常用指标。
    """
    out = df.copy()
    close = out["收盘"].astype(float)
    high = out["最高"].astype(float)
    low = out["最低"].astype(float)

    # 均线
    out["MA20"] = close.rolling(20, min_periods=20).mean()
    out["MA60"] = close.rolling(60, min_periods=60).mean()
    out["EMA20"] = _ema(close, 20)

    # ATR
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    out["ATR14"] = tr.rolling(14, min_periods=14).mean()

    # OI 变化与量价关系
    if "持仓量" in out.columns:
        out["OI_delta"] = out["持仓量"].astype(float).diff()
    if "成交量" in out.columns:
        out["VOL_MA20"] = out["成交量"].astype(float).rolling(20, min_periods=20).mean()

    return out


def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd = ema_fast - ema_slow
    macd_signal = _ema(macd, signal)
    macd_hist = macd - macd_signal
    return macd, macd_signal, macd_hist


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi


# ========== 高级技术指标计算函数 ==========

def _add_psar(df: pd.DataFrame, high: pd.Series, low: pd.Series, close: pd.Series, 
              af_start: float = 0.02, af_increment: float = 0.02, af_max: float = 0.2) -> pd.DataFrame:
    """PSAR (抛物线转向指标)"""
    length = len(close)
    psar = pd.Series(index=close.index, dtype=float)
    trend = pd.Series(index=close.index, dtype=int)  # 1=上升趋势, -1=下降趋势
    
    if length < 2:
        df["PSAR"] = psar
        df["PSAR_TREND"] = trend
        return df
    
    # 初始化
    psar.iloc[0] = low.iloc[0]
    trend.iloc[0] = 1
    af = af_start
    ep = high.iloc[0]  # 极值点
    
    for i in range(1, length):
        prev_psar = psar.iloc[i-1]
        prev_trend = trend.iloc[i-1]
        
        # 计算新的PSAR
        new_psar = prev_psar + af * (ep - prev_psar)
        
        # 趋势判断
        if prev_trend == 1:  # 上升趋势
            if low.iloc[i] <= new_psar:  # 趋势反转
                trend.iloc[i] = -1
                psar.iloc[i] = ep  # 使用之前的极值点
                af = af_start
                ep = low.iloc[i]
            else:  # 趋势延续
                trend.iloc[i] = 1
                psar.iloc[i] = max(new_psar, low.iloc[i-1], low.iloc[i-2] if i > 1 else low.iloc[i-1])
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + af_increment, af_max)
        else:  # 下降趋势
            if high.iloc[i] >= new_psar:  # 趋势反转
                trend.iloc[i] = 1
                psar.iloc[i] = ep
                af = af_start
                ep = high.iloc[i]
            else:  # 趋势延续
                trend.iloc[i] = -1
                psar.iloc[i] = min(new_psar, high.iloc[i-1], high.iloc[i-2] if i > 1 else high.iloc[i-1])
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + af_increment, af_max)
    
    df["PSAR"] = psar
    df["PSAR_TREND"] = trend
    return df


def _add_williams_r(df: pd.DataFrame, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.DataFrame:
    """Williams %R (威廉指标)"""
    highest_high = high.rolling(period, min_periods=period).max()
    lowest_low = low.rolling(period, min_periods=period).min()
    williams_r = -100 * (highest_high - close) / (highest_high - lowest_low).replace(0, pd.NA)
    df[f"WILLIAMS_R{period}"] = williams_r
    return df


def _add_cci(df: pd.DataFrame, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.DataFrame:
    """CCI (商品通道指数)"""
    typical_price = (high + low + close) / 3
    sma_tp = typical_price.rolling(period, min_periods=period).mean()
    mad = typical_price.rolling(period, min_periods=period).apply(lambda x: abs(x - x.mean()).mean(), raw=False)
    cci = (typical_price - sma_tp) / (0.015 * mad).replace(0, pd.NA)
    df[f"CCI{period}"] = cci
    return df


def _add_stoch_rsi(df: pd.DataFrame, close: pd.Series, period: int = 14, k_period: int = 3, d_period: int = 3) -> pd.DataFrame:
    """Stochastic RSI"""
    rsi = _rsi(close, period)
    rsi_lowest = rsi.rolling(period, min_periods=period).min()
    rsi_highest = rsi.rolling(period, min_periods=period).max()
    
    stoch_rsi = (rsi - rsi_lowest) / (rsi_highest - rsi_lowest).replace(0, pd.NA)
    stoch_k = stoch_rsi.rolling(k_period, min_periods=k_period).mean() * 100
    stoch_d = stoch_k.rolling(d_period, min_periods=d_period).mean()
    
    df["STOCH_RSI"] = stoch_rsi * 100
    df["STOCH_K"] = stoch_k
    df["STOCH_D"] = stoch_d
    return df


def _add_ichimoku(df: pd.DataFrame, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.DataFrame:
    """一目均衡表 (Ichimoku)"""
    # 转换线 (Tenkan-sen): 9日最高最低价平均
    tenkan_sen = (high.rolling(9, min_periods=9).max() + low.rolling(9, min_periods=9).min()) / 2
    
    # 基准线 (Kijun-sen): 26日最高最低价平均
    kijun_sen = (high.rolling(26, min_periods=26).max() + low.rolling(26, min_periods=26).min()) / 2
    
    # 先行带A (Senkou Span A): (转换线+基准线)/2，向前移动26日
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
    
    # 先行带B (Senkou Span B): 52日最高最低价平均，向前移动26日
    senkou_span_b = ((high.rolling(52, min_periods=52).max() + low.rolling(52, min_periods=52).min()) / 2).shift(26)
    
    # 滞后线 (Chikou Span): 当前收盘价向后移动26日
    chikou_span = close.shift(-26)
    
    df["TENKAN_SEN"] = tenkan_sen
    df["KIJUN_SEN"] = kijun_sen
    df["SENKOU_SPAN_A"] = senkou_span_a
    df["SENKOU_SPAN_B"] = senkou_span_b
    df["CHIKOU_SPAN"] = chikou_span
    
    # 云层厚度
    df["KUMO_THICKNESS"] = abs(senkou_span_a - senkou_span_b)
    
    return df


def _add_cmf(df: pd.DataFrame, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 20) -> pd.DataFrame:
    """Chaikin Money Flow (CMF)"""
    money_flow_multiplier = ((close - low) - (high - close)) / (high - low).replace(0, pd.NA)
    money_flow_volume = money_flow_multiplier * volume
    
    cmf = money_flow_volume.rolling(period, min_periods=period).sum() / volume.rolling(period, min_periods=period).sum().replace(0, pd.NA)
    df[f"CMF{period}"] = cmf
    return df


def _add_vpt(df: pd.DataFrame, close: pd.Series, volume: pd.Series) -> pd.DataFrame:
    """Volume Price Trend (VPT)"""
    price_change_pct = close.pct_change()
    vpt = (price_change_pct * volume).cumsum()
    df["VPT"] = vpt
    return df


def _add_tsi(df: pd.DataFrame, close: pd.Series, long_period: int = 25, short_period: int = 13) -> pd.DataFrame:
    """True Strength Index (TSI)"""
    price_change = close.diff()
    
    # 双重平滑
    first_smooth_pc = price_change.ewm(span=long_period).mean()
    second_smooth_pc = first_smooth_pc.ewm(span=short_period).mean()
    
    first_smooth_abs_pc = price_change.abs().ewm(span=long_period).mean()
    second_smooth_abs_pc = first_smooth_abs_pc.ewm(span=short_period).mean()
    
    tsi = 100 * second_smooth_pc / second_smooth_abs_pc.replace(0, pd.NA)
    df["TSI"] = tsi
    return df


def _add_cci_divergence(df: pd.DataFrame, close: pd.Series, period: int = 20) -> pd.DataFrame:
    """CCI背离指标"""
    if f"CCI{period}" not in df.columns:
        return df
    
    cci = df[f"CCI{period}"]
    
    # 寻找价格和CCI的局部高点和低点
    price_peaks = (close > close.shift(1)) & (close > close.shift(-1))
    price_troughs = (close < close.shift(1)) & (close < close.shift(-1))
    
    cci_peaks = (cci > cci.shift(1)) & (cci > cci.shift(-1))
    cci_troughs = (cci < cci.shift(1)) & (cci < cci.shift(-1))
    
    # 简化的背离检测
    bullish_divergence = price_troughs & ~cci_troughs  # 价格低点但CCI不是低点
    bearish_divergence = price_peaks & ~cci_peaks      # 价格高点但CCI不是高点
    
    df["CCI_BULL_DIV"] = bullish_divergence.astype(int)
    df["CCI_BEAR_DIV"] = bearish_divergence.astype(int)
    
    return df


def _add_oi_indicators(df: pd.DataFrame, close: pd.Series, volume: pd.Series, oi: pd.Series) -> pd.DataFrame:
    """期货持仓量相关指标"""
    # 持仓量变化率
    oi_change = oi.diff()
    oi_change_pct = oi.pct_change()
    
    df["OI_CHANGE"] = oi_change
    df["OI_CHANGE_PCT"] = oi_change_pct * 100
    
    # 持仓量移动平均
    df["OI_MA5"] = oi.rolling(5, min_periods=5).mean()
    df["OI_MA20"] = oi.rolling(20, min_periods=20).mean()
    
    # 持仓量相对位置
    oi_max_20 = oi.rolling(20, min_periods=20).max()
    oi_min_20 = oi.rolling(20, min_periods=20).min()
    df["OI_POSITION"] = (oi - oi_min_20) / (oi_max_20 - oi_min_20).replace(0, pd.NA) * 100
    
    # 价格-持仓量背离指标
    price_change_5 = close.diff(5)
    oi_change_5 = oi.diff(5)
    
    # 定义背离条件
    bullish_divergence = (price_change_5 < 0) & (oi_change_5 > 0)  # 价跌量增
    bearish_divergence = (price_change_5 > 0) & (oi_change_5 < 0)  # 价涨量减
    
    df["OI_PRICE_BULL_DIV"] = bullish_divergence.astype(int)
    df["OI_PRICE_BEAR_DIV"] = bearish_divergence.astype(int)
    
    # 持仓量强度指标 (OI Strength Index)
    oi_rsi = _rsi(oi, 14)
    df["OI_RSI"] = oi_rsi
    
    return df


def _add_futures_composite_indicators(df: pd.DataFrame, close: pd.Series, volume: pd.Series, oi: pd.Series) -> pd.DataFrame:
    """期货综合指标（价格-成交量-持仓量）"""
    # 价格动能指标
    price_momentum = close.pct_change(5) * 100
    df["PRICE_MOMENTUM_5D"] = price_momentum
    
    # 成交量动能指标
    volume_momentum = volume.pct_change(5) * 100
    df["VOLUME_MOMENTUM_5D"] = volume_momentum
    
    # 持仓量动能指标（如果有持仓量数据）
    if not oi.empty and not oi.isna().all():
        oi_momentum = oi.pct_change(5) * 100
        df["OI_MOMENTUM_5D"] = oi_momentum
        
        # 三维动能综合评分
        # 正常化处理（使用Z-score）
        price_z = (price_momentum - price_momentum.rolling(20).mean()) / price_momentum.rolling(20).std()
        volume_z = (volume_momentum - volume_momentum.rolling(20).mean()) / volume_momentum.rolling(20).std()
        oi_z = (oi_momentum - oi_momentum.rolling(20).mean()) / oi_momentum.rolling(20).std()
        
        # 综合评分（权重：价格40%，成交量30%，持仓量30%）
        composite_score = (price_z * 0.4 + volume_z * 0.3 + oi_z * 0.3)
        df["FUTURES_COMPOSITE_SCORE"] = composite_score
        
        # 市场参与度指标
        # 基于成交量和持仓量的相对变化
        vol_oi_ratio = volume / oi.replace(0, pd.NA)
        df["VOL_OI_RATIO"] = vol_oi_ratio
        df["VOL_OI_RATIO_MA20"] = vol_oi_ratio.rolling(20, min_periods=20).mean()
        
        # 资金流向指标
        # 当价格上涨且持仓量增加时，资金流入；反之流出
        price_change = close.diff()
        oi_change = oi.diff()
        
        money_flow = pd.Series(index=close.index, dtype=float)
        money_flow[(price_change > 0) & (oi_change > 0)] = 1  # 多头建仓
        money_flow[(price_change < 0) & (oi_change > 0)] = -1  # 空头建仓
        money_flow[(price_change > 0) & (oi_change < 0)] = -0.5  # 空头平仓
        money_flow[(price_change < 0) & (oi_change < 0)] = 0.5  # 多头平仓
        money_flow = money_flow.fillna(0)
        
        df["MONEY_FLOW_DIRECTION"] = money_flow
        df["MONEY_FLOW_MA5"] = money_flow.rolling(5, min_periods=5).mean()
        
    else:
        # 没有持仓量数据时的简化版本
        df["OI_MOMENTUM_5D"] = pd.NA
        df["FUTURES_COMPOSITE_SCORE"] = pd.NA
        df["VOL_OI_RATIO"] = pd.NA
        df["VOL_OI_RATIO_MA20"] = pd.NA
        df["MONEY_FLOW_DIRECTION"] = pd.NA
        df["MONEY_FLOW_MA5"] = pd.NA
    
    # 波动率-成交量关系
    returns = close.pct_change()
    volatility = returns.rolling(20, min_periods=20).std() * 100
    volume_normalized = volume / volume.rolling(20, min_periods=20).mean()
    
    df["VOLATILITY_20D"] = volatility
    df["VOLUME_NORMALIZED"] = volume_normalized
    
    # 波动率-成交量相关性
    vol_corr = returns.rolling(20, min_periods=20).corr(volume_normalized)
    df["VOL_PRICE_CORR"] = vol_corr
    
    return df


def add_extended_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    close = out["收盘"].astype(float)
    high = out["最高"].astype(float)
    low = out["最低"].astype(float)
    open_ = out["开盘"].astype(float) if "开盘" in out.columns else close

    # MACD
    macd, macd_signal, macd_hist = _macd(close)
    out["MACD"] = macd
    out["MACD_SIGNAL"] = macd_signal
    out["MACD_HIST"] = macd_hist

    # RSI
    out["RSI14"] = _rsi(close, 14)

    # BOLL(20)
    ma20 = out.get("MA20") if "MA20" in out.columns else close.rolling(20, min_periods=20).mean()
    std20 = close.rolling(20, min_periods=20).std()
    out["BOLL_MID"] = ma20
    out["BOLL_UP"] = ma20 + 2 * std20
    out["BOLL_LOW"] = ma20 - 2 * std20
    out["BOLL_BW"] = out["BOLL_UP"] - out["BOLL_LOW"]  # 带宽

    # 突破/回撤（20日窗口）
    out["HHV20"] = close.rolling(20, min_periods=20).max()
    out["LLV20"] = close.rolling(20, min_periods=20).min()
    out["BREAKOUT_LONG20"] = (close > out["HHV20"]).astype(int)
    out["BREAKOUT_SHORT20"] = (close < out["LLV20"]).astype(int)

    # 回撤强度（距20日高点的回撤比）
    out["PULLBACK20_PCT"] = (close - out["HHV20"]) / out["HHV20"].replace(0, pd.NA)

    # ADX/DMI(14)
    tr1 = (high - low).abs()
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    plus_dm = (high - high.shift(1)).clip(lower=0)
    minus_dm = (low.shift(1) - low).clip(lower=0)
    # 平滑
    period = 14
    atr = tr.rolling(period, min_periods=period).mean()
    plus_di = 100 * (plus_dm.rolling(period, min_periods=period).mean() / atr.replace(0, pd.NA))
    minus_di = 100 * (minus_dm.rolling(period, min_periods=period).mean() / atr.replace(0, pd.NA))
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA)).fillna(0)
    adx = dx.rolling(period, min_periods=period).mean()
    out["PLUS_DI14"] = plus_di
    out["MINUS_DI14"] = minus_di
    out["ADX14"] = adx

    # KDJ(9,3,3)
    n = 9
    rsv = (close - low.rolling(n, min_periods=n).min()) / (
        (high.rolling(n, min_periods=n).max() - low.rolling(n, min_periods=n).min()).replace(0, pd.NA)
    ) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    j = 3 * k - 2 * d
    out["KDJ_K"] = k
    out["KDJ_D"] = d
    out["KDJ_J"] = j

    # OBV
    vol = out.get("成交量", pd.Series(dtype=float)).astype(float)
    sign = close.diff().fillna(0).apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    out["OBV"] = (sign * vol).cumsum()
    out["VOL_MA20"] = vol.rolling(20, min_periods=20).mean()
    out["VOL_Z20"] = (vol - vol.rolling(20, min_periods=20).mean()) / vol.rolling(20, min_periods=20).std()

    # OI z-score
    if "持仓量" in out.columns:
        oi = out["持仓量"].astype(float)
        out["OI_Z20"] = (oi - oi.rolling(20, min_periods=20).mean()) / oi.rolling(20, min_periods=20).std()

    # VWAP(20) 近似（日频，用典型价 * 成交量 / 成交量）
    tp = (high + low + close) / 3
    vol_sum_20 = vol.rolling(20, min_periods=20).sum()
    out["VWAP20"] = (tp * vol).rolling(20, min_periods=20).sum() / vol_sum_20.replace(0, pd.NA)

    # Gaps & Candles
    prev_close = close.shift(1)
    out["GAP_PCT"] = (open_ - prev_close) / prev_close.replace(0, pd.NA)
    body = (close - open_).abs()
    upper_shadow = (high - pd.concat([open_, close], axis=1).max(axis=1)).clip(lower=0)
    lower_shadow = (pd.concat([open_, close], axis=1).min(axis=1) - low).clip(lower=0)
    out["UPPER_SHADOW_RATIO"] = upper_shadow / (body.replace(0, pd.NA))
    out["LOWER_SHADOW_RATIO"] = lower_shadow / (body.replace(0, pd.NA))

    # 波动百分位（180日）
    atr_ratio = out.get("ATR14", pd.Series(dtype=float)) / close.replace(0, pd.NA)
    def _percentile_rank(x: pd.Series) -> float:
        if x.isna().all():
            return float("nan")
        last = x.iloc[-1]
        s = x.dropna()
        if len(s) == 0:
            return float("nan")
        return float((s <= last).mean())
    out["ATR_RATIO"] = atr_ratio
    out["ATR_RATIO_PCTL180"] = atr_ratio.rolling(180, min_periods=60).apply(_percentile_rank, raw=False)

    # 箱体（20日）：带宽/中位数小于阈值即视为盘整
    mid = (out["HHV20"] + out["LLV20"]) / 2
    out["BOX20_FLAG"] = ((out["HHV20"] - out["LLV20"]) / mid.replace(0, pd.NA) < 0.03).astype(int)

    # ========== 新增高级技术指标 ==========
    
    # PSAR (抛物线转向指标)
    out = _add_psar(out, high, low, close)
    
    # Williams %R (威廉指标)
    out = _add_williams_r(out, high, low, close, period=14)
    
    # CCI (商品通道指数)
    out = _add_cci(out, high, low, close, period=20)
    
    # Stochastic RSI
    out = _add_stoch_rsi(out, close, period=14)
    
    # Ichimoku (一目均衡表)
    out = _add_ichimoku(out, high, low, close)
    
    # Chaikin Money Flow (CMF)
    out = _add_cmf(out, high, low, close, vol, period=20)
    
    # Volume Price Trend (VPT)
    out = _add_vpt(out, close, vol)
    
    # Average Directional Index Rating (ADXR)
    if "ADX14" in out.columns:
        out["ADXR14"] = (out["ADX14"] + out["ADX14"].shift(14)) / 2
    
    # True Strength Index (TSI)
    out = _add_tsi(out, close)
    
    # Commodity Channel Index Divergence
    out = _add_cci_divergence(out, close)
    
    # ========== 期货特有指标 ==========
    
    # 持仓量相关指标
    if "持仓量" in out.columns:
        out = _add_oi_indicators(out, close, vol, out["持仓量"].astype(float))
    
    # 价格-持仓量-成交量综合指标
    out = _add_futures_composite_indicators(out, close, vol, out.get("持仓量", pd.Series(dtype=float)))

    return out


def infer_trend_and_signals(df: pd.DataFrame) -> Dict:
    """基于基础指标推断技术面结论。

    返回:
    {
      direction: long|short|neutral,
      strength: 0~1,
      triggers: [...],
      volatility: {atr: float, regime: high|low},
      oi_divergence: confirm|conflict|neutral,
      notes: [...]
    }
    """
    if df.empty or df["收盘"].isna().all():
        return {
            "direction": "neutral",
            "strength": 0.0,
            "triggers": [],
            "volatility": {"atr": None, "regime": "low"},
            "oi_divergence": "neutral",
            "notes": ["无足够数据"],
        }

    last = df.iloc[-1]
    notes: List[str] = []

    # 趋势判定: EMA20 vs MA60
    direction = "neutral"
    strength = 0.0
    if pd.notna(last.get("EMA20")) and pd.notna(last.get("MA60")):
        if last["EMA20"] > last["MA60"]:
            direction = "long"
        elif last["EMA20"] < last["MA60"]:
            direction = "short"
        else:
            direction = "neutral"

        # 强度：距离占比
        base = abs(last["EMA20"] - last["MA60"]) / max(last["MA60"], 1e-9)
        strength = max(0.0, min(1.0, float(base)))

    # 触发条件样例（含BOLL与突破、MACD、RSI、带宽变化、ADX/KDJ、OBV/量、影线与缺口、箱体）
    triggers: List[str] = []
    if pd.notna(last.get("MA20")) and pd.notna(last.get("MA60")):
        if last["收盘"] > last["MA20"] > last["MA60"]:
            triggers.append("价在MA20/MA60上方，趋势延续条件")
        if last["收盘"] < last["MA20"] < last["MA60"]:
            triggers.append("价在MA20/MA60下方，空头延续条件")
    if pd.notna(last.get("BOLL_UP")) and pd.notna(last.get("BOLL_LOW")):
        if last["收盘"] > last["BOLL_UP"]:
            triggers.append("收盘上穿BOLL上轨，动能偏强/警惕回归")
        if last["收盘"] < last["BOLL_LOW"]:
            triggers.append("收盘下穿BOLL下轨，动能偏弱/警惕反弹")
    if int(last.get("BREAKOUT_LONG20", 0)) == 1:
        triggers.append("突破20日新高")
    if int(last.get("BREAKOUT_SHORT20", 0)) == 1:
        triggers.append("跌破20日新低")

    # MACD信号
    macd_val = last.get("MACD")
    macd_sig = last.get("MACD_SIGNAL")
    macd_hist = last.get("MACD_HIST")
    prev = df.iloc[-2] if len(df) >= 2 else None
    if pd.notna(macd_val) and pd.notna(macd_sig):
        if macd_val > macd_sig:
            triggers.append("MACD金叉")
        elif macd_val < macd_sig:
            triggers.append("MACD死叉")
    if prev is not None and pd.notna(macd_hist) and pd.notna(prev.get("MACD_HIST")):
        if macd_hist > prev["MACD_HIST"]:
            triggers.append("MACD柱体放大")
        elif macd_hist < prev["MACD_HIST"]:
            triggers.append("MACD柱体缩小")

    # RSI信号
    rsi_val = last.get("RSI14")
    if pd.notna(rsi_val):
        if rsi_val >= 70:
            triggers.append("RSI超买区间(>=70)")
        elif rsi_val <= 30:
            triggers.append("RSI超卖区间(<=30)")

    # BOLL带宽变化
    if prev is not None and pd.notna(last.get("BOLL_UP")) and pd.notna(last.get("BOLL_LOW")) \
            and pd.notna(prev.get("BOLL_UP")) and pd.notna(prev.get("BOLL_LOW")):
        bw_now = float(last["BOLL_UP"] - last["BOLL_LOW"]) if pd.notna(last["BOLL_UP"]) and pd.notna(last["BOLL_LOW"]) else None
        bw_prev = float(prev["BOLL_UP"] - prev["BOLL_LOW"]) if pd.notna(prev["BOLL_UP"]) and pd.notna(prev["BOLL_LOW"]) else None
        if bw_now is not None and bw_prev is not None:
            if bw_now > bw_prev * 1.05:
                triggers.append("BOLL带宽扩张")
            elif bw_now < bw_prev * 0.95:
                triggers.append("BOLL带宽收缩")

    # ADX/DMI
    adx_val = last.get("ADX14")
    pdi = last.get("PLUS_DI14")
    mdi = last.get("MINUS_DI14")
    if pd.notna(adx_val):
        if adx_val >= 25:
            triggers.append("趋势强（ADX>=25）")
        else:
            triggers.append("趋势弱（ADX<25）")
    if pd.notna(pdi) and pd.notna(mdi):
        if pdi > mdi:
            triggers.append("多头占优（+DI>-DI）")
        elif pdi < mdi:
            triggers.append("空头占优（+DI<-DI）")

    # KDJ
    kdjk = last.get("KDJ_K")
    kdjd = last.get("KDJ_D")
    kdjj = last.get("KDJ_J")
    if pd.notna(kdjk) and pd.notna(kdjd):
        if kdjk > kdjd:
            triggers.append("KDJ金叉")
        elif kdjk < kdjd:
            triggers.append("KDJ死叉")
    if pd.notna(kdjj):
        if kdjj >= 100:
            triggers.append("KDJ超买(J>=100)")
        elif kdjj <= 0:
            triggers.append("KDJ超卖(J<=0)")

    # 量能与OBV
    vol_z = last.get("VOL_Z20")
    if pd.notna(vol_z):
        if vol_z >= 2:
            triggers.append("放量（VOL_Z>=2）")
        elif vol_z <= -2:
            triggers.append("缩量（VOL_Z<=-2）")

    # 影线与缺口
    if pd.notna(last.get("UPPER_SHADOW_RATIO")) and last.get("UPPER_SHADOW_RATIO") >= 2:
        triggers.append("长上影（可能遇阻）")
    if pd.notna(last.get("LOWER_SHADOW_RATIO")) and last.get("LOWER_SHADOW_RATIO") >= 2:
        triggers.append("长下影（可能获支撑）")
    if pd.notna(last.get("GAP_PCT")):
        if last["GAP_PCT"] >= 0.01:
            triggers.append("向上跳空(>=1%)")
        elif last["GAP_PCT"] <= -0.01:
            triggers.append("向下跳空(<=-1%)")

    # 箱体
    if int(last.get("BOX20_FLAG", 0)) == 1:
        triggers.append("箱体盘整(20日)")

    # ========== 新增高级指标信号 ==========
    
    # PSAR信号
    psar_val = last.get("PSAR")
    psar_trend = last.get("PSAR_TREND")
    if pd.notna(psar_val) and pd.notna(psar_trend):
        if psar_trend == 1 and last["收盘"] > psar_val:
            triggers.append("PSAR上升趋势确认")
        elif psar_trend == -1 and last["收盘"] < psar_val:
            triggers.append("PSAR下降趋势确认")
        elif (psar_trend == 1 and last["收盘"] <= psar_val) or (psar_trend == -1 and last["收盘"] >= psar_val):
            triggers.append("PSAR趋势反转信号")
    
    # Williams %R信号
    williams_r = last.get("WILLIAMS_R14")
    if pd.notna(williams_r):
        if williams_r >= -20:
            triggers.append("Williams %R超买区间(>=-20)")
        elif williams_r <= -80:
            triggers.append("Williams %R超卖区间(<=-80)")
    
    # CCI信号
    cci_val = last.get("CCI20")
    if pd.notna(cci_val):
        if cci_val >= 100:
            triggers.append("CCI超买区间(>=100)")
        elif cci_val <= -100:
            triggers.append("CCI超卖区间(<=-100)")
        elif -100 < cci_val < 100:
            triggers.append("CCI正常区间")
    
    # Stochastic RSI信号
    stoch_k = last.get("STOCH_K")
    stoch_d = last.get("STOCH_D")
    if pd.notna(stoch_k) and pd.notna(stoch_d):
        if stoch_k > stoch_d:
            triggers.append("Stoch RSI金叉")
        elif stoch_k < stoch_d:
            triggers.append("Stoch RSI死叉")
        if stoch_k >= 80:
            triggers.append("Stoch RSI超买(>=80)")
        elif stoch_k <= 20:
            triggers.append("Stoch RSI超卖(<=20)")
    
    # Ichimoku信号
    tenkan = last.get("TENKAN_SEN")
    kijun = last.get("KIJUN_SEN")
    senkou_a = last.get("SENKOU_SPAN_A")
    senkou_b = last.get("SENKOU_SPAN_B")
    if pd.notna(tenkan) and pd.notna(kijun):
        if tenkan > kijun:
            triggers.append("一目均衡表：转换线>基准线")
        elif tenkan < kijun:
            triggers.append("一目均衡表：转换线<基准线")
    if pd.notna(senkou_a) and pd.notna(senkou_b):
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        if last["收盘"] > cloud_top:
            triggers.append("价格在云层上方")
        elif last["收盘"] < cloud_bottom:
            triggers.append("价格在云层下方")
        else:
            triggers.append("价格在云层内部")
    
    # CMF信号
    cmf_val = last.get("CMF20")
    if pd.notna(cmf_val):
        if cmf_val > 0.1:
            triggers.append("CMF强势买入压力(>0.1)")
        elif cmf_val < -0.1:
            triggers.append("CMF强势卖出压力(<-0.1)")
    
    # TSI信号
    tsi_val = last.get("TSI")
    if pd.notna(tsi_val):
        if tsi_val > 25:
            triggers.append("TSI强势上升(>25)")
        elif tsi_val < -25:
            triggers.append("TSI强势下降(<-25)")
    
    # CCI背离信号
    if int(last.get("CCI_BULL_DIV", 0)) == 1:
        triggers.append("CCI看涨背离")
    if int(last.get("CCI_BEAR_DIV", 0)) == 1:
        triggers.append("CCI看跌背离")

    # ========== 期货特有指标信号 ==========
    
    # 持仓量信号
    oi_change_pct = last.get("OI_CHANGE_PCT")
    if pd.notna(oi_change_pct):
        if oi_change_pct > 5:
            triggers.append("持仓量大幅增加(>5%)")
        elif oi_change_pct < -5:
            triggers.append("持仓量大幅减少(<-5%)")
    
    # 持仓量位置
    oi_position = last.get("OI_POSITION")
    if pd.notna(oi_position):
        if oi_position >= 80:
            triggers.append("持仓量处于高位(>=80%)")
        elif oi_position <= 20:
            triggers.append("持仓量处于低位(<=20%)")
    
    # 价格-持仓量背离
    if int(last.get("OI_PRICE_BULL_DIV", 0)) == 1:
        triggers.append("价格-持仓量看涨背离")
    if int(last.get("OI_PRICE_BEAR_DIV", 0)) == 1:
        triggers.append("价格-持仓量看跌背离")
    
    # 资金流向
    money_flow = last.get("MONEY_FLOW_MA5")
    if pd.notna(money_flow):
        if money_flow > 0.5:
            triggers.append("资金净流入(多头主导)")
        elif money_flow < -0.5:
            triggers.append("资金净流出(空头主导)")
    
    # 期货综合评分
    composite_score = last.get("FUTURES_COMPOSITE_SCORE")
    if pd.notna(composite_score):
        if composite_score > 1.5:
            triggers.append("期货综合评分强势(>1.5)")
        elif composite_score < -1.5:
            triggers.append("期货综合评分弱势(<-1.5)")
    
    # 成交量-持仓量比率
    vol_oi_ratio = last.get("VOL_OI_RATIO")
    vol_oi_ma = last.get("VOL_OI_RATIO_MA20")
    if pd.notna(vol_oi_ratio) and pd.notna(vol_oi_ma):
        if vol_oi_ratio > vol_oi_ma * 1.5:
            triggers.append("换手率异常增高")
        elif vol_oi_ratio < vol_oi_ma * 0.5:
            triggers.append("换手率异常降低")

    # 波动率状态
    atr_val = float(last.get("ATR14")) if pd.notna(last.get("ATR14")) else None
    regime = "low"
    if atr_val is not None and pd.notna(df["收盘"]).sum() >= 100:
        # 简化：ATR/收盘的分位近似
        atr_ratio = atr_val / max(float(last["收盘"]), 1e-9)
        regime = "high" if atr_ratio > 0.02 else "low"

    # OI 背离（示意）：近5日价格与 OI 同向/反向
    oi_div = "neutral"
    if "持仓量" in df.columns:
        window = 5
        price_chg = df["收盘"].astype(float).diff(window).iloc[-1]
        oi_chg = df["持仓量"].astype(float).diff(window).iloc[-1]
        if pd.notna(price_chg) and pd.notna(oi_chg):
            if price_chg > 0 and oi_chg > 0:
                oi_div = "confirm"
            elif price_chg > 0 and oi_chg < 0:
                oi_div = "conflict"
            elif price_chg < 0 and oi_chg > 0:
                oi_div = "conflict"

    return {
        "direction": direction,
        "strength": round(strength, 3),
        "triggers": triggers,
        "volatility": {"atr": atr_val, "regime": regime},
        "oi_divergence": oi_div,
        "notes": notes,
        "snapshot": {
            "close": float(last.get("收盘")) if pd.notna(last.get("收盘")) else None,
            "MA20": float(last.get("MA20")) if pd.notna(last.get("MA20")) else None,
            "MA60": float(last.get("MA60")) if pd.notna(last.get("MA60")) else None,
            "EMA20": float(last.get("EMA20")) if pd.notna(last.get("EMA20")) else None,
            "ATR14": atr_val,
            "RSI14": float(rsi_val) if pd.notna(rsi_val) else None,
            "MACD": float(macd_val) if pd.notna(macd_val) else None,
            "MACD_SIGNAL": float(macd_sig) if pd.notna(macd_sig) else None,
            "MACD_HIST": float(macd_hist) if pd.notna(macd_hist) else None,
            "BOLL_UP": float(last.get("BOLL_UP")) if pd.notna(last.get("BOLL_UP")) else None,
            "BOLL_MID": float(last.get("BOLL_MID")) if pd.notna(last.get("BOLL_MID")) else None,
            "BOLL_LOW": float(last.get("BOLL_LOW")) if pd.notna(last.get("BOLL_LOW")) else None,
            "BOLL_BW": float(last.get("BOLL_BW")) if pd.notna(last.get("BOLL_BW")) else None,
            "+DI14": float(pdi) if pd.notna(pdi) else None,
            "-DI14": float(mdi) if pd.notna(mdi) else None,
            "ADX14": float(adx_val) if pd.notna(adx_val) else None,
            "KDJ_K": float(kdjk) if pd.notna(kdjk) else None,
            "KDJ_D": float(kdjd) if pd.notna(kdjd) else None,
            "KDJ_J": float(kdjj) if pd.notna(kdjj) else None,
            "VOL_Z20": float(vol_z) if pd.notna(vol_z) else None,
            "OI_Z20": float(last.get("OI_Z20")) if pd.notna(last.get("OI_Z20")) else None,
            "VWAP20": float(last.get("VWAP20")) if pd.notna(last.get("VWAP20")) else None,
            "ATR_RATIO_PCTL180": float(last.get("ATR_RATIO_PCTL180")) if pd.notna(last.get("ATR_RATIO_PCTL180")) else None,
            "BOX20": int(last.get("BOX20_FLAG", 0)),
            # 新增高级指标
            "PSAR": float(last.get("PSAR")) if pd.notna(last.get("PSAR")) else None,
            "PSAR_TREND": int(last.get("PSAR_TREND", 0)),
            "WILLIAMS_R14": float(last.get("WILLIAMS_R14")) if pd.notna(last.get("WILLIAMS_R14")) else None,
            "CCI20": float(last.get("CCI20")) if pd.notna(last.get("CCI20")) else None,
            "STOCH_RSI": float(last.get("STOCH_RSI")) if pd.notna(last.get("STOCH_RSI")) else None,
            "STOCH_K": float(last.get("STOCH_K")) if pd.notna(last.get("STOCH_K")) else None,
            "STOCH_D": float(last.get("STOCH_D")) if pd.notna(last.get("STOCH_D")) else None,
            "TENKAN_SEN": float(last.get("TENKAN_SEN")) if pd.notna(last.get("TENKAN_SEN")) else None,
            "KIJUN_SEN": float(last.get("KIJUN_SEN")) if pd.notna(last.get("KIJUN_SEN")) else None,
            "SENKOU_SPAN_A": float(last.get("SENKOU_SPAN_A")) if pd.notna(last.get("SENKOU_SPAN_A")) else None,
            "SENKOU_SPAN_B": float(last.get("SENKOU_SPAN_B")) if pd.notna(last.get("SENKOU_SPAN_B")) else None,
            "CHIKOU_SPAN": float(last.get("CHIKOU_SPAN")) if pd.notna(last.get("CHIKOU_SPAN")) else None,
            "CMF20": float(last.get("CMF20")) if pd.notna(last.get("CMF20")) else None,
            "VPT": float(last.get("VPT")) if pd.notna(last.get("VPT")) else None,
            "TSI": float(last.get("TSI")) if pd.notna(last.get("TSI")) else None,
            "ADXR14": float(last.get("ADXR14")) if pd.notna(last.get("ADXR14")) else None,
        },
    }


def summarize_multi_timeframes(df_daily: pd.DataFrame) -> Dict:
    """输出日/周两个维度的技术摘要。"""
    if df_daily.empty:
        return {"daily": {}, "weekly": {}}

    # 日线
    d1 = add_basic_indicators(df_daily)
    d1 = add_extended_indicators(d1)
    daily_summary = infer_trend_and_signals(d1)

    # 周线
    try:
        tmp = df_daily.copy()
        tmp = tmp.dropna(subset=["时间"]).copy()
        tmp["时间"] = pd.to_datetime(tmp["时间"])
        tmp = tmp.set_index("时间")
        wk = pd.DataFrame({
            "开盘": tmp["开盘"].resample("W-FRI").first(),
            "最高": tmp["最高"].resample("W-FRI").max(),
            "最低": tmp["最低"].resample("W-FRI").min(),
            "收盘": tmp["收盘"].resample("W-FRI").last(),
            "成交量": tmp.get("成交量", pd.Series(dtype=float)).resample("W-FRI").sum(min_count=1),
            "持仓量": tmp.get("持仓量", pd.Series(dtype=float)).resample("W-FRI").last(),
        }).dropna(subset=["开盘","最高","最低","收盘"], how="any")
        wk = wk.reset_index().rename(columns={"index": "时间"})
        w1 = add_basic_indicators(wk)
        w1 = add_extended_indicators(w1)
        weekly_summary = infer_trend_and_signals(w1)
    except Exception:
        weekly_summary = {"direction": "neutral", "strength": 0.0, "triggers": [],
                          "volatility": {"atr": None, "regime": "low"}, "oi_divergence": "neutral", "notes": ["周线计算失败"]}

    return {
        "daily": daily_summary,
        "weekly": weekly_summary,
    }


