# 🔧 API参考文档

本文档提供期货持仓分析系统的详细API参考。

## 📋 目录

- [核心模块](#核心模块)
- [数据获取模块](#数据获取模块)
- [分析引擎](#分析引擎)
- [策略分析器](#策略分析器)
- [配置管理](#配置管理)
- [工具函数](#工具函数)

---

## 核心模块

### StreamlitApp

主应用类，负责Web界面和用户交互。

```python
class StreamlitApp:
    def __init__(self):
        """初始化Streamlit应用"""
        
    def run(self):
        """运行应用"""
        
    def render_sidebar(self):
        """渲染侧边栏"""
        
    def render_main_content(self):
        """渲染主要内容"""
```

#### 方法详解

##### `run()`
启动Streamlit应用的主入口点。

**返回值**: None

**示例**:
```python
app = StreamlitApp()
app.run()
```

---

## 数据获取模块

### CloudDataFetcher

云端数据获取器，专门处理云端环境的数据获取问题。

```python
class CloudDataFetcher:
    def __init__(self):
        """初始化云端数据获取器"""
        
    def fetch_position_data_with_auto_skip(self, trade_date: str, progress_callback=None) -> bool:
        """获取持仓数据，自动跳过超时的交易所"""
        
    def safe_akshare_call(self, func, *args, **kwargs):
        """安全的akshare调用，包含重试机制和超时控制"""
```

#### 方法详解

##### `fetch_position_data_with_auto_skip(trade_date, progress_callback=None)`
获取持仓数据，具备智能自动跳过功能。

**参数**:
- `trade_date` (str): 交易日期，格式为YYYYMMDD
- `progress_callback` (callable, optional): 进度回调函数

**返回值**: bool - 获取成功返回True，失败返回False

**示例**:
```python
fetcher = CloudDataFetcher()
success = fetcher.fetch_position_data_with_auto_skip("20240530")
if success:
    print("数据获取成功")
```

##### `safe_akshare_call(func, *args, **kwargs)`
安全的akshare调用包装器。

**参数**:
- `func` (callable): 要调用的akshare函数
- `*args`: 位置参数
- `**kwargs`: 关键字参数

**返回值**: 函数执行结果或None（失败时）

**示例**:
```python
import akshare as ak
fetcher = CloudDataFetcher()
data = fetcher.safe_akshare_call(ak.futures_dce_position_rank, date="20240530")
```

---

## 分析引擎

### FuturesAnalysisEngine

核心分析引擎，负责协调各种分析策略。

```python
class FuturesAnalysisEngine:
    def __init__(self, data_dir: str, retail_seats: List[str]):
        """初始化分析引擎"""
        
    def full_analysis(self, trade_date: str, progress_callback=None) -> Dict:
        """执行完整分析"""
        
    def update_retail_seats(self, retail_seats: List[str]):
        """更新家人席位配置"""
```

#### 方法详解

##### `full_analysis(trade_date, progress_callback=None)`
执行完整的期货持仓分析。

**参数**:
- `trade_date` (str): 交易日期，格式为YYYYMMDD
- `progress_callback` (callable, optional): 进度回调函数

**返回值**: Dict - 包含所有分析结果的字典

**返回值结构**:
```python
{
    'metadata': {
        'trade_date': str,
        'analysis_time': str,
        'retail_seats': List[str]
    },
    'position_analysis': Dict,  # 合约级别的分析结果
    'summary': {
        'statistics': Dict,     # 统计信息
        'strategy_signals': Dict,  # 各策略信号
        'signal_resonance': Dict   # 信号共振分析
    },
    'term_structure': List      # 期限结构分析
}
```

**示例**:
```python
engine = FuturesAnalysisEngine("data", ["东方财富", "平安期货"])
results = engine.full_analysis("20240530")
print(f"分析了 {results['summary']['statistics']['total_contracts']} 个合约")
```

---

## 策略分析器

### StrategyAnalyzer

策略分析器，实现各种分析策略。

```python
class StrategyAnalyzer:
    def __init__(self, retail_seats: List[str]):
        """初始化策略分析器"""
        
    def analyze_power_change(self, df: pd.DataFrame) -> Dict:
        """多空力量变化策略"""
        
    def analyze_spider_web(self, df: pd.DataFrame) -> Dict:
        """蜘蛛网策略"""
        
    def analyze_retail_reverse(self, df: pd.DataFrame) -> Dict:
        """家人席位反向操作策略"""
```

#### 方法详解

##### `analyze_power_change(df)`
多空力量变化策略分析。

**参数**:
- `df` (pd.DataFrame): 持仓数据DataFrame

**返回值**: Dict - 分析结果

**返回值结构**:
```python
{
    'signal': str,      # '看多', '看空', '中性'
    'strength': float,  # 信号强度
    'reason': str       # 信号原因
}
```

##### `analyze_spider_web(df)`
蜘蛛网策略分析。

**参数**:
- `df` (pd.DataFrame): 持仓数据DataFrame

**返回值**: Dict - 分析结果，结构同上

##### `analyze_retail_reverse(df)`
家人席位反向操作策略分析。

**参数**:
- `df` (pd.DataFrame): 持仓数据DataFrame

**返回值**: Dict - 分析结果，包含额外的seat_details字段

---

## 配置管理

### 配置常量

系统配置定义在`config.py`中：

```python
# 系统配置
SYSTEM_CONFIG = {
    "app_name": str,
    "version": str,
    "author": str,
    "email": str
}

# 策略配置
STRATEGY_CONFIG = {
    "多空力量变化策略": Dict,
    "蜘蛛网策略": Dict,
    "家人席位反向操作策略": Dict
}

# 显示配置
DISPLAY_CONFIG = {
    "max_signals_per_strategy": int,
    "max_contracts_in_chart": int
}
```

---

## 工具函数

### 日期验证

```python
def validate_trade_date(date_str: str) -> bool:
    """验证交易日期格式"""
    
def get_recent_trade_date() -> str:
    """获取最近的交易日期"""
```

### 数据处理

```python
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """清理数据"""
    
def calculate_position_changes(df: pd.DataFrame) -> pd.DataFrame:
    """计算持仓变化"""
```

---

## 🔧 使用示例

### 基本使用

```python
from futures_analyzer import FuturesAnalysisEngine
from cloud_data_fetcher import CloudDataFetcher

# 1. 获取数据
fetcher = CloudDataFetcher()
success = fetcher.fetch_position_data_with_auto_skip("20240530")

if success:
    # 2. 分析数据
    engine = FuturesAnalysisEngine("data", ["东方财富", "平安期货"])
    results = engine.full_analysis("20240530")
    
    # 3. 查看结果
    print(f"总合约数: {results['summary']['statistics']['total_contracts']}")
    print(f"看多信号: {results['summary']['statistics']['total_long_signals']}")
    print(f"看空信号: {results['summary']['statistics']['total_short_signals']}")
```

### 自定义进度回调

```python
def my_progress_callback(message, progress):
    print(f"进度: {progress:.1%} - {message}")

results = engine.full_analysis("20240530", my_progress_callback)
```

### 策略单独使用

```python
from futures_analyzer import StrategyAnalyzer
import pandas as pd

# 加载数据
df = pd.read_excel("data/大商所持仓.xlsx", sheet_name="螺纹钢2501")

# 分析策略
analyzer = StrategyAnalyzer(["东方财富", "平安期货"])
result = analyzer.analyze_power_change(df)

print(f"信号: {result['signal']}")
print(f"强度: {result['strength']:.4f}")
print(f"原因: {result['reason']}")
```

---

## 🐛 错误处理

### 常见异常

```python
class FuturesAnalysisError(Exception):
    """期货分析基础异常"""
    pass

class DataFetchError(FuturesAnalysisError):
    """数据获取异常"""
    pass

class AnalysisError(FuturesAnalysisError):
    """分析过程异常"""
    pass
```

### 异常处理示例

```python
try:
    results = engine.full_analysis("20240530")
except DataFetchError as e:
    print(f"数据获取失败: {e}")
except AnalysisError as e:
    print(f"分析失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

---

## 📊 数据结构

### 持仓数据结构

```python
# 标准持仓数据DataFrame结构
columns = [
    'long_party_name',          # 多单席位名称
    'long_open_interest',       # 多单持仓量
    'long_open_interest_chg',   # 多单持仓变化
    'short_party_name',         # 空单席位名称
    'short_open_interest',      # 空单持仓量
    'short_open_interest_chg'   # 空单持仓变化
]
```

### 分析结果结构

```python
# 完整分析结果结构
analysis_result = {
    'metadata': {
        'trade_date': '20240530',
        'analysis_time': '2024-05-30 15:30:00',
        'retail_seats': ['东方财富', '平安期货', '徽商期货']
    },
    'position_analysis': {
        '螺纹钢2501': {
            'strategies': {
                '多空力量变化策略': {
                    'signal': '看多',
                    'strength': 0.1234,
                    'reason': '多单增加1000手，空单减少500手'
                }
            },
            'raw_data': pd.DataFrame,
            'summary_data': {
                'total_long': 50000,
                'total_short': 45000,
                'total_long_chg': 1000,
                'total_short_chg': -500
            }
        }
    },
    'summary': {
        'statistics': {
            'total_contracts': 100,
            'total_long_signals': 25,
            'total_short_signals': 30
        },
        'strategy_signals': {
            '多空力量变化策略': {
                'long': [{'contract': '螺纹钢2501', 'strength': 0.1234}],
                'short': []
            }
        }
    }
}
```

---

## 🔗 相关链接

- [快速开始指南](QUICK_START_GUIDE.md)
- [自动跳过功能详解](AUTO_SKIP_FEATURES.md)
- [常见问题解答](FAQ.md)
- [贡献指南](../CONTRIBUTING.md)

---

**📧 技术支持：953534947@qq.com** 