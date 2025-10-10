# 🤝 贡献指南

感谢您对商品期货AI分析系统的关注！我们欢迎各种形式的贡献。

## 🚀 快速开始

### 1. Fork 仓库
点击仓库右上角的 "Fork" 按钮，将项目复制到您的GitHub账号下。

### 2. 克隆仓库
```bash
git clone https://github.com/您的用户名/TradingAgents_for_Futures.git
cd TradingAgents_for_Futures
```

### 3. 创建分支
```bash
git checkout -b feature/您的功能名称
```

### 4. 安装依赖
```bash
pip install -r requirements.txt
```

## 📝 贡献类型

### 🐛 Bug修复
- 发现并修复系统问题
- 改进错误处理
- 优化性能问题

### ✨ 新功能
- 添加新的分析模块
- 改进AI分析算法
- 增加新的数据源
- 优化用户界面

### 📖 文档改进
- 完善使用文档
- 添加代码注释
- 改进README
- 创建教程视频

### 🎨 界面优化
- 改进Streamlit界面
- 优化图表显示
- 提升用户体验
- 响应式设计

### 🔧 性能优化
- 提升数据处理速度
- 优化内存使用
- 改进API调用效率
- 缓存机制优化

## 🔧 开发环境设置

### 环境要求
- Python 3.8+
- Git
- 文本编辑器（推荐VS Code）

### 本地开发
```bash
# 1. 克隆仓库
git clone https://github.com/haoge10241024/TradingAgents_for_Futures.git
cd TradingAgents_for_Futures

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装开发依赖
pip install pytest flake8 black isort

# 5. 配置API密钥
cp 期货TradingAgents系统_配置文件.example.json 期货TradingAgents系统_配置文件.json
# 编辑配置文件，填入您的API密钥

# 6. 运行测试
pytest

# 7. 启动开发服务器
python 启动系统.py
```

## 📋 代码规范

### Python代码风格
- 遵循PEP 8规范
- 使用4个空格缩进
- 行长度不超过120字符
- 使用有意义的变量名

### 提交信息规范
使用以下格式：
```
类型(范围): 简短描述

详细描述（可选）

相关Issue: #123
```

类型包括：
- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建过程或辅助工具的变动

### 示例
```
feat(analysis): 添加新的技术指标分析模块

- 添加RSI指标计算
- 添加MACD指标分析
- 更新技术分析报告生成

相关Issue: #45
```

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_analysis.py

# 生成覆盖率报告
pytest --cov=qihuo --cov-report=html
```

### 编写测试
- 为新功能编写单元测试
- 测试覆盖率应达到80%以上
- 使用描述性的测试名称

## 📤 提交Pull Request

### 1. 提交更改
```bash
git add .
git commit -m "feat: 添加新功能"
git push origin feature/您的功能名称
```

### 2. 创建Pull Request
1. 访问您的Fork仓库
2. 点击 "New Pull Request"
3. 选择正确的分支
4. 填写PR描述
5. 等待代码审查

### PR描述模板
```markdown
## 📝 描述
简要描述您的更改

## 🔧 更改类型
- [ ] Bug修复
- [ ] 新功能
- [ ] 文档更新
- [ ] 性能优化
- [ ] 其他

## 🧪 测试
- [ ] 已运行测试
- [ ] 添加了新测试
- [ ] 所有测试通过

## 📸 截图（如适用）
添加界面截图或图表

## 🔗 相关Issue
关闭 #123
```

## 🔍 代码审查

### 审查要点
- 代码质量和可读性
- 功能正确性
- 性能影响
- 安全性考虑
- 文档完整性

### 审查流程
1. 自动检查（CI/CD）
2. 人工审查
3. 测试验证
4. 合并代码

## 🎯 项目优先级

### 高优先级
- 🐛 关键Bug修复
- 🔒 安全性问题
- 📊 数据准确性
- 🚀 性能优化

### 中优先级
- ✨ 新功能开发
- 🎨 界面改进
- 📖 文档完善
- 🔧 工具优化

### 低优先级
- 🎨 代码重构
- 📝 注释完善
- 🧪 测试覆盖
- 📊 统计信息

## 💡 贡献建议

### 新手友好
- 文档改进
- 测试编写
- Bug修复
- 界面优化

### 中级开发者
- 新功能开发
- 性能优化
- 代码重构
- 工具开发

### 高级开发者
- 架构设计
- 核心算法
- 系统集成
- 安全加固

## 🏆 贡献者认可

### 贡献者徽章
- 🥇 核心贡献者
- 🥈 活跃贡献者
- 🥉 新贡献者

### 认可方式
- README中的贡献者列表
- Release notes中的致谢
- GitHub贡献者统计
- 特殊贡献者徽章

## 📞 获取帮助

### 联系方式
- 💬 [GitHub Discussions](https://github.com/haoge10241024/TradingAgents_for_Futures/discussions)
- 📧 邮箱：953534947@qq.com
- 🐛 [Issues](https://github.com/haoge10241024/TradingAgents_for_Futures/issues)

### 常见问题
- 查看 [FAQ](https://github.com/haoge10241024/TradingAgents_for_Futures/wiki/FAQ)
- 阅读 [文档](https://github.com/haoge10241024/TradingAgents_for_Futures/wiki)
- 搜索 [Issues](https://github.com/haoge10241024/TradingAgents_for_Futures/issues)

## 📄 许可证

通过贡献代码，您同意您的贡献将在MIT许可证下发布。

## 🙏 感谢

感谢所有贡献者的努力，让这个项目变得更好！

---

**⭐ 如果这个项目对您有帮助，请给我们一个Star！**
