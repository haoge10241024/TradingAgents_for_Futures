# API 参考文档

## 核心模块

### FuturesAnalyzer 类

期货持仓分析的核心引擎。

#### 初始化
```python
analyzer = FuturesAnalyzer()
```

#### 主要方法

##### `analyze_retail_reverse(data, family_seats)`
家人席位反向操作策略分析

**参数：**
- `data` (dict): 各交易所持仓数据
- `family_seats` (list): 家人席位列表

**返回：**
- `dict`: 分析结果，包含信号和详细数据

**示例：**
```python
family_seats = ['永安期货', '国泰君安', '海通期货']
result = analyzer.analyze_retail_reverse(data, family_seats)
```

##### `analyze_top20_concentration(data)`
前20名持仓集中度分析

**参数：**
- `data` (dict): 各交易所持仓数据

**返回：**
- `dict`: 集中度分析结果

##### `analyze_volume_position_divergence(data)`
成交量与持仓量背离分析

**参数：**
- `data` (dict): 各交易所持仓数据

**返回：**
- `dict`: 背离分析结果

### CloudDataFetcher 类

云端数据获取器，专门处理云端环境的数据获取问题。

#### 初始化
```python
fetcher = CloudDataFetcher()
```

#### 主要方法

##### `fetch_position_data_with_auto_skip(date, skip_gfex=False)`
智能自动跳过的数据获取方法

**参数：**
- `date` (str): 日期，格式为 'YYYY-MM-DD'
- `skip_gfex` (bool): 是否跳过广期所，默认False

**返回：**
- `dict`: 各交易所持仓数据

**特性：**
- 20秒超时自动跳过广期所
- 智能重试机制
- 错误处理和恢复

##### `fetch_position_data_safe(exchange, date)`
安全的单个交易所数据获取

**参数：**
- `exchange` (str): 交易所名称
- `date` (str): 日期

**返回：**
- `pd.DataFrame`: 持仓数据

##### `test_network_connection()`
网络连接测试

**返回：**
- `dict`: 网络状态信息

### PerformanceOptimizer 类

性能优化模块，提供缓存和并发处理功能。

#### 主要方法

##### `@st.cache_data(ttl=3600)`
Streamlit缓存装饰器，1小时TTL

##### `get_cached_data(key)`
获取缓存数据

**参数：**
- `key` (str): 缓存键

**返回：**
- 缓存的数据或None

##### `set_cached_data(key, data)`
设置缓存数据

**参数：**
- `key` (str): 缓存键
- `data`: 要缓存的数据

## 配置模块

### config.py

系统配置文件，包含：

```python
# 系统版本
VERSION = "2.1"

# 交易所配置
EXCHANGES = {
    '大商所': 'dce',
    '中金所': 'cffex',
    '上期所': 'shfe',
    '郑商所': 'czce',
    '广期所': 'gfex'
}

# 家人席位默认配置
DEFAULT_FAMILY_SEATS = [
    '永安期货', '国泰君安', '海通期货',
    '中信期货', '银河期货', '华泰期货'
]

# 缓存配置
CACHE_TTL = 3600  # 1小时
FILE_CACHE_TTL = 86400  # 24小时

# 网络配置
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2
```

## 工具函数

### utils.py

#### `format_number(num)`
数字格式化函数

**参数：**
- `num` (float): 要格式化的数字

**返回：**
- `str`: 格式化后的字符串

#### `calculate_percentage_change(old_value, new_value)`
计算百分比变化

**参数：**
- `old_value` (float): 旧值
- `new_value` (float): 新值

**返回：**
- `float`: 百分比变化

#### `validate_date(date_string)`
日期验证函数

**参数：**
- `date_string` (str): 日期字符串

**返回：**
- `bool`: 是否为有效日期

## 错误处理

### 异常类型

- `NetworkError`: 网络连接错误
- `DataFetchError`: 数据获取错误
- `AnalysisError`: 分析过程错误
- `CacheError`: 缓存操作错误

### 错误处理示例

```python
try:
    data = fetcher.fetch_position_data_with_auto_skip(date)
    result = analyzer.analyze_retail_reverse(data, family_seats)
except NetworkError as e:
    st.error(f"网络连接失败: {e}")
except DataFetchError as e:
    st.warning(f"数据获取失败: {e}")
except AnalysisError as e:
    st.error(f"分析失败: {e}")
```

## 性能优化建议

1. **使用缓存**：充分利用Streamlit缓存和文件缓存
2. **并发处理**：使用ThreadPoolExecutor进行并发数据获取
3. **超时控制**：设置合理的超时时间避免长时间等待
4. **错误恢复**：实现重试机制和降级策略

## 部署配置

### Streamlit Cloud 配置

```toml
# .streamlit/config.toml
[server]
headless = true
port = 8501
enableCORS = false
enableXsrfProtection = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

### 环境要求

- Python 3.11+
- 内存: 最少512MB，推荐1GB+
- 网络: 稳定的互联网连接

## 更新日志

详见 [CHANGELOG.md](../CHANGELOG.md)

## 贡献指南

详见 [CONTRIBUTING.md](../CONTRIBUTING.md) 