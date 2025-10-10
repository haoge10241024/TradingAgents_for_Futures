"""
统一期货数据提供器（函数签名与说明）

目标：在不依赖具体数据源实现的情况下，先约定可供智能体调用的函数接口。
后续将以 AkShare 为主数据源进行填充与清洗，同时加入缓存、限速与重试。
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ProviderConfig:
    cache_dir: str = "qihuo/.data/cache"
    rate_limit_per_sec: int = 4
    retries: int = 3
    timeout_sec: int = 30
    use_cache: bool = True


class UnifiedFuturesProvider:
    """统一期货数据提供器（仅签名）。

    设计要点：
    - 行情与 OI：映射 ak.futures_hist_em
    - 基差与现货：映射 ak.futures_spot_price / _previous / _daily
    - 期限结构与展期：映射 ak.get_roll_yield_bar / ak.get_roll_yield
    - 仓单与库存：映射 ak.futures_*_warehouse_receipt / ak.get_receipt / ak.futures_inventory_em
    - 席位与成交：映射 ak.get_*_rank_table / ak.futures_hold_pos_sina
    - 成本参数：映射 ak.futures_comm_info
    - 资讯文本：映射 ak.futures_news_shmet
    """

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self.config = config or ProviderConfig()

    # ========== 行情与 OI ==========
    def get_ohlcv(
        self,
        symbol: str,
        start: str,
        end: str,
        freq: str = "1d",
        continuous: bool = True,
    ) -> "Any":
        """获取连续合约 K 线与持仓量（最小实现）。
        期望列：时间/开盘/最高/最低/收盘/成交量/持仓量 等。
        对应：ak.futures_hist_em(symbol="螺纹钢主连" 等, period)
        """
        try:
            import pandas as pd  # type: ignore
        except Exception as e:
            # 未安装 pandas
            raise NotImplementedError(str(e))

        # 简易映射：英文品种代码 -> 中文主连标识
        mapping = {
            "RB": "螺纹钢主连",
            "HC": "热卷主连",
            "CU": "沪铜主连",
            "AL": "沪铝主连",
            "ZN": "沪锌主连",
            "NI": "沪镍主连",
            "SN": "沪锡主连",
            "AG": "沪银主连",
            "AU": "沪金主连",
            "IF": "沪深300主连",
            "IH": "上证50主连",
            "IC": "中证500主连",
            "IM": "中证1000主连",
            "SS": "不锈钢主连",
            "I": "铁矿主连",
            "JM": "焦煤主连",
            "J": "焦炭主连",
            "TA": "PTA主连",
            "MA": "甲醇主连",
            "RU": "橡胶主连",
            "FG": "玻璃主连",
            "LH": "生猪主连",
            "SC": "原油主连",
        }

        zh = mapping.get(symbol.upper())
        if not zh:
            # 兜底：直接使用原 symbol（若调用者传入已是中文）
            zh = symbol

        period = {"1d": "daily", "1w": "weekly", "1mo": "monthly"}.get(freq, "daily")

        # 先尝试读取本地缓存
        from pathlib import Path

        cache_dir = Path(self.config.cache_dir)
        csv_path = cache_dir / f"ohlcv_{symbol.upper()}.csv"

        df = None
        if csv_path.exists():
            try:
                df = pd.read_csv(csv_path)
            except Exception:
                df = None

        # 若本地无缓存则尝试在线获取
        if df is None or len(df) == 0:
            try:
                import akshare as ak  # type: ignore
                df = ak.futures_hist_em(symbol=zh, period=period)
            except Exception as e:
                raise NotImplementedError(f"在线获取失败且本地无缓存: {e}")

        if df is None or len(df) == 0:
            return pd.DataFrame()

        # 选择并规范字段
        # 典型列：时间 开盘 最高 最低 收盘 涨跌 涨跌幅 成交量 成交额 持仓量
        need = ["时间", "开盘", "最高", "最低", "收盘", "成交量", "持仓量"]
        for col in need:
            if col not in df.columns:
                # 若缺失则补空列
                df[col] = pd.NA

        df = df[need].copy()
        # 转换类型
        for col in ["开盘", "最高", "最低", "收盘", "成交量", "持仓量"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # 过滤时间范围并按时间排序
        try:
            df["时间"] = pd.to_datetime(df["时间"])  # 原为字符串 YYYY-MM-DD
            mask = (df["时间"] >= pd.to_datetime(start)) & (df["时间"] <= pd.to_datetime(end))
            df = df.loc[mask].sort_values("时间").reset_index(drop=True)
        except Exception:
            pass

        return df

    # ========== 基差与现货 ==========
    def get_basis_daily(
        self, vars_list: List[str], start: str, end: str
    ) -> "Any":
        """获取一段时间的基差数据（占位）。
        对应：ak.futures_spot_price_daily(start_day, end_day, vars_list)
        """
        raise NotImplementedError

    def get_spot_on(self, date: str) -> "Any":
        """获取指定交易日的现货/近月/主力与基差（占位）。
        对应：ak.futures_spot_price(date)
        """
        raise NotImplementedError

    # ========== 期限结构与展期 ==========
    def get_roll_yield_curve(self, var: str, date: str) -> "Any":
        """获取某品种在某日的展期结构/价差组成（占位）。
        对应：ak.get_roll_yield_bar(type_method="symbol", var, date)
        """
        raise NotImplementedError

    def get_roll_yield_range(self, var: str, start: str, end: str) -> "Any":
        """获取一段时间的主次合约价差/展期收益率（占位）。
        对应：ak.get_roll_yield_bar(type_method="date", var, start_day, end_day)
        """
        raise NotImplementedError

    # ========== 仓单与库存 ==========
    def get_warehouse_receipt(self, exchange: str, date: str) -> "Any":
        """获取某交易所某日仓单（占位）。
        对应：ak.futures_*_warehouse_receipt(date) 或 ak.get_receipt(...)
        """
        raise NotImplementedError

    def get_inventory_series(self, series_name: str) -> "Any":
        """获取库存或注册仓单等时序（占位）。
        对应：ak.futures_inventory_em(symbol)
        """
        raise NotImplementedError

    # ========== 席位与成交 ==========
    def get_position_ranks(self, exchange: str, date: str, product: Optional[str] = None) -> "Any":
        """获取会员持仓/成交排名（占位）。
        对应：ak.get_czce_rank_table / get_dce_rank_table / get_shfe_rank_table / get_cffex_rank_table 等
        """
        raise NotImplementedError

    def get_member_holds(self, contract: str, date: str, side: str = "多单持仓") -> "Any":
        """获取会员多/空/成交量持仓（占位）。
        对应：ak.futures_hold_pos_sina(symbol, contract, date)
        """
        raise NotImplementedError

    # ========== 成本参数 ==========
    def get_fee_margin_all(self) -> "Any":
        """获取全市场合约手续费与保证金（占位）。
        对应：ak.futures_comm_info(symbol="所有")
        """
        raise NotImplementedError

    # ========== 资讯文本 ==========
    def get_news_shmet(self, symbol: str, start: Optional[str] = None, end: Optional[str] = None) -> "Any":
        """获取上金所相关资讯（占位）。
        对应：ak.futures_news_shmet(symbol)
        """
        raise NotImplementedError


def get_provider(config: Optional[Dict[str, Any]] = None) -> UnifiedFuturesProvider:
    """工厂方法：返回数据提供器实例（占位）。"""
    pcfg = ProviderConfig(**config) if config else ProviderConfig()
    return UnifiedFuturesProvider(pcfg)


