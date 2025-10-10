# 配置指南

本文档详细说明如何配置商品期货AI分析系统。

## 快速配置

### 步骤1: 复制配置文件模板

```bash
# 复制JSON配置文件模板
cp 期货TradingAgents系统_配置文件.example.json 期货TradingAgents系统_配置文件.json

# 复制Python配置文件模板（如果需要）
cp config.example.py config.py
```

### 步骤2: 获取API密钥

#### DeepSeek API（必需）

1. 访问 [DeepSeek平台](https://platform.deepseek.com/)
2. 注册/登录账号
3. 进入API管理页面
4. 创建新的API密钥
5. 复制密钥（格式：`sk-xxxxxxxxxxxxxxxx`）

#### Serper API（可选）

用于新闻搜索功能，如不需要可跳过。

1. 访问 [Serper.dev](https://serper.dev/)
2. 注册账号
3. 获取API密钥
4. 新用户有免费额度

### 步骤3: 填写配置文件

打开 `期货TradingAgents系统_配置文件.json`，填入API密钥：

```json
{
  "api_settings": {
    "deepseek": {
      "api_key": "sk-你的DeepSeek密钥",
      "base_url": "https://api.deepseek.com/v1",
      "model": "deepseek-chat"
    },
    "serper": {
      "api_key": "你的Serper密钥"
    }
  }
}
```

## 详细配置说明

### API设置

```json
"api_settings": {
  "deepseek": {
    "api_key": "你的API密钥",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",           // 普通对话模型
    "reasoning_model": "deepseek-reasoner",  // 推理模型
    "max_tokens": 4000,                 // 最大生成长度
    "temperature": 0.1                  // 温度参数（越低越稳定）
  }
}
```

#### 模型选择

- **deepseek-chat**: 快速响应，适合常规分析
- **deepseek-reasoner**: 深度推理，适合复杂决策（更慢但更准确）

### 数据路径配置

```json
"paths": {
  "data_root_dir": "./qihuo/database",          // 数据库根目录
  "results_dir": "./qihuo/trading_agents_results",  // 结果输出
  "logs_dir": "./qihuo/logs",                   // 日志文件
  "cache_dir": "./qihuo/cache",                 // 缓存目录
  "config_dir": "./qihuo/config"                // 配置目录
}
```

> 使用相对路径（`./`）确保跨平台兼容性

### 系统设置

```json
"system_settings": {
  "max_concurrent_processes": 4,      // 最大并发进程数
  "default_timeout": 300,             // 默认超时（秒）
  "retry_attempts": 3,                // 失败重试次数
  "enable_progress_tracking": true,   // 启用进度追踪
  "auto_save_results": true           // 自动保存结果
}
```

#### 性能调优

- **并发数**: 根据CPU核心数调整，推荐设置为核心数-1
- **超时**: 网络慢时可增加到600秒
- **重试**: 网络不稳定时可增加到5次

### 分析模块配置

```json
"analysis_modules": {
  "technical": {
    "enabled": true,              // 是否启用
    "confidence_weight": 1.0,     // 信心度权重
    "timeout_seconds": 120        // 模块超时
  },
  "basis": {
    "enabled": true,
    "confidence_weight": 1.0,
    "timeout_seconds": 120
  }
  // ... 其他模块类似
}
```

#### 模块说明

| 模块 | 功能 | 推荐启用 |
|------|------|---------|
| technical | 技术分析 | ✓ |
| basis | 基差分析 | ✓ |
| inventory | 库存分析 | ✓ |
| positioning | 持仓分析 | ✓ |
| term_structure | 期限结构 | ✓ |
| news | 新闻分析 | 可选 |

### 辩论系统配置

```json
"debate_settings": {
  "max_debate_rounds": 2,              // 最大辩论轮数
  "max_risk_discuss_rounds": 2,        // 风险讨论轮数
  "debate_timeout_seconds": 300,       // 辩论超时
  "minimum_confidence_threshold": 0.6, // 最低信心阈值
  "enable_reasoning_mode": true        // 启用推理模式
}
```

#### 辩论深度设置

- **quick**: 1轮快速辩论（~2分钟）
- **standard**: 2轮标准辩论（~5分钟）
- **deep**: 3轮深度辩论（~10分钟）

### 日志配置

```json
"logging": {
  "level": "INFO",                    // 日志级别
  "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
  "file_logging": true,               // 文件日志
  "console_logging": true,            // 控制台日志
  "max_log_file_size_mb": 100,       // 最大日志大小
  "backup_count": 5                   // 保留日志数量
}
```

#### 日志级别

- **DEBUG**: 详细调试信息
- **INFO**: 一般信息（推荐）
- **WARNING**: 警告信息
- **ERROR**: 错误信息

### 支持的品种

系统默认支持50+个期货品种，在配置文件的 `supported_commodities` 数组中定义：

```json
"supported_commodities": [
  "RB", "HC", "I",      // 黑色系
  "CU", "AL", "ZN",     // 有色金属
  "AU", "AG",           // 贵金属
  // ... 更多品种
]
```

## 环境变量配置（可选）

除了JSON配置文件，也可以使用环境变量：

创建 `.env` 文件：

```bash
# API密钥
DEEPSEEK_API_KEY=sk-your-api-key
SERPER_API_KEY=your-serper-key

# 系统设置
MAX_CONCURRENT_PROCESSES=4
DEFAULT_TIMEOUT=300

# 数据路径
DATA_ROOT_DIR=./qihuo/database
```

## 配置验证

启动系统前，可以验证配置：

```bash
python -c "import json; config = json.load(open('期货TradingAgents系统_配置文件.json')); print('配置文件格式正确')"
```

## 安全建议

1. **不要提交API密钥到Git仓库**
   - 配置文件已在 `.gitignore` 中排除
   
2. **定期更换API密钥**
   - 建议每3个月更换一次

3. **设置API密钥权限**
   - 仅启用必要的API权限

4. **监控API使用量**
   - 定期检查API调用次数和费用

## 常见配置问题

### API密钥无效

**症状**: 提示 "API key invalid" 或 "Authentication failed"

**解决方案**:
1. 检查密钥是否正确复制（无多余空格）
2. 确认密钥尚未过期
3. 检查API账户余额

### 数据路径错误

**症状**: 提示找不到数据文件

**解决方案**:
1. 使用相对路径（`./qihuo/database`）
2. 确保目录存在
3. 检查文件系统权限

### 超时错误

**症状**: 分析过程中频繁超时

**解决方案**:
1. 增加 `default_timeout` 值
2. 减少并发数 `max_concurrent_processes`
3. 检查网络连接

### 内存不足

**症状**: 系统崩溃或变慢

**解决方案**:
1. 减少并发数
2. 禁用部分分析模块
3. 减少历史数据天数

## 高级配置

### 自定义分析参数

在 `qihuo/config/core.yaml` 中可以进行更详细的配置：

```yaml
data:
  default_lookback_days: 365    # 默认回溯天数
  rate_limit_per_sec: 4         # 每秒请求限制
  min_days_for_llm: 60          # LLM分析最少天数

risk:
  max_margin_ratio: 0.30        # 最大保证金比例
  max_position_per_symbol: 0.20 # 单品种最大仓位
```

### 数据库配置

如需使用MongoDB或Redis缓存：

```python
# config.py
MONGODB_URI = "mongodb://localhost:27017/"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
```

## 配置模板示例

### 保守型配置

适合稳定运行，降低API消耗：

```json
{
  "system_settings": {
    "max_concurrent_processes": 2
  },
  "debate_settings": {
    "max_debate_rounds": 1,
    "enable_reasoning_mode": false
  },
  "api_settings": {
    "deepseek": {
      "model": "deepseek-chat"
    }
  }
}
```

### 激进型配置

适合深度分析，追求准确性：

```json
{
  "system_settings": {
    "max_concurrent_processes": 6
  },
  "debate_settings": {
    "max_debate_rounds": 3,
    "enable_reasoning_mode": true
  },
  "api_settings": {
    "deepseek": {
      "model": "deepseek-reasoner"
    }
  }
}
```

## 配置检查清单

启动系统前，请确认：

- [ ] DeepSeek API密钥已填写
- [ ] 数据路径正确配置
- [ ] 至少启用3个分析模块
- [ ] 日志目录有写入权限
- [ ] Python版本 >= 3.8
- [ ] 所有依赖包已安装

---

更多帮助请参考 [README.md](README.md) 或提交Issue。

