# 🔧 故障排除指南

## 🚨 紧急问题快速解决

### 🔥 系统完全无法启动
```bash
# 1. 检查Python版本
python --version  # 应该是3.8+

# 2. 重新安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 3. 清理缓存
rm -rf __pycache__/
rm -rf cache/

# 4. 重新启动
streamlit run streamlit_app.py
```

### 🔥 系统卡死不响应
```bash
# 1. 强制停止
Ctrl + C  # 或关闭终端

# 2. 清理进程
# Windows
taskkill /f /im python.exe

# Linux/Mac
pkill -f streamlit

# 3. 重新启动
streamlit run streamlit_app.py --server.port 8502
```

### 🔥 数据获取完全失败
```bash
# 1. 检查网络连接
ping www.baidu.com

# 2. 测试akshare
python -c "import akshare as ak; print(ak.__version__)"

# 3. 使用演示模式
# 在界面中选择"演示模式"
```

---

## 📊 数据获取问题

### 问题1: "akshare导入失败"
**错误信息**: `ModuleNotFoundError: No module named 'akshare'`

**解决方案**:
```bash
# 方法1: 重新安装akshare
pip uninstall akshare
pip install akshare

# 方法2: 使用国内镜像
pip install akshare -i https://pypi.tuna.tsinghua.edu.cn/simple/

# 方法3: 指定版本
pip install akshare>=1.13.0
```

### 问题2: "网络连接超时"
**错误信息**: `requests.exceptions.ConnectTimeout`

**解决方案**:
```python
# 1. 检查网络连接
import requests
try:
    response = requests.get('https://www.baidu.com', timeout=10)
    print("网络连接正常")
except:
    print("网络连接异常")

# 2. 配置代理（如果需要）
import os
os.environ['HTTP_PROXY'] = 'http://your-proxy:port'
os.environ['HTTPS_PROXY'] = 'https://your-proxy:port'

# 3. 增加超时时间
# 在cloud_data_fetcher.py中修改timeout参数
```

### 问题3: "广期所数据获取卡顿"
**现象**: 系统在广期所处停留很久

**解决方案**:
- ✅ **v2.1版本已自动解决**: 15秒自动跳过
- 🔧 **手动解决**: 重启应用，系统会自动跳过
- ⚙️ **配置调整**: 可以修改超时时间

```python
# 在cloud_data_fetcher.py中调整
{"market": "GFEX", "name": "广期所", "timeout": 10}  # 改为10秒
```

### 问题4: "数据格式错误"
**错误信息**: `KeyError: 'long_party_name'`

**解决方案**:
```python
# 1. 检查数据结构
print(df.columns.tolist())

# 2. 清理数据缓存
import os
if os.path.exists('data/'):
    import shutil
    shutil.rmtree('data/')

# 3. 重新获取数据
```

---

## 🖥️ 系统环境问题

### 问题5: "Python版本不兼容"
**错误信息**: `SyntaxError: invalid syntax`

**解决方案**:
```bash
# 1. 检查Python版本
python --version
python3 --version

# 2. 使用正确的Python版本
python3.11 -m pip install -r requirements.txt
python3.11 -m streamlit run streamlit_app.py

# 3. 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 问题6: "内存不足"
**错误信息**: `MemoryError` 或系统变慢

**解决方案**:
```python
# 1. 检查内存使用
import psutil
print(f"内存使用: {psutil.virtual_memory().percent}%")

# 2. 优化内存使用
# 在streamlit_app.py中添加
import gc
gc.collect()  # 强制垃圾回收

# 3. 分批处理数据
def process_in_chunks(data, chunk_size=1000):
    for i in range(0, len(data), chunk_size):
        yield data[i:i+chunk_size]

# 4. 清理缓存
st.cache_data.clear()
```

### 问题7: "端口被占用"
**错误信息**: `OSError: [Errno 48] Address already in use`

**解决方案**:
```bash
# 1. 查找占用端口的进程
# Windows
netstat -ano | findstr :8501
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8501
kill -9 <PID>

# 2. 使用其他端口
streamlit run streamlit_app.py --server.port 8502

# 3. 配置文件指定端口
# 在.streamlit/config.toml中添加
[server]
port = 8502
```

---

## 🎨 界面显示问题

### 问题8: "页面显示异常"
**现象**: 布局混乱、组件重叠

**解决方案**:
```python
# 1. 清理浏览器缓存
# Ctrl+Shift+R 强制刷新

# 2. 重置Streamlit缓存
streamlit cache clear

# 3. 检查浏览器兼容性
# 推荐使用Chrome、Firefox、Edge最新版本

# 4. 禁用浏览器扩展
# 尝试在无痕模式下运行
```

### 问题9: "图表不显示"
**现象**: 图表区域空白

**解决方案**:
```python
# 1. 检查plotly版本
import plotly
print(plotly.__version__)

# 2. 重新安装plotly
pip uninstall plotly
pip install plotly>=5.0.0

# 3. 检查数据
print(df.head())
print(df.dtypes)

# 4. 简化图表配置
fig = px.line(df, x='date', y='value', title='简单图表')
st.plotly_chart(fig, use_container_width=True)
```

### 问题10: "中文显示乱码"
**现象**: 中文字符显示为方块或问号

**解决方案**:
```python
# 1. 设置编码
import sys
print(sys.getdefaultencoding())

# 2. 在文件开头添加
# -*- coding: utf-8 -*-

# 3. 设置matplotlib中文字体
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 4. 检查数据编码
df = pd.read_excel(file, encoding='utf-8')
```

---

## ⚡ 性能问题

### 问题11: "运行速度很慢"
**现象**: 分析需要很长时间

**解决方案**:
```python
# 1. 启用缓存
@st.cache_data(ttl=3600)
def expensive_function():
    # 耗时操作
    pass

# 2. 优化数据处理
# 使用向量化操作替代循环
df['new_col'] = df['col1'] * df['col2']  # 好
# for i in range(len(df)): df.loc[i, 'new_col'] = ...  # 差

# 3. 减少数据量
df_sample = df.sample(n=1000)  # 采样

# 4. 并行处理
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=2) as executor:
    futures = [executor.submit(process_data, chunk) for chunk in chunks]
```

### 问题12: "缓存问题"
**现象**: 数据不更新或缓存过大

**解决方案**:
```python
# 1. 手动清理缓存
st.cache_data.clear()

# 2. 设置缓存TTL
@st.cache_data(ttl=600)  # 10分钟过期
def get_data():
    pass

# 3. 条件性缓存
@st.cache_data
def get_data(date, _force_refresh=False):
    if _force_refresh:
        st.cache_data.clear()
    return fetch_data(date)

# 4. 清理文件缓存
import shutil
if os.path.exists('cache/'):
    shutil.rmtree('cache/')
```

---

## 🚀 部署问题

### 问题13: "Streamlit Cloud部署失败"
**错误信息**: 各种部署错误

**解决方案**:
```yaml
# 1. 检查requirements.txt
streamlit
pandas
numpy
plotly
akshare
openpyxl
xlsxwriter
requests
python-dateutil
pytz
urllib3

# 2. 检查.python-version
3.11

# 3. 检查文件结构
your-repo/
├── streamlit_app.py
├── requirements.txt
├── .python-version
├── .streamlit/
│   └── config.toml
└── ...

# 4. 检查GitHub仓库
# 确保所有文件都已推送到GitHub
git add .
git commit -m "Update files"
git push origin main
```

### 问题14: "云端运行超时"
**现象**: 云端环境运行时间过长

**解决方案**:
```python
# 1. 使用v2.1版本的智能跳过功能
# 系统会自动处理超时问题

# 2. 优化代码
# 减少不必要的计算
# 使用缓存机制

# 3. 配置超时
# 在cloud_data_fetcher.py中调整超时设置
TIMEOUT_CONFIG = {
    "大商所": 20,
    "中金所": 20,
    "郑商所": 20,
    "上期所": 20,
    "广期所": 10  # 更短的超时
}
```

### 问题15: "依赖包冲突"
**错误信息**: `ERROR: pip's dependency resolver does not currently consider all the ways that packages can conflict`

**解决方案**:
```bash
# 1. 简化requirements.txt
# 移除版本限制，只保留包名
streamlit
pandas
numpy
plotly
akshare

# 2. 使用pip-tools
pip install pip-tools
pip-compile requirements.in
pip-sync requirements.txt

# 3. 创建新的虚拟环境
python -m venv fresh_env
source fresh_env/bin/activate
pip install -r requirements.txt
```

---

## 🔍 调试技巧

### 启用调试模式
```python
# 1. 在代码中添加调试信息
import logging
logging.basicConfig(level=logging.DEBUG)

# 2. 使用st.write调试
st.write("调试信息:", variable)

# 3. 使用try-except捕获错误
try:
    result = risky_operation()
except Exception as e:
    st.error(f"错误: {e}")
    st.write("详细错误信息:", str(e))

# 4. 检查数据结构
st.write("数据形状:", df.shape)
st.write("数据类型:", df.dtypes)
st.write("数据预览:", df.head())
```

### 性能分析
```python
# 1. 时间测量
import time
start_time = time.time()
# 执行操作
end_time = time.time()
st.write(f"执行时间: {end_time - start_time:.2f}秒")

# 2. 内存监控
import psutil
process = psutil.Process()
memory_info = process.memory_info()
st.write(f"内存使用: {memory_info.rss / 1024 / 1024:.2f} MB")

# 3. 缓存命中率
@st.cache_data
def cached_function():
    st.write("缓存未命中，重新计算")
    return expensive_computation()
```

### 日志记录
```python
# 1. 配置日志
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# 2. 记录关键操作
logger = logging.getLogger(__name__)
logger.info("开始数据获取")
logger.warning("广期所数据获取超时")
logger.error("分析失败", exc_info=True)
```

---

## 📞 获取帮助

### 收集错误信息
在报告问题时，请提供以下信息：

```python
# 1. 系统信息
import platform
import sys
print(f"操作系统: {platform.system()} {platform.release()}")
print(f"Python版本: {sys.version}")

# 2. 包版本信息
import streamlit
import pandas
import numpy
import plotly
print(f"Streamlit: {streamlit.__version__}")
print(f"Pandas: {pandas.__version__}")
print(f"NumPy: {numpy.__version__}")
print(f"Plotly: {plotly.__version__}")

# 3. 错误堆栈
import traceback
try:
    # 问题代码
    pass
except Exception as e:
    print("错误信息:", str(e))
    print("错误堆栈:")
    traceback.print_exc()
```

### 联系方式
- 📧 **邮箱**: 953534947@qq.com
- 🐛 **GitHub Issues**: [提交问题](https://github.com/yourusername/futures-analysis/issues)
- 💬 **讨论**: [GitHub Discussions](https://github.com/yourusername/futures-analysis/discussions)

### 问题模板
```markdown
## 问题描述
简要描述遇到的问题

## 复现步骤
1. 第一步
2. 第二步
3. 第三步

## 预期行为
描述期望的正确行为

## 实际行为
描述实际发生的情况

## 环境信息
- 操作系统: 
- Python版本: 
- Streamlit版本: 
- 其他相关信息: 

## 错误信息
```
粘贴完整的错误信息
```

## 截图
如果适用，添加截图帮助解释问题
```

---

**🔧 故障排除指南 v2.1**  
**更新日期**: 2024-12-01  
**维护者**: 7haoge

记住：大多数问题都有解决方案，不要放弃！如果以上方法都无法解决问题，请联系我们获取帮助。 