# Trading Agents 系统 - DEBUG 调试信息控制说明

## 问题说明

系统运行时会输出大量的DEBUG调试信息，包括：
- 🐛 DEBUG: 各阶段执行状态
- DEBUG: 内容清理过程
- ================== 分隔线
- 🔍 AI生成内容预览

这些信息对开发调试有帮助，但在生产环境会影响输出可读性。

## 解决方案

系统已添加**全局DEBUG开关**，通过环境变量控制是否输出调试信息。

### 方法一：在代码中控制（推荐用于开发）

在运行脚本之前设置环境变量：

#### Windows PowerShell:
```powershell
# 关闭DEBUG（默认）
$env:TRADING_DEBUG = "0"
python 您的脚本.py

# 开启DEBUG
$env:TRADING_DEBUG = "1"
python 您的脚本.py
```

#### Windows CMD:
```cmd
# 关闭DEBUG（默认）
set TRADING_DEBUG=0
python 您的脚本.py

# 开启DEBUG
set TRADING_DEBUG=1
python 您的脚本.py
```

#### Linux/Mac:
```bash
# 关闭DEBUG（默认）
export TRADING_DEBUG=0
python 您的脚本.py

# 开启DEBUG
export TRADING_DEBUG=1
python 您的脚本.py
```

### 方法二：在Python代码中直接修改

打开 `优化版辩论风控决策系统.py` 文件，找到第34行：

```python
# 当前设置（默认关闭）
ENABLE_DEBUG = os.getenv('TRADING_DEBUG', '0') == '1'
```

修改为以下任意一种：

```python
# 永久开启DEBUG
ENABLE_DEBUG = True

# 永久关闭DEBUG
ENABLE_DEBUG = False
```

### 方法三：通过配置文件控制（推荐用于生产）

在主程序入口添加：

```python
import os

# 在导入其他模块之前设置
os.environ['TRADING_DEBUG'] = '0'  # 关闭DEBUG
# os.environ['TRADING_DEBUG'] = '1'  # 开启DEBUG

# 然后导入系统模块
from 优化版辩论风控决策系统 import OptimizedTradingAgentsSystem
```

## 验证效果

### 关闭DEBUG后（默认状态）
系统运行时**不会**输出以下内容：
- ✅ 所有 `🐛 DEBUG:` 开头的信息
- ✅ 所有 `DEBUG:` 开头的清理过程信息  
- ✅ 所有 `🔍` 开头的内容预览信息
- ✅ 所有 `==========` 分隔线

### 开启DEBUG后
系统会输出完整的调试信息，帮助您：
- 追踪各个阶段的执行状态
- 查看AI生成内容的清理过程
- 诊断可能的问题

## 快速测试

在PowerShell中运行：

```powershell
# 测试关闭DEBUG（应该看不到调试信息）
$env:TRADING_DEBUG = "0"
python 期货TradingAgents系统_专业完整版界面.py

# 测试开启DEBUG（应该看到大量调试信息）
$env:TRADING_DEBUG = "1"
python 期货TradingAgents系统_专业完整版界面.py
```

## 建议设置

- **开发/调试阶段**：设置 `TRADING_DEBUG=1`
- **生产/演示环境**：设置 `TRADING_DEBUG=0`（默认）
- **性能测试**：设置 `TRADING_DEBUG=0`

## 其他说明

- DEBUG开关只影响调试信息输出，不影响系统功能
- 关闭DEBUG可以提高系统运行速度（减少I/O操作）
- 系统的正常日志（logger）不受影响，仍会正常记录

## 技术细节

修改文件：`TradingAgents_for_Futures/优化版辩论风控决策系统.py`

关键代码：
```python
# 第30-39行
ENABLE_DEBUG = os.getenv('TRADING_DEBUG', '0') == '1'

def debug_print(*args, **kwargs):
    """全局DEBUG打印函数 - 可通过环境变量控制"""
    if ENABLE_DEBUG:
        print(*args, **kwargs)
```

所有调试输出均通过 `debug_print()` 函数，而非直接使用 `print()`。

