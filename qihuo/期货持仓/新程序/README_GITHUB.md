# 🚀 期货持仓分析系统 v2.1

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.1-orange.svg)](https://github.com/yourusername/futures-analysis)

**智能期货持仓分析系统 - 自动跳过版**

一个基于Python和Streamlit的智能期货持仓分析系统，集成多种分析策略，具备智能超时处理功能，确保分析流畅进行。

**作者：7haoge | 邮箱：953534947@qq.com**

---

## 🌟 核心特性

### ⚡ v2.1 新特性：智能自动跳过
- 🚀 **智能超时检测**：自动监控交易所响应时间
- 🎯 **自动跳过机制**：广期所超过20秒自动跳过
- 📊 **无缝继续分析**：跳过后继续获取其他交易所数据
- 🔧 **用户无感知**：完全自动化处理，无需手动干预

### 📊 分析策略
- **多空力量变化策略**：分析席位持仓增减变化判断市场趋势
- **蜘蛛网策略**：基于持仓分布分化程度判断机构资金参与情况
- **家人席位反向操作策略**：基于散户投资者行为特点的反向操作策略
- **期限结构分析**：严格按照近月到远月价格关系分析
- **信号共振分析**：识别多策略共同看好的品种

### 🛠️ 技术特性
- **实时数据获取**：自动从各大期货交易所获取最新持仓数据
- **可配置家人席位**：用户可自定义散户席位配置
- **智能缓存机制**：避免重复分析，提高效率
- **可视化展示**：丰富的图表和数据可视化
- **报告导出**：支持Excel和文本格式的分析报告导出

---

## 🚀 快速开始

### 环境要求
- Python 3.8+
- 稳定的网络连接
- 8GB+ 内存推荐

### 安装步骤

1. **克隆项目**
   ```bash
   git clone https://github.com/yourusername/futures-analysis.git
   cd futures-analysis
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **运行测试**
   ```bash
   python test_auto_skip.py
   ```

4. **启动应用**
   ```bash
   streamlit run streamlit_app.py
   ```

5. **开始使用**
   - 在浏览器中打开显示的URL（通常是 http://localhost:8501）
   - 选择分析日期
   - 点击"🚀 开始分析"
   - 等待分析完成

✅ **就这么简单！系统会自动处理所有技术问题。**

---

## 📋 项目结构

```
futures-analysis/
├── streamlit_app.py          # 主应用程序
├── cloud_data_fetcher.py     # 云端数据获取器（智能跳过功能）
├── futures_analyzer.py       # 核心分析引擎
├── performance_optimizer.py  # 性能优化模块
├── config.py                # 系统配置
├── utils.py                 # 工具函数
├── requirements.txt         # 依赖包列表
├── .streamlit/
│   └── config.toml          # Streamlit配置
├── .github/
│   └── workflows/
│       └── test.yml         # GitHub Actions工作流
├── docs/                    # 文档目录
│   ├── QUICK_START_GUIDE.md # 快速开始指南
│   ├── AUTO_SKIP_FEATURES.md # 自动跳过功能详解
│   └── API_REFERENCE.md     # API参考文档
├── tests/                   # 测试目录
│   ├── test_auto_skip.py    # 自动跳过功能测试
│   └── test_system.py       # 系统测试
└── data/                    # 数据存储目录（自动创建）
```

---

## 🎯 使用指南

### 基本操作
1. **配置家人席位**（可选）
   - 在左侧边栏查看当前家人席位配置
   - 可添加新席位或删除现有席位
   - 支持重置为默认配置

2. **选择分析日期**
   - 在左侧边栏选择要分析的交易日期
   - 建议选择最近的工作日

3. **开始分析**
   - 点击"🚀 开始分析"按钮
   - 系统自动获取数据并处理超时问题
   - 查看实时进度显示

4. **查看结果**
   - 浏览各策略的分析结果
   - 点击展开查看详细持仓信息
   - 查看信号共振品种

### 高级功能
- **详细持仓查看**：每个信号都可展开查看详细持仓数据
- **家人席位配置**：实时配置散户席位，立即生效
- **报告导出**：下载Excel或文本格式的分析报告
- **网络诊断**：内置网络连接测试和诊断功能

---

## 🔧 技术实现

### 智能自动跳过机制

```python
# 核心超时控制逻辑
def fetch_data_with_auto_skip(self, trade_date):
    # 使用线程和队列实现精确超时控制
    result_queue = queue.Queue()
    
    def fetch_data():
        try:
            result = self.safe_akshare_call(exchange_func, **args)
            result_queue.put(('success', result))
        except Exception as e:
            result_queue.put(('error', str(e)))
    
    # 启动获取线程
    fetch_thread = threading.Thread(target=fetch_data)
    fetch_thread.daemon = True
    fetch_thread.start()
    
    # 等待结果，广期所最多等待20秒
    fetch_thread.join(timeout=20)
    
    if fetch_thread.is_alive():
        # 超时自动跳过
        self.auto_skip_and_continue()
```

### 关键技术特性
- **线程安全设计**：使用threading和queue确保并发安全
- **精确超时控制**：广期所20秒，其他交易所30秒
- **智能错误处理**：自动创建空文件保持系统兼容性
- **优雅降级**：部分数据获取失败不影响整体分析

---

## 📊 性能优化

### v2.1版本改进
| 功能 | v2.0 | v2.1 | 改进 |
|------|------|------|------|
| 广期所处理 | 手动选择跳过 | 自动智能跳过 | 🚀 完全自动化 |
| 用户操作 | 3-4步 | 2步 | 📱 简化50% |
| 超时处理 | 可能无限等待 | 20秒精确控制 | ⚡ 快速响应 |
| 错误恢复 | 手动重试 | 自动处理 | 🔧 智能恢复 |

### 性能指标
- **首次分析**：1-3分钟（取决于网络状况）
- **缓存命中**：10-30秒
- **广期所超时**：最多20秒自动跳过
- **成功率**：99%+（即使部分交易所失败）

---

## 🧪 测试

### 运行测试
```bash
# 运行自动跳过功能测试
python test_auto_skip.py

# 运行完整系统测试
python test_system.py
```

### 测试覆盖
- ✅ 模块导入测试
- ✅ 自动跳过功能测试
- ✅ 超时机制测试
- ✅ 网络连接测试
- ✅ 数据获取测试

---

## 📚 文档

- [📖 快速开始指南](docs/QUICK_START_GUIDE.md) - 一分钟快速上手
- [🚀 自动跳过功能详解](docs/AUTO_SKIP_FEATURES.md) - 技术实现详解
- [🔧 API参考文档](docs/API_REFERENCE.md) - 开发者文档
- [❓ 常见问题解答](docs/FAQ.md) - 问题排查指南

---

## 🤝 贡献指南

### 如何贡献
1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 开发环境设置
```bash
# 克隆项目
git clone https://github.com/yourusername/futures-analysis.git
cd futures-analysis

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 运行测试
python -m pytest tests/
```

---

## 🔄 更新日志

### v2.1.0 (2024-05-30)
**重大改进**
- 🚀 新增智能自动跳过功能
- 🎯 简化用户操作流程
- ⚡ 提升系统响应速度
- 🔧 优化错误处理机制

**技术优化**
- 线程安全的超时控制
- 精确的20秒广期所超时
- 自动兼容性文件创建
- 智能错误恢复机制

### v2.0.0 (2024-05-15)
**新增功能**
- 可配置家人席位功能
- 详细持仓信息查看
- 改进的期限结构分析
- 性能优化和缓存机制

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 📞 联系方式

**作者**：7haoge  
**邮箱**：953534947@qq.com  
**项目链接**：https://github.com/yourusername/futures-analysis

---

## 🙏 致谢

- [Streamlit](https://streamlit.io/) - 优秀的Web应用框架
- [akshare](https://akshare.akfamily.xyz/) - 金融数据接口
- [Plotly](https://plotly.com/) - 数据可视化库
- [Pandas](https://pandas.pydata.org/) - 数据处理库

---

## ⭐ Star History

如果这个项目对您有帮助，请给我们一个 ⭐！

[![Star History Chart](https://api.star-history.com/svg?repos=yourusername/futures-analysis&type=Date)](https://star-history.com/#yourusername/futures-analysis&Date)

---

**🚀 期货持仓分析系统 v2.1 - 让期货分析更智能、更流畅！** 