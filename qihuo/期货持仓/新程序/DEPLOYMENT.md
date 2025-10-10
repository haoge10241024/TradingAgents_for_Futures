# 期货持仓分析系统 - Streamlit Cloud 部署指南

## 📋 部署前准备

### 1. GitHub仓库准备
确保您的GitHub仓库包含以下文件：
- `streamlit_app.py` - 主应用文件
- `futures_analyzer.py` - 核心分析模块
- `config.py` - 配置文件
- `utils.py` - 工具函数
- `requirements.txt` - 依赖包列表
- `README.md` - 项目说明
- `.streamlit/config.toml` - Streamlit配置
- `.gitignore` - Git忽略文件

### 2. 文件结构
```
your-repo/
├── streamlit_app.py          # 主应用入口
├── futures_analyzer.py       # 核心分析引擎
├── config.py                # 系统配置
├── utils.py                 # 工具函数
├── requirements.txt         # Python依赖
├── README.md               # 项目文档
├── DEPLOYMENT.md           # 部署指南
├── .gitignore             # Git忽略文件
├── .streamlit/
│   └── config.toml        # Streamlit配置
└── data/                  # 数据目录（自动创建）
```

## 🚀 Streamlit Cloud 部署步骤

### 步骤1：准备GitHub仓库
1. 在GitHub上创建新仓库（建议命名为 `futures-position-analysis`）
2. 将所有必要文件上传到仓库
3. 确保仓库是公开的（Public）

### 步骤2：连接Streamlit Cloud
1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 使用GitHub账号登录
3. 点击 "New app" 创建新应用

### 步骤3：配置应用
1. **Repository**: 选择您的GitHub仓库
2. **Branch**: 选择 `main` 或 `master` 分支
3. **Main file path**: 输入 `streamlit_app.py`
4. **App URL**: 自定义应用URL（可选）

### 步骤4：部署
1. 点击 "Deploy!" 开始部署
2. 等待部署完成（通常需要2-5分钟）
3. 部署成功后会自动跳转到应用页面

## ⚙️ 部署配置说明

### requirements.txt 说明
```txt
streamlit==1.28.0         # Streamlit框架（固定版本）
pandas==1.3.5             # 数据处理（Python 3.8兼容版本）
numpy==1.21.6             # 数值计算（Python 3.8兼容版本）
plotly==5.15.0            # 图表绘制
akshare==1.12.0           # 金融数据获取
openpyxl==3.0.10          # Excel读写
xlsxwriter==3.0.9         # Excel写入
requests==2.28.2          # HTTP请求
python-dateutil==2.8.2    # 日期处理
pytz==2022.7              # 时区处理
```

### Streamlit配置
- 主题颜色：蓝色系
- 禁用开发模式
- 优化云端性能

### Python版本控制
- `runtime.txt` - 指定Python 3.8版本（避免Python 3.13的distutils问题）
- `.python-version` - 本地开发版本控制

### 版本选择说明
- **Python 3.8**: 选择此版本是因为：
  - 稳定性好，兼容性强
  - 避免Python 3.13中移除distutils模块的问题
  - 与所有依赖包版本完全兼容
- **依赖包版本**: 选择经过测试的稳定版本组合，确保在Streamlit Cloud上正常运行

## 🔧 常见问题解决

### 1. 部署失败
**可能原因**：
- requirements.txt中的包版本冲突
- 主文件路径错误
- 代码中有语法错误
- Python版本不兼容（如pandas在Python 3.13下编译失败）
- distutils模块缺失（Python 3.12+版本问题）

**解决方案**：
- 检查GitHub仓库中的文件是否完整
- 确认streamlit_app.py文件名正确
- 查看部署日志中的错误信息
- 确保使用Python 3.8版本（通过runtime.txt指定）
- 使用固定版本号的依赖包
- 如果遇到"ModuleNotFoundError: No module named 'distutils'"错误，确保使用Python 3.8而不是3.12+版本

### 2. 应用运行缓慢
**可能原因**：
- 网络数据获取延迟
- 计算量过大

**解决方案**：
- 系统已内置缓存机制
- 避免频繁重新分析
- 使用快速模式

### 3. 数据获取失败
**可能原因**：
- 网络连接问题
- API限制

**解决方案**：
- 系统会自动重试
- 检查选择的日期是否为交易日
- 稍后重试

## 📱 使用建议

### 1. 首次使用
1. 等待应用完全加载
2. 配置家人席位（如需要）
3. 选择最近的交易日
4. 点击"开始分析"

### 2. 性能优化
- 避免同时打开多个分析任务
- 使用缓存结果，避免重复分析
- 定期清除缓存

### 3. 数据安全
- 所有数据处理都在云端进行
- 不会存储用户个人信息
- 分析结果仅在会话期间保留

## 🔄 更新部署

### 更新代码
1. 在GitHub仓库中更新代码
2. 提交并推送到主分支
3. Streamlit Cloud会自动重新部署

### 版本管理
- 建议使用Git标签管理版本
- 重要更新前先在本地测试
- 保持README.md文档更新

## 📞 技术支持

如果在部署过程中遇到问题：
1. 检查Streamlit Cloud的部署日志
2. 确认所有依赖包都已正确安装
3. 联系作者：953534947@qq.com

---

**期货持仓分析系统 v2.0**  
**作者：7haoge | 邮箱：953534947@qq.com** 