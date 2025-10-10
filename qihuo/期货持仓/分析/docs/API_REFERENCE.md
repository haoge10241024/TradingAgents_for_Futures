# 📚 API 参考文档

## 概述

本文档详细介绍期货持仓分析系统的核心API接口和使用方法。

## 核心模块

### 1. FuturesAnalysisEngine

主分析引擎，负责协调所有分析流程。

#### 初始化
```python
from futures_analyzer import FuturesAnalysisEngine

engine = FuturesAnalysisEngine(
    data_dir="data",           # 数据存储目录
    retail_seats=None          # 家人席位列表，None使用默认配置
)
```

#### 主要方法

##### full_analysis()
执行完整的期货持仓分析。

```python
def full_analysis(trade_date: str, progress_callback=None) -> Dict[str, Any]:
    """
    完整分析流程
    
    Args:
        trade_date: 交易日期，格式YYYYMMDD
        progress_callback: 进度回调函数，接收(message, progress)参数
    
    Returns:
        Dict: 分析结果字典
        {
            'position_analysis': {},    # 持仓分析结果
            'term_structure': [],       # 期限结构分析
            'summary': {},              # 分析总结
            'metadata': {}              # 元数据
        }
    """
```

**使用示例：**
```python
def progress_callback(message, progress):
    print(f"[{progress*100:.1f}%] {message}")

results = engine.full_analysis("20241201", progress_callback)
```

##### update_retail_seats()
更新家人席位配置。

```python
def update_retail_seats(retail_seats: List[str]):
    """
    更新家人席位配置
    
    Args:
        retail_seats: 家人席位名称列表
    """
```

### 2. CloudDataFetcher

云端数据获取器，专门处理云端环境的数据获取问题。

#### 初始化
```python
from cloud_data_fetcher import CloudDataFetcher

fetcher = CloudDataFetcher()
```

#### 主要方法

##### fetch_position_data_with_auto_skip()
获取持仓数据，自动跳过超时的交易所。

```python
def fetch_position_data_with_auto_skip(trade_date: str, progress_callback=None) -> bool:
    """
    获取持仓数据，自动跳过超时的交易所
    
    Args:
        trade_date: 交易日期，格式YYYYMMDD
        progress_callback: 进度回调函数
    
    Returns:
        bool: 是否成功获取数据
    """
```

##### fetch_price_data_with_fallback()
获取期货行情数据，包含智能自动跳过功能。

```python
def fetch_price_data_with_fallback(trade_date: str, progress_callback=None) -> pd.DataFrame:
    """
    获取期货行情数据，包含智能自动跳过功能
    
    Args:
        trade_date: 交易日期，格式YYYYMMDD
        progress_callback: 进度回调函数
    
    Returns:
        pd.DataFrame: 合并后的价格数据
    """
```

### 3. StrategyAnalyzer

策略分析器，包含所有分析策略的实现。

#### 初始化
```python
from futures_analyzer import StrategyAnalyzer

analyzer = StrategyAnalyzer(retail_seats=None)
```

#### 主要方法

##### analyze_power_change()
多空力量变化策略分析。

```python
def analyze_power_change(data: Dict[str, Any]) -> Tuple[str, str, float]:
    """
    多空力量变化策略
    
    Args:
        data: 处理后的持仓数据
    
    Returns:
        Tuple[str, str, float]: (信号, 原因, 强度)
    """
```

##### analyze_spider_web()
蜘蛛网策略分析。

```python
def analyze_spider_web(data: Dict[str, Any]) -> Tuple[str, str, float]:
    """
    蜘蛛网策略
    
    Args:
        data: 处理后的持仓数据
    
    Returns:
        Tuple[str, str, float]: (信号, 原因, 强度)
    """
```

##### analyze_retail_reverse()
家人席位反向操作策略分析。

```python
def analyze_retail_reverse(data: Dict[str, Any]) -> Tuple[str, str, float, List[Dict]]:
    """
    家人席位反向操作策略
    
    Args:
        data: 处理后的持仓数据
    
    Returns:
        Tuple[str, str, float, List[Dict]]: (信号, 原因, 强度, 席位详情)
    """
```

### 4. PerformanceOptimizer

性能优化器，提供缓存和性能优化功能。

#### 装饰器

##### @smart_cache
智能缓存装饰器。

```python
from performance_optimizer import smart_cache

@smart_cache(max_age_hours=24)
def expensive_function(param1, param2):
    # 耗时操作
    return result
```

#### 函数

##### optimize_streamlit_performance()
优化Streamlit性能。

```python
from performance_optimizer import optimize_streamlit_performance

optimize_streamlit_performance()
```

##### show_performance_metrics()
显示性能指标。

```python
from performance_optimizer import show_performance_metrics

show_performance_metrics()
```

## 数据结构

### 分析结果结构

```python
{
    'position_analysis': {
        'contract_name': {
            'strategies': {
                '多空力量变化策略': {
                    'signal': 'str',      # 看多/看空/中性
                    'reason': 'str',      # 分析原因
                    'strength': 'float'   # 信号强度
                },
                '蜘蛛网策略': {...},
                '家人席位反向操作策略': {
                    'signal': 'str',
                    'reason': 'str', 
                    'strength': 'float',
                    'seat_details': 'List[Dict]'  # 席位详情
                }
            },
            'raw_data': 'pd.DataFrame',   # 原始数据
            'summary_data': {             # 汇总数据
                'total_long': 'int',
                'total_short': 'int',
                'total_long_chg': 'int',
                'total_short_chg': 'int'
            }
        }
    },
    'term_structure': [
        ('品种', '结构类型', ['合约列表'], [价格列表])
    ],
    'summary': {
        'strategy_signals': {},       # 各策略信号汇总
        'signal_resonance': {},       # 信号共振分析
        'statistics': {}              # 统计信息
    },
    'metadata': {
        'trade_date': 'str',
        'analysis_time': 'str',
        'include_term_structure': 'bool',
        'retail_seats': 'List[str]'
    }
}
```

### 席位详情结构

```python
{
    'seat_name': 'str',      # 席位名称
    'long_chg': 'float',     # 多单变化
    'short_chg': 'float',    # 空单变化
    'long_pos': 'float',     # 多单持仓
    'short_pos': 'float'     # 空单持仓
}
```

## 配置选项

### 系统配置 (config.py)

```python
STRATEGY_CONFIG = {
    "家人席位反向操作策略": {
        "default_retail_seats": [
            "永安期货", "国泰君安", "海通期货",
            "申银万国", "华泰期货", "中信期货"
        ]
    }
}

STREAMLIT_CONFIG = {
    "page_title": "期货持仓分析系统",
    "page_icon": "📊",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

CACHE_CONFIG = {
    "ttl": 3600,              # 缓存时间（秒）
    "max_entries": 100,       # 最大缓存条目
    "persist": True           # 是否持久化
}
```

### 超时配置

```python
TIMEOUT_CONFIG = {
    "大商所": 30,
    "中金所": 30,
    "郑商所": 30,
    "上期所": 30,
    "广期所": 15    # 更短超时，智能跳过
}
```

## 错误处理

### 异常类型

#### DataFetchError
数据获取失败异常。

```python
class DataFetchError(Exception):
    """数据获取失败异常"""
    pass
```

#### TimeoutError
超时异常。

```python
class TimeoutError(Exception):
    """超时异常"""
    pass
```

#### AnalysisError
分析失败异常。

```python
class AnalysisError(Exception):
    """分析失败异常"""
    pass
```

### 错误处理示例

```python
try:
    results = engine.full_analysis(trade_date)
except DataFetchError as e:
    print(f"数据获取失败: {e}")
except TimeoutError as e:
    print(f"操作超时: {e}")
except AnalysisError as e:
    print(f"分析失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

## 最佳实践

### 1. 进度回调使用

```python
def progress_callback(message, progress):
    """标准进度回调函数"""
    print(f"[{progress*100:.1f}%] {message}")
    
    # 在Streamlit中使用
    if 'streamlit' in sys.modules:
        import streamlit as st
        st.progress(progress)
        st.text(message)
```

### 2. 缓存优化

```python
# 使用智能缓存
@smart_cache(max_age_hours=6)
def get_market_data(date):
    return expensive_api_call(date)

# 手动缓存管理
from performance_optimizer import optimizer
optimizer.clear_old_cache(max_age_days=7)
```

### 3. 错误恢复

```python
def robust_analysis(trade_date, max_retries=3):
    """带重试的分析函数"""
    for attempt in range(max_retries):
        try:
            return engine.full_analysis(trade_date)
        except (DataFetchError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            print(f"尝试 {attempt + 1} 失败，重试中...")
            time.sleep(5)
```

### 4. 内存管理

```python
# 大数据处理时的内存优化
def process_large_dataset(data):
    # 分块处理
    chunk_size = 1000
    results = []
    
    for i in range(0, len(data), chunk_size):
        chunk = data[i:i+chunk_size]
        result = process_chunk(chunk)
        results.append(result)
        
        # 清理中间变量
        del chunk
        
    return pd.concat(results, ignore_index=True)
```

## 扩展开发

### 添加新策略

```python
class CustomStrategy:
    """自定义策略示例"""
    
    def analyze_custom_strategy(self, data: Dict[str, Any]) -> Tuple[str, str, float]:
        """
        自定义策略分析
        
        Args:
            data: 处理后的持仓数据
            
        Returns:
            Tuple[str, str, float]: (信号, 原因, 强度)
        """
        # 实现自定义分析逻辑
        signal = "看多"  # 或 "看空", "中性"
        reason = "自定义分析原因"
        strength = 0.8
        
        return signal, reason, strength

# 集成到分析器
def extend_analyzer():
    analyzer = StrategyAnalyzer()
    analyzer.custom_strategy = CustomStrategy()
    return analyzer
```

### 添加新数据源

```python
class CustomDataSource:
    """自定义数据源"""
    
    def fetch_data(self, trade_date: str) -> pd.DataFrame:
        """获取自定义数据源数据"""
        # 实现数据获取逻辑
        return pd.DataFrame()

# 集成到数据管理器
def extend_data_manager():
    manager = FuturesDataManager()
    manager.custom_source = CustomDataSource()
    return manager
```

## 版本兼容性

### v2.1 API变更

- 新增：`fetch_position_data_with_auto_skip()` 方法
- 新增：增强超时处理机制
- 改进：错误处理和用户提示
- 兼容：所有v2.0 API保持兼容

### 迁移指南

从v2.0迁移到v2.1：

```python
# v2.0 代码
fetcher.fetch_position_data_skip_gfex(date)

# v2.1 推荐代码
fetcher.fetch_position_data_with_auto_skip(date)
```

## 性能调优

### 缓存策略

```python
# 针对不同数据类型的缓存策略
@smart_cache(max_age_hours=24)  # 持仓数据：24小时
def get_position_data(date):
    pass

@smart_cache(max_age_hours=6)   # 价格数据：6小时
def get_price_data(date):
    pass

@smart_cache(max_age_hours=1)   # 实时数据：1小时
def get_realtime_data():
    pass
```

### 并发优化

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_analysis(dates):
    """并行分析多个日期"""
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(engine.full_analysis, date) for date in dates]
        results = [f.result() for f in futures]
    return results
```

---

**📚 API参考文档 v2.1**  
**更新日期**: 2024-12-01  
**维护者**: 7haoge 