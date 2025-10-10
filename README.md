# 🚀 商品期货AI分析系统

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-red)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![DeepSeek](https://img.shields.io/badge/AI-DeepSeek-orange)](https://www.deepseek.com/)
[![Multi-Agent](https://img.shields.io/badge/Architecture-Multi--Agent-purple)](https://github.com/haoge10241024/TradingAgents_for_Futures)

**🤖 基于Multi-Agent架构的智能期货分析平台**

*集成AI推理、技术分析、持仓分析、基差分析等全方位功能*

[📖 使用文档](https://github.com/haoge10241024/TradingAgents_for_Futures/wiki) • 
[🚀 快速开始](#-快速开始) • 
[💡 功能特色](#-核心功能) • 
[📊 在线演示](#-在线演示)

</div>

## 📊 系统简介

这是一个功能完整的AI驱动的商品期货分析系统，为期货交易提供全方位的智能分析和决策支持。

### ✨ 为什么选择我们的系统？

- 🎯 **专业级分析**：涵盖技术、基本面、持仓、基差等6大维度
- 🤖 **AI智能决策**：Multi-Agent架构，模拟专业交易团队决策流程
- 📈 **实时数据**：支持50+期货品种，数据实时更新
- 🎨 **美观界面**：Streamlit构建的现代化Web界面
- 🔧 **易于使用**：一键启动，配置简单，文档详细
- 💰 **成本低廉**：DeepSeek API费用仅¥1-2/百万tokens

### 🏆 系统亮点

| 特色 | 描述 |
|------|------|
| 🧠 **AI多空辩论** | 看涨研究员 vs 看跌研究员，AI深度推理 |
| 👥 **专业决策链** | 交易员→风控→CIO，模拟真实交易流程 |
| 📊 **6大分析模块** | 技术、基差、库存、新闻、持仓、期限结构 |
| 📄 **智能报告** | 自动生成Word专业分析报告 |
| 🔄 **实时更新** | 数据自动更新，分析结果实时刷新 |

### 核心功能

- **📈 6大分析模块**
  - 技术分析：K线、指标、形态识别
  - 基差分析：现货与期货价差分析
  - 库存仓单分析：供需关系研判
  - 新闻分析：市场情绪和舆情监测
  - 持仓席位分析：主力动向追踪
  - 期限结构分析：跨期价差研究

- **🎭 AI多空辩论系统**
  - 看涨研究员 vs 看跌研究员
  - 深度推理引擎
  - 研究经理综合评判

- **👨‍💼 专业交易决策链**
  - 专业交易员：交易策略制定
  - 风险管理团队：风险评估和控制
  - CIO决策：最终投资决策

- **📄 智能报告生成**
  - Word专业报告导出
  - 图表可视化下载
  - 多维度分析整合

## 🚀 快速开始

### 1. 环境要求

```bash
Python >= 3.8
```

推荐使用Python 3.10或3.11以获得最佳性能。

### 2. 安装依赖

```bash
# 克隆或下载项目后
cd TradingAgents_for_Futures

# 安装Python依赖包
pip install -r requirements.txt
```

> **注意**: `ta-lib`需要先安装C库，Windows用户可以从[这里](https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib)下载wheel文件安装。

### 3. 配置API密钥（重要）

⚠️ **必须配置API密钥才能使用系统**

```bash
# 复制配置文件模板
cp 期货TradingAgents系统_配置文件.example.json 期货TradingAgents系统_配置文件.json

# 编辑配置文件，填入API密钥
# 找到 "api_key" 字段，填入你的密钥
```

需要的API密钥：
- **DeepSeek API**（必需）：用于AI分析
  - 获取地址: https://platform.deepseek.com/
  - 费用：约¥1-2/百万tokens（非常实惠）
  - 新用户注册即送免费额度
  - 详细说明：[API密钥配置指南](API密钥配置指南.md)

- **Serper API**（可选）：用于新闻搜索
  - 获取地址: https://serper.dev/
  - 新用户免费2,500次搜索

> 📖 **详细配置教程**：请查看 [API密钥配置指南](API密钥配置指南.md)，包含图文步骤和常见问题。

### 4. 启动系统

#### Windows用户
双击运行 `启动系统.bat`

#### 所有平台
```bash
# 使用启动脚本
python 启动系统.py

# 或直接启动
streamlit run 期货TradingAgents系统_专业完整版界面.py
```

系统将在浏览器中自动打开，默认地址: http://localhost:8501

## 📊 在线演示

> 🎬 **系统演示视频**：[点击观看完整演示](https://github.com/haoge10241024/TradingAgents_for_Futures/discussions)

### 📸 界面预览

| 功能模块 | 界面截图 | 说明 |
|---------|---------|------|
| 🏠 **主界面** | ![主界面](https://via.placeholder.com/400x250/4CAF50/white?text=主界面) | 品种选择、分析配置 |
| 📊 **技术分析** | ![技术分析](https://via.placeholder.com/400x250/2196F3/white?text=技术分析) | K线图、技术指标 |
| 🤖 **AI辩论** | ![AI辩论](https://via.placeholder.com/400x250/FF9800/white?text=AI多空辩论) | 看涨vs看跌分析 |
| 📄 **报告导出** | ![报告](https://via.placeholder.com/400x250/9C27B0/white?text=专业报告) | Word报告生成 |

*注：实际截图请运行系统后查看*

## 📊 关于数据

### 🎁 本仓库已包含示例数据

✅ **开箱即用**：本项目包含10-15个主要品种的历史数据，可直接使用：
- 📈 基差数据（现货-期货价差）
- 📦 库存仓单数据（供需关系）
- 👥 持仓席位数据（主力动向）
- 📊 技术分析数据（K线、指标）
- ⏰ 期限结构数据（跨期价差）

### 获取完整数据（可选）

如需完整的历史数据和所有品种：

```bash
# 运行数据更新器
python unified_futures_data_updater.py

# 首次下载需要10-30分钟
# 后续增量更新只需2-5分钟
```

### 数据来源

所有数据来自公开渠道：
- **AkShare**：开源金融数据接口
- **交易所官网**：上期所、大商所、郑商所、能源中心

> 📖 **数据配置详情**：请查看 [本地数据配置指南](本地数据配置指南.md) 和 [数据上传说明](数据上传说明.md)

## 📖 使用指南

### 基本流程

1. **选择品种**: 在侧边栏选择要分析的期货品种（如铜、铝、螺纹钢等）
2. **配置分析**: 选择要启用的分析模块
3. **执行分析**: 点击"开始分析"按钮
4. **查看结果**: 查看6大模块的分析报告
5. **AI决策**: 启动多空辩论和决策链
6. **导出报告**: 下载Word报告或图表

### 数据更新

系统首次运行需要下载历史数据：

```bash
# 更新所有数据
python unified_futures_data_updater.py

# 或使用启动脚本自动检查和更新
python 启动系统.py
```

### 支持的品种

系统支持国内四大期货交易所的50+个品种：

- **上期所(SHFE)**: 铜、铝、锌、铅、镍、锡、金、银、螺纹钢、热卷等
- **大商所(DCE)**: 豆一、豆二、豆粕、豆油、玉米、铁矿石、焦炭、焦煤等
- **郑商所(CZCE)**: 棉花、白糖、PTA、甲醇、玻璃、纯碱、尿素等
- **能源中心(INE)**: 原油、20号胶、低硫燃料油等

## 📁 项目结构

```
TradingAgents_for_Futures/
├── 期货TradingAgents系统_专业完整版界面.py    # 主界面程序
├── 优化版辩论风控决策系统.py                # 核心决策引擎
├── 期货TradingAgents系统_基础架构.py        # 基础框架
├── 期货TradingAgents系统_工具模块.py        # 工具函数
├── unified_futures_data_updater.py         # 数据更新器
├── config.py                               # 配置文件
├── requirements.txt                        # 依赖清单
├── README.md                              # 说明文档
├── 启动系统.bat                           # Windows启动脚本
├── 启动系统.py                            # Python启动脚本
│
├── qihuo/                                 # 核心代码包
│   ├── agents/                           # AI Agent定义
│   ├── analysis/                         # 分析模块
│   ├── config/                           # 配置文件
│   ├── data_providers/                   # 数据提供者
│   ├── database/                         # 本地数据库
│   ├── features/                         # 特征工程
│   ├── llm/                             # LLM客户端
│   ├── scripts/                         # 工具脚本
│   └── utils/                           # 工具函数
│
└── modules/                              # 数据更新模块
    ├── basis_updater.py                 # 基差数据
    ├── inventory_updater.py             # 库存数据
    ├── positioning_updater.py           # 持仓数据
    ├── technical_updater.py             # 技术数据
    └── term_structure_updater.py        # 期限结构数据
```

## 🔧 高级配置

### 配置文件说明

主配置文件: `期货TradingAgents系统_配置文件.json`

```json
{
  "api_settings": {
    "deepseek": {
      "api_key": "你的API密钥",
      "model": "deepseek-chat",
      "reasoning_model": "deepseek-reasoner"
    }
  },
  "analysis_modules": {
    "technical": { "enabled": true },
    "basis": { "enabled": true },
    "inventory": { "enabled": true }
    // ... 其他模块配置
  }
}
```

### 数据路径配置

默认数据存储在 `qihuo/database/` 目录下：

- `basis/` - 基差数据
- `inventory/` - 库存仓单数据
- `positioning/` - 持仓席位数据
- `technical_analysis/` - 技术分析数据
- `term_structure/` - 期限结构数据

## 📊 数据源说明

本系统的数据主要来自：

1. **AkShare** - 开源金融数据接口
2. **交易所官网** - 各期货交易所公开数据
3. **新闻API** - 实时市场新闻和资讯

所有数据仅供学习和研究使用，不构成投资建议。

## 🤝 常见问题

### Q: 如何获取DeepSeek API密钥？
A: 访问 https://platform.deepseek.com/ 注册账号并创建API密钥。

### Q: TA-Lib安装失败怎么办？
A: Windows用户可以从 https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib 下载对应Python版本的wheel文件安装。

### Q: 数据更新失败怎么办？
A: 检查网络连接，某些数据源可能需要稳定的网络环境。可以多次尝试更新。

### Q: 分析速度慢怎么办？
A: 
- 减少分析的历史数据天数
- 关闭部分不必要的分析模块
- 使用更快的AI模型（deepseek-chat而非reasoner）

### Q: 如何添加新的品种？
A: 在 `config.py` 的品种列表中添加新品种代码，系统会自动支持。

## 📝 注意事项

1. **API配额**: DeepSeek API有调用限制，请合理使用
2. **数据延迟**: 部分数据可能有1-2天的延迟
3. **投资风险**: 系统分析仅供参考，投资有风险，决策需谨慎
4. **网络环境**: 需要稳定的网络连接以获取数据和访问API

## 🔐 隐私和安全

- API密钥等敏感信息不会被上传或共享
- 本地数据存储在 `qihuo/database/` 目录
- 不会收集用户的交易数据或个人信息

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🌟 致谢

- [AkShare](https://github.com/akfamily/akshare) - 优秀的金融数据接口
- [Streamlit](https://streamlit.io/) - 强大的Web应用框架
- [DeepSeek](https://www.deepseek.com/) - 先进的AI推理引擎

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 如何贡献

1. **Fork** 本仓库
2. **创建** 功能分支 (`git checkout -b feature/AmazingFeature`)
3. **提交** 更改 (`git commit -m 'Add some AmazingFeature'`)
4. **推送** 到分支 (`git push origin feature/AmazingFeature`)
5. **创建** Pull Request

### 贡献类型

- 🐛 **Bug修复**：发现并修复系统问题
- ✨ **新功能**：添加新的分析模块或功能
- 📖 **文档改进**：完善使用文档和说明
- 🎨 **界面优化**：改进用户界面和体验
- 🔧 **性能优化**：提升系统运行效率

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=haoge10241024/TradingAgents_for_Futures&type=Date)](https://star-history.com/#haoge10241024/TradingAgents_for_Futures&Date)

## 📊 项目统计

![GitHub stars](https://img.shields.io/github/stars/haoge10241024/TradingAgents_for_Futures?style=social)
![GitHub forks](https://img.shields.io/github/forks/haoge10241024/TradingAgents_for_Futures?style=social)
![GitHub issues](https://img.shields.io/github/issues/haoge10241024/TradingAgents_for_Futures)
![GitHub pull requests](https://img.shields.io/github/issues-pr/haoge10241024/TradingAgents_for_Futures)

## 📧 联系方式

<div align="center">

**👨‍💻 项目作者：7haoge**

📧 **邮箱**：953534947@qq.com  
🐙 **GitHub**：[@haoge10241024](https://github.com/haoge10241024)  
💬 **讨论区**：[GitHub Discussions](https://github.com/haoge10241024/TradingAgents_for_Futures/discussions)

---

**⭐ 如果这个项目对您有帮助，请给我们一个Star！**

</div>

---

## ⚠️ 免责声明

**重要提醒**：
- 📚 本系统仅供学习和研究使用
- 💰 不构成任何投资建议
- ⚠️ 期货交易具有高风险
- 🚨 可能导致全部或部分本金损失
- 📋 使用本系统进行交易决策的一切后果由使用者自行承担

**请理性投资，风险自负！**
