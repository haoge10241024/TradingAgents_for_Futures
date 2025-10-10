# API密钥配置指南

## ⚠️ 重要提醒

本系统需要配置API密钥才能正常运行。

## 📋 需要的API密钥

### 1. DeepSeek API（必需）

DeepSeek是本系统的核心AI引擎，用于所有智能分析功能。

#### 获取步骤

1. **访问DeepSeek平台**
   - 网址: https://platform.deepseek.com/
   - 如果还没有账号，点击"注册"

2. **注册账号**
   - 填写邮箱和密码
   - 验证邮箱
   - 完成注册

3. **充值（如果需要）**
   - 登录后进入"账户中心"
   - DeepSeek价格非常实惠：
     - deepseek-chat: ¥1/百万tokens（输入）
     - deepseek-reasoner: ¥4/百万tokens（输入）
   - 建议首次充值¥20-50元，可用很久

4. **创建API密钥**
   - 进入"API Keys"页面
   - 点击"Create new secret key"
   - 给密钥起个名字（如：期货分析系统）
   - 复制生成的密钥（格式：`sk-xxxxxxxxxxxxxx`）
   - **重要**：密钥只显示一次，请立即保存！

5. **配置到系统**
   ```bash
   # 方法1：编辑JSON配置文件
   复制 期货TradingAgents系统_配置文件.example.json
   为   期货TradingAgents系统_配置文件.json
   
   # 找到这一行并填入密钥：
   "api_key": "sk-你复制的密钥粘贴在这里"
   
   # 方法2：编辑Python配置文件
   复制 config.example.py 为 config.py
   
   # 找到这一行并填入密钥：
   DEEPSEEK_API_KEY = "sk-你复制的密钥粘贴在这里"
   ```

### 2. Serper API（可选，用于新闻搜索）

如果需要实时新闻分析功能，可配置Serper API。

#### 获取步骤

1. **访问Serper官网**
   - 网址: https://serper.dev/

2. **注册账号**
   - 使用Google账号快速登录
   - 或使用邮箱注册

3. **获取免费额度**
   - 新用户自动获得2,500次免费搜索
   - 足够初期使用

4. **获取API密钥**
   - 登录后在Dashboard找到API Key
   - 复制密钥

5. **配置到系统**
   ```json
   // 在 期货TradingAgents系统_配置文件.json 中：
   "serper": {
     "api_key": "你的Serper密钥"
   }
   ```

## 🔧 配置步骤详解

### 步骤1：复制配置模板

```bash
# 在项目目录下执行

# 方式A：使用JSON配置（推荐）
cp 期货TradingAgents系统_配置文件.example.json 期货TradingAgents系统_配置文件.json

# 方式B：使用Python配置
cp config.example.py config.py
```

### 步骤2：编辑配置文件

#### JSON配置方式

打开 `期货TradingAgents系统_配置文件.json`，修改以下部分：

```json
{
  "api_settings": {
    "deepseek": {
      "api_key": "sk-在这里粘贴你的DeepSeek密钥",
      "base_url": "https://api.deepseek.com/v1",
      "model": "deepseek-chat",
      "reasoning_model": "deepseek-reasoner"
    },
    "serper": {
      "api_key": "在这里粘贴你的Serper密钥（可选）"
    }
  }
}
```

#### Python配置方式

打开 `config.py`，修改以下行：

```python
# DeepSeek API配置（必需）
DEEPSEEK_API_KEY = "sk-在这里粘贴你的DeepSeek密钥"

# Serper API配置（可选）
SERPER_API_KEY = "在这里粘贴你的Serper密钥"
```

### 步骤3：验证配置

运行测试脚本验证API密钥是否正确：

```python
# test_api_config.py
from pathlib import Path
import json

# 读取配置
config_file = Path("期货TradingAgents系统_配置文件.json")
if config_file.exists():
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    api_key = config['api_settings']['deepseek']['api_key']
    
    if api_key.startswith('sk-') and len(api_key) > 20:
        print("✓ DeepSeek API密钥格式正确")
    else:
        print("✗ DeepSeek API密钥格式错误")
else:
    print("✗ 配置文件不存在，请从模板复制")
```

## 💰 费用说明

### DeepSeek费用

DeepSeek的价格非常实惠，是同类AI服务中最便宜的：

| 模型 | 输入价格 | 输出价格 | 适用场景 |
|------|---------|---------|---------|
| deepseek-chat | ¥1/百万tokens | ¥2/百万tokens | 常规分析，速度快 |
| deepseek-reasoner | ¥4/百万tokens | ¥8/百万tokens | 深度推理，准确度高 |

**实际使用估算**：
- 单次完整分析（6个模块）：约0.05-0.1元
- 多空辩论（2轮）：约0.1-0.2元
- 每天分析5个品种：约1-2元
- **月度费用预估**：¥30-60元

### Serper费用

- 免费额度：2,500次搜索
- 付费计划：$50/月起
- 新闻分析可选，不是必需

## 🔒 安全建议

### 1. 保护API密钥

- ✅ **切勿**将API密钥硬编码在代码中
- ✅ **切勿**将包含密钥的配置文件上传到GitHub
- ✅ **切勿**在公共场合分享密钥
- ✅ **定期**更换API密钥（建议每3-6个月）

### 2. 使用.gitignore

系统已配置`.gitignore`自动排除配置文件：

```gitignore
# API密钥配置文件
config.py
*.yaml
!core.example.yaml
期货TradingAgents系统_配置文件.json
```

### 3. 环境变量（推荐）

更安全的方式是使用环境变量：

```bash
# Linux/macOS
export DEEPSEEK_API_KEY="sk-your-key-here"
export SERPER_API_KEY="your-serper-key"

# Windows
set DEEPSEEK_API_KEY=sk-your-key-here
set SERPER_API_KEY=your-serper-key
```

然后在代码中读取：

```python
import os
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
```

### 4. 监控使用量

定期检查API使用情况：

- DeepSeek平台：https://platform.deepseek.com/usage
- 设置使用量提醒
- 发现异常立即更换密钥

## ❓ 常见问题

### Q1: 配置后仍提示API错误？

**检查项**：
1. 密钥是否正确复制（无多余空格）
2. 密钥是否已过期
3. DeepSeek账户是否有余额
4. 网络连接是否正常

**解决方案**：
```python
# 测试API连接
import requests

api_key = "你的密钥"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.post(
    "https://api.deepseek.com/v1/chat/completions",
    headers=headers,
    json={
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": "测试"}]
    }
)

print(response.status_code)  # 应该是200
```

### Q2: 如何切换到其他AI服务？

系统主要支持DeepSeek，如需使用其他服务（如OpenAI、Claude），需要修改：
- `qihuo/llm/deepseek_client.py`
- 调整API调用接口

### Q3: 没有API密钥可以使用吗？

不可以。AI分析是系统核心功能，必须配置DeepSeek API。但您可以：
- 只使用数据展示功能（关闭AI分析）
- 使用免费的开源模型（需自行部署）

### Q4: 配置文件丢失怎么办？

```bash
# 重新从模板创建
cp 期货TradingAgents系统_配置文件.example.json 期货TradingAgents系统_配置文件.json

# 填入密钥即可
```

### Q5: 可以团队共享API密钥吗？

**不推荐**。原因：
- 安全风险：任何人离职都需要更换
- 费用管理：无法区分个人使用量
- 配额限制：可能相互影响

**建议**：每人注册独立账号。

## 📚 相关文档

- [快速开始指南](快速开始指南.md) - 系统快速启动
- [配置详解](CONFIGURATION.md) - 更多配置选项
- [安装指南](INSTALL.md) - 完整安装步骤

## 🆘 获取帮助

遇到API配置问题？

1. 查看日志文件：`qihuo/logs/trading_agents.log`
2. 运行测试脚本验证配置
3. 在GitHub提交Issue
4. 查看DeepSeek官方文档：https://platform.deepseek.com/docs

---

**下一步**：配置完成后，请阅读 [本地数据配置指南](本地数据配置指南.md)

