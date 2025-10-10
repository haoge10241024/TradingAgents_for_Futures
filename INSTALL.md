# 安装指南

本文档提供商品期货AI分析系统的详细安装步骤。

## 系统要求

### 硬件要求

- **CPU**: 双核及以上（推荐四核）
- **内存**: 8GB RAM（推荐16GB）
- **磁盘空间**: 至少5GB可用空间
- **网络**: 稳定的互联网连接

### 软件要求

- **操作系统**: 
  - Windows 10/11
  - macOS 10.14+
  - Linux (Ubuntu 18.04+, CentOS 7+)
- **Python**: 3.8, 3.9, 3.10, 或 3.11（推荐3.10）
- **pip**: 最新版本

## 安装步骤

### 1. 安装Python

#### Windows

1. 访问 [Python官网](https://www.python.org/downloads/)
2. 下载Python 3.10安装包
3. 运行安装程序，**勾选 "Add Python to PATH"**
4. 验证安装：
```cmd
python --version
pip --version
```

#### macOS

使用Homebrew安装：
```bash
brew install python@3.10
python3 --version
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3.10 python3.10-pip
python3.10 --version
```

### 2. 下载项目

#### 方法1: Git克隆

```bash
git clone https://github.com/your-repo/TradingAgents_for_Futures.git
cd TradingAgents_for_Futures
```

#### 方法2: 下载ZIP

1. 从GitHub下载ZIP文件
2. 解压到目标目录
3. 打开命令行并进入该目录

### 3. 创建虚拟环境（推荐）

#### Windows

```cmd
python -m venv venv
venv\Scripts\activate
```

#### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. 安装依赖包

```bash
pip install -r requirements.txt
```

> **注意**: 如果下载速度慢，可以使用国内镜像：
> ```bash
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

### 5. 安装TA-Lib（可选但推荐）

TA-Lib用于技术指标计算。

#### Windows

1. 访问 [这个页面](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)
2. 下载对应Python版本的whl文件，例如：
   - Python 3.10 64位: `TA_Lib‑0.4.24‑cp310‑cp310‑win_amd64.whl`
3. 安装：
```cmd
pip install TA_Lib‑0.4.24‑cp310‑cp310‑win_amd64.whl
```

#### macOS

```bash
brew install ta-lib
pip install ta-lib
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt-get install ta-lib
pip install ta-lib
```

如果TA-Lib安装失败，系统会使用备用方案（stockstats库），不影响核心功能。

### 6. 配置API密钥

#### 6.1 复制配置模板

```bash
# 复制JSON配置模板
cp 期货TradingAgents系统_配置文件.example.json 期货TradingAgents系统_配置文件.json

# 复制Python配置模板
cp config.example.py config.py
```

#### 6.2 获取DeepSeek API密钥

1. 访问 [DeepSeek平台](https://platform.deepseek.com/)
2. 注册账号并登录
3. 进入"API Keys"页面
4. 点击"Create API Key"
5. 复制生成的密钥（格式：`sk-xxxxxx...`）

#### 6.3 填写配置文件

编辑 `期货TradingAgents系统_配置文件.json`：

```json
{
  "api_settings": {
    "deepseek": {
      "api_key": "sk-你的DeepSeek密钥粘贴在这里"
    }
  }
}
```

或编辑 `config.py`：

```python
DEEPSEEK_API_KEY = "sk-你的DeepSeek密钥粘贴在这里"
```

### 7. 初始化数据目录

系统会自动创建必要的目录，但也可以手动创建：

```bash
mkdir -p qihuo/database/{basis,inventory,positioning,technical_analysis,term_structure}
mkdir -p qihuo/logs
mkdir -p qihuo/cache
mkdir -p qihuo/output
```

### 8. 验证安装

运行以下命令验证安装：

```bash
python -c "import streamlit, pandas, plotly; print('依赖检查通过')"
```

## 首次运行

### Windows

双击运行 `启动系统.bat`

或在命令行中：
```cmd
python 启动系统.py
```

### macOS/Linux

```bash
chmod +x 启动系统.py
python 启动系统.py
```

### 手动启动

```bash
streamlit run 期货TradingAgents系统_专业完整版界面.py
```

系统将在浏览器中打开，默认地址：http://localhost:8501

## 常见安装问题

### 问题1: Python版本不兼容

**错误**: `SyntaxError` 或 `ModuleNotFoundError`

**解决**:
```bash
# 检查Python版本
python --version

# 如果版本低于3.8，需要升级Python
```

### 问题2: pip安装失败

**错误**: `error: Microsoft Visual C++ 14.0 is required`

**解决** (Windows):
1. 下载并安装 [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
2. 或使用预编译的wheel文件

### 问题3: TA-Lib安装失败

**解决**: TA-Lib不是必需的，系统会自动使用备用库

如果需要安装：
- Windows: 使用wheel文件
- macOS: 先安装Homebrew，然后 `brew install ta-lib`
- Linux: `sudo apt-get install ta-lib`

### 问题4: 网络连接问题

**症状**: pip下载缓慢或失败

**解决**: 使用国内镜像
```bash
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题5: 权限错误

**错误**: `Permission denied`

**解决**:
```bash
# Linux/macOS
sudo pip install -r requirements.txt

# 或使用--user参数
pip install --user -r requirements.txt
```

### 问题6: Streamlit无法启动

**错误**: `streamlit: command not found`

**解决**:
```bash
# 确认streamlit已安装
pip list | grep streamlit

# 如果未安装
pip install streamlit

# 或使用完整路径
python -m streamlit run 期货TradingAgents系统_专业完整版界面.py
```

## 数据初始化

首次运行时，需要下载历史数据：

```bash
# 更新所有数据（可能需要10-30分钟）
python unified_futures_data_updater.py
```

或在Streamlit界面中点击"数据更新"按钮。

## 升级指南

### 升级Python包

```bash
pip install --upgrade -r requirements.txt
```

### 升级系统代码

```bash
git pull origin main
pip install --upgrade -r requirements.txt
```

### 保留配置和数据

升级时，以下文件不会被覆盖：
- `config.py`
- `期货TradingAgents系统_配置文件.json`
- `qihuo/database/` 目录下的数据

## 卸载

### 删除虚拟环境

```bash
# Windows
rmdir /s venv

# macOS/Linux
rm -rf venv
```

### 删除项目文件

直接删除整个项目目录即可。

## 进阶配置

### 使用Docker（可选）

如果熟悉Docker，可以使用容器化部署：

```dockerfile
# Dockerfile示例
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "期货TradingAgents系统_专业完整版界面.py"]
```

```bash
docker build -t futures-ai .
docker run -p 8501:8501 futures-ai
```

### 配置系统服务（Linux）

创建systemd服务文件 `/etc/systemd/system/futures-ai.service`:

```ini
[Unit]
Description=Futures AI Analysis System
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/TradingAgents_for_Futures
ExecStart=/usr/bin/python3 启动系统.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl enable futures-ai
sudo systemctl start futures-ai
```

## 性能优化建议

1. **使用SSD**: 提高数据读写速度
2. **增加内存**: 推荐16GB以上
3. **使用虚拟环境**: 隔离依赖，避免冲突
4. **定期清理**: 删除旧的日志和缓存文件

## 技术支持

如遇到安装问题：

1. 查看 [FAQ](CONFIGURATION.md#常见配置问题)
2. 搜索或提交 [GitHub Issue](https://github.com/your-repo/issues)
3. 查看日志文件 `qihuo/logs/trading_agents.log`

---

安装完成后，请阅读 [README.md](README.md) 了解系统使用方法。

