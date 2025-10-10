# 🤝 贡献指南

感谢您对期货持仓分析系统的关注！我们欢迎所有形式的贡献。

## 📋 贡献方式

### 🐛 报告Bug
- 使用 [GitHub Issues](https://github.com/yourusername/futures-analysis/issues) 报告bug
- 请提供详细的错误信息和复现步骤
- 包含您的系统环境信息

### 💡 提出新功能
- 在 Issues 中描述您的想法
- 说明功能的用途和预期效果
- 讨论实现方案

### 🔧 代码贡献
1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 🛠️ 开发环境设置

### 环境要求
- Python 3.8+
- Git
- 稳定的网络连接

### 设置步骤
```bash
# 1. 克隆项目
git clone https://github.com/yourusername/futures-analysis.git
cd futures-analysis

# 2. 创建虚拟环境
python -m venv venv

# 3. 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 运行测试
python test_auto_skip.py
python test_system.py

# 6. 启动开发服务器
streamlit run streamlit_app.py
```

## 📝 代码规范

### Python代码风格
- 遵循 PEP 8 规范
- 使用有意义的变量和函数名
- 添加适当的注释和文档字符串
- 保持函数简洁，单一职责

### 示例代码格式
```python
def fetch_position_data(self, trade_date: str) -> bool:
    """
    获取持仓数据
    
    Args:
        trade_date: 交易日期，格式为YYYYMMDD
        
    Returns:
        bool: 获取成功返回True，失败返回False
    """
    try:
        # 实现逻辑
        return True
    except Exception as e:
        logger.error(f"获取持仓数据失败: {e}")
        return False
```

### 提交信息格式
```
类型(范围): 简短描述

详细描述（可选）

相关Issue: #123
```

类型包括：
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

## 🧪 测试要求

### 运行测试
```bash
# 运行所有测试
python test_auto_skip.py
python test_system.py

# 检查代码覆盖率（如果安装了coverage）
coverage run -m pytest tests/
coverage report
```

### 测试要求
- 新功能必须包含相应的测试
- 确保所有现有测试通过
- 测试覆盖率不应降低

## 📚 文档要求

### 文档更新
- 新功能需要更新相关文档
- API变更需要更新API文档
- 重大变更需要更新README

### 文档格式
- 使用Markdown格式
- 包含代码示例
- 添加适当的图片和图表

## 🔍 代码审查

### Pull Request要求
- 提供清晰的PR描述
- 关联相关的Issue
- 确保CI检查通过
- 响应审查意见

### 审查标准
- 代码质量和可读性
- 功能正确性
- 性能影响
- 安全性考虑
- 文档完整性

## 🚀 发布流程

### 版本号规范
遵循语义化版本控制 (SemVer)：
- 主版本号：不兼容的API修改
- 次版本号：向下兼容的功能性新增
- 修订号：向下兼容的问题修正

### 发布检查清单
- [ ] 所有测试通过
- [ ] 文档已更新
- [ ] 版本号已更新
- [ ] 更新日志已添加
- [ ] 性能测试通过

## 💬 社区准则

### 行为准则
- 尊重所有贡献者
- 建设性的讨论和反馈
- 包容不同的观点和经验
- 专注于对项目最有利的事情

### 沟通渠道
- GitHub Issues：Bug报告和功能请求
- GitHub Discussions：一般讨论和问答
- Email：953534947@qq.com（紧急问题）

## 🎯 贡献重点

当前我们特别欢迎以下方面的贡献：

### 高优先级
- 🐛 Bug修复
- 📊 新的分析策略
- 🚀 性能优化
- 📱 用户体验改进

### 中优先级
- 📚 文档改进
- 🧪 测试覆盖率提升
- 🔧 代码重构
- 🌐 国际化支持

### 低优先级
- 🎨 UI美化
- 📈 新的图表类型
- 🔌 第三方集成
- 📦 打包和分发

## 🏆 贡献者认可

我们会在以下地方认可贡献者：
- README.md 中的贡献者列表
- 发布说明中的特别感谢
- 项目网站（如果有）

## 📞 获取帮助

如果您在贡献过程中遇到问题：

1. 查看现有的Issues和Discussions
2. 阅读项目文档
3. 联系维护者：953534947@qq.com

## 🙏 感谢

感谢您考虑为期货持仓分析系统做出贡献！每一个贡献都让这个项目变得更好。

---

**让我们一起构建更好的期货分析工具！** 🚀 