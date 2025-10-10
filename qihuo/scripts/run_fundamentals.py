import argparse
import json
from pathlib import Path

# 保障可直接运行：将项目根目录加入 sys.path
import sys
_CURR = Path(__file__).resolve()
_ROOT = _CURR.parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from qihuo.analysis.fundamentals_aggregator import aggregate_fundamentals
from qihuo.scripts.run_daily import load_config  # 复用加载配置


def main() -> None:
    p = argparse.ArgumentParser(description="汇总四类基本面为LLM输入准备")
    p.add_argument("--symbol", required=True, help="品种代码，如 RB/TA/CU")
    p.add_argument("--out", default=None, help="输出文件（默认写入 qihuo/output/fundamentals_{symbol}.json）")
    p.add_argument("--try-online", action="store_true", help="若缓存缺失则尝试在线获取AkShare数据")
    p.add_argument("--start", default=None, help="YYYYMMDD，可选")
    p.add_argument("--end", default=None, help="YYYYMMDD，可选")
    args = p.parse_args()

    cfg = load_config()
    cache_dir = cfg.get("project", {}).get("cache_dir", "qihuo/.data/cache")
    out_dir = Path(cfg.get("project", {}).get("output_dir", "qihuo/output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    # 规范日期
    start = args.start
    end = args.end
    agg = aggregate_fundamentals(
        args.symbol.upper(),
        cache_dir,
        try_online=bool(args.try_online),
        start=start,
        end=end,
    )

    out_path = Path(args.out) if args.out else (out_dir / f"fundamentals_{agg['symbol']}.json")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(agg, f, ensure_ascii=False, indent=2)
    print(str(out_path))


if __name__ == "__main__":
    main()


