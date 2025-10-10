import argparse
import json
from pathlib import Path

# 保障可直接运行：将项目根目录加入 sys.path
import sys
_CURR = Path(__file__).resolve()
_ROOT = _CURR.parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from qihuo.llm.deepseek_client import DeepSeekClient
from qihuo.scripts.run_daily import load_config


def main() -> None:
    p = argparse.ArgumentParser(description="新闻分析师：调用LLM对新闻进行事件抽取与方向/置信度评估")
    p.add_argument("--symbol", required=True)
    p.add_argument("--news-file", required=True, help="qihuo/output/news_{symbol}.json")
    p.add_argument("--out", default=None, help="输出文件，默认 news_ai_{symbol}.json")
    args = p.parse_args()

    cfg = load_config()
    out_dir = Path(cfg.get("project", {}).get("output_dir", "qihuo/output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    news_path = Path(args.news_file)
    data = json.loads(news_path.read_text(encoding="utf-8"))
    items = data.get("items", [])

    ds = DeepSeekClient()
    obj, raw, err = ds.analyze_news_json_with_raw(items=items, symbol=args.symbol.upper())
    out = {
        "symbol": args.symbol.upper(),
        "ai_news": obj if obj else {"events": [], "summary": ""},
        "raw_present": bool(raw),
        "error": err,
    }

    out_path = Path(args.out) if args.out else (out_dir / f"news_ai_{args.symbol.upper()}.json")
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()


