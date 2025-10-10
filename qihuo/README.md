概述

这是一个本地可运行的 AI 驱动期货分析系统的项目骨架（MVP 起步）。本阶段仅提供：
- 配置模板（`config/core.example.yaml`）
- 数据提供器函数清单（`data_providers/unified_futures_provider.py`，仅签名与说明）
- 输出 JSON 规范（`config/output_schema.json`）
- 最小 CLI（`scripts/run_daily.py`），可直接产出结构化报告骨架

目录
- `config/` 配置模板与输出规范
- `.secrets/` 本地密钥（示例文件，不入库）
- `data_providers/` 统一期货数据提供器（AkShare 封装的函数签名）
- `scripts/` CLI 入口
- `output/` 运行输出（JSON 报告）
- `.data/` 本地缓存（预留）

快速开始
1) 运行最小 CLI（无需依赖 AkShare）：
```bash
python qihuo/scripts/run_daily.py --symbol RB --date 2025-08-12
```
生成文件：`qihuo/output/report_RB_2025-08-12.json`

2) 配置（可选，下一步将启用）
- 将 `config/core.example.yaml` 复制为 `config/core.yaml`，按需修改
- 将 `.secrets/.env.example` 复制为 `.secrets/.env` 并填入 `DEEPSEEK_API_KEY`

说明
- 当前仅输出报告骨架，后续会逐步接入 AkShare 数据与大模型智能体。

