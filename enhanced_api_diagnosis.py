#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版API配置诊断工具
专门诊断"API密钥正确但系统仍使用占位符"的问题
"""

import json
import os
import sys
from pathlib import Path
import requests

print("=" * 80)
print("🔍 增强版API配置诊断工具 v2.0")
print("=" * 80)
print()

# 第一步：检查工作目录
print("【步骤1】检查当前工作目录")
print("-" * 80)
current_dir = Path.cwd()
print(f"✅ 当前工作目录: {current_dir}")
print()

# 第二步：查找所有可能的配置文件
print("【步骤2】查找所有配置文件")
print("-" * 80)

config_files_to_check = [
    "期货TradingAgents系统_配置文件.json",
    "期货TradingAgents系统_配置文件.example.json",
    "config.json",
    "config.py"
]

found_configs = []
for config_name in config_files_to_check:
    config_path = current_dir / config_name
    if config_path.exists():
        found_configs.append({
            "name": config_name,
            "path": config_path,
            "size": config_path.stat().st_size
        })
        print(f"✅ 发现: {config_name}")
        print(f"   路径: {config_path}")
        print(f"   大小: {config_path.stat().st_size} 字节")
        print()

if not found_configs:
    print("❌ 错误：未找到任何配置文件！")
    print()
    print("💡 解决方案：")
    print("   1. 确保您在项目根目录运行此脚本")
    print("   2. 创建配置文件：")
    print("      copy 期货TradingAgents系统_配置文件.example.json 期货TradingAgents系统_配置文件.json")
    print("   3. 编辑配置文件，填入您的API密钥")
    sys.exit(1)

# 第三步：检查主配置文件内容
print("【步骤3】检查主配置文件内容")
print("-" * 80)

main_config_path = current_dir / "期货TradingAgents系统_配置文件.json"

if not main_config_path.exists():
    print("❌ 错误：主配置文件不存在！")
    print(f"   期望路径: {main_config_path}")
    print()
    print("💡 解决方案：")
    print("   运行以下命令创建配置文件：")
    print("   copy 期货TradingAgents系统_配置文件.example.json 期货TradingAgents系统_配置文件.json")
    sys.exit(1)

try:
    with open(main_config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    print(f"✅ 配置文件读取成功")
    print(f"   文件路径: {main_config_path}")
    print()
except json.JSONDecodeError as e:
    print(f"❌ 错误：配置文件JSON格式错误！")
    print(f"   错误信息: {e}")
    print()
    print("💡 解决方案：")
    print("   1. 使用JSON验证工具检查文件格式")
    print("   2. 确保所有引号、逗号、括号匹配")
    print("   3. 删除多余的注释（JSON不支持//注释）")
    sys.exit(1)
except Exception as e:
    print(f"❌ 错误：无法读取配置文件！")
    print(f"   错误信息: {e}")
    sys.exit(1)

# 第四步：检查API密钥配置
print("【步骤4】检查API密钥配置")
print("-" * 80)

# 检查DeepSeek API密钥
deepseek_key = None
try:
    deepseek_key = config.get('api_settings', {}).get('deepseek', {}).get('api_key')
    
    if not deepseek_key:
        print("❌ 错误：配置文件中未找到DeepSeek API密钥！")
        print()
        print("💡 解决方案：")
        print("   在配置文件的 api_settings -> deepseek -> api_key 中填入您的密钥")
        sys.exit(1)
    
    # 检查是否为占位符
    placeholders = [
        "YOUR_DEEPSEEK_API_KEY_HERE",
        "YOUR_API_KEY_HERE",
        "sk-your-api-key-here",
        "****HERE"
    ]
    
    if deepseek_key in placeholders:
        print(f"❌ 错误：API密钥仍为占位符！")
        print(f"   当前值: {deepseek_key}")
        print()
        print("💡 解决方案：")
        print("   1. 访问 https://platform.deepseek.com/")
        print("   2. 获取您的API密钥（格式：sk-xxxxxxxxxx）")
        print("   3. 在配置文件中替换占位符为真实密钥")
        sys.exit(1)
    
    # 检查密钥格式
    if not deepseek_key.startswith('sk-'):
        print(f"⚠️  警告：API密钥格式可能不正确")
        print(f"   当前值: {deepseek_key[:10]}...")
        print(f"   DeepSeek密钥通常以 'sk-' 开头")
        print()
    
    print(f"✅ DeepSeek API密钥已配置")
    print(f"   密钥前缀: {deepseek_key[:10]}...")
    print(f"   密钥长度: {len(deepseek_key)} 字符")
    print()
    
except Exception as e:
    print(f"❌ 错误：无法提取API密钥！")
    print(f"   错误信息: {e}")
    sys.exit(1)

# 第五步：测试API密钥有效性
print("【步骤5】测试API密钥有效性")
print("-" * 80)

try:
    print("正在向DeepSeek API发送测试请求...")
    
    headers = {
        "Authorization": f"Bearer {deepseek_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "max_tokens": 10
    }
    
    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers=headers,
        json=data,
        timeout=30
    )
    
    if response.status_code == 200:
        print("✅ API密钥有效！测试请求成功")
        print()
    elif response.status_code == 401:
        print("❌ 错误：API密钥无效或已过期！")
        print(f"   响应: {response.text}")
        print()
        print("💡 解决方案：")
        print("   1. 访问 https://platform.deepseek.com/ 检查密钥是否有效")
        print("   2. 确认账户余额是否充足")
        print("   3. 尝试重新生成API密钥")
        sys.exit(1)
    else:
        print(f"⚠️  警告：API返回异常状态码 {response.status_code}")
        print(f"   响应: {response.text}")
        print()
        
except requests.exceptions.Timeout:
    print("⚠️  警告：API请求超时（可能是网络问题）")
    print()
except Exception as e:
    print(f"⚠️  警告：API测试请求失败")
    print(f"   错误信息: {e}")
    print()

# 第六步：模拟系统加载配置
print("【步骤6】模拟系统加载配置过程")
print("-" * 80)

print("正在模拟系统配置加载...")

# 导入系统的配置类
try:
    sys.path.insert(0, str(current_dir))
    from 期货TradingAgents系统_基础架构 import FuturesTradingAgentsConfig
    
    # 创建配置实例（与系统实际运行时相同）
    system_config = FuturesTradingAgentsConfig()
    
    # 获取系统实际加载的API密钥
    loaded_key = system_config.get('api_settings.deepseek.api_key')
    
    print(f"✅ 系统配置加载成功")
    print(f"   系统实际使用的API密钥前缀: {loaded_key[:10]}...")
    print()
    
    # 关键检查：对比文件中的密钥和系统加载的密钥
    if loaded_key != deepseek_key:
        print("🚨 【核心问题发现】")
        print("=" * 80)
        print("❌ 系统实际加载的API密钥与配置文件中的不一致！")
        print()
        print(f"   配置文件中的密钥: {deepseek_key[:10]}...")
        print(f"   系统实际使用的密钥: {loaded_key[:10]}...")
        print()
        print("💡 可能的原因：")
        print("   1. 系统从其他位置加载了配置（检查是否有多个配置文件）")
        print("   2. 环境变量覆盖了配置文件（检查DEEPSEEK_API_KEY环境变量）")
        print("   3. 代码中硬编码了默认值（检查代码中的占位符）")
        print("   4. Python缓存问题（删除__pycache__目录）")
        print()
        print("💡 解决方案：")
        print("   1. 删除所有Python缓存：")
        print("      rmdir /s /q __pycache__")
        print("      del /s /q *.pyc")
        print("   2. 检查并删除其他配置文件（只保留一个）")
        print("   3. 检查环境变量：")
        print("      echo %DEEPSEEK_API_KEY%")
        print("   4. 重启终端/IDE后再试")
        print()
        sys.exit(1)
    else:
        print("✅ 系统加载的API密钥与配置文件一致！")
        print()
        
except ImportError as e:
    print(f"⚠️  无法导入系统配置模块（这是正常的，跳过此步骤）")
    print(f"   错误: {e}")
    print()
except Exception as e:
    print(f"⚠️  配置加载模拟失败")
    print(f"   错误信息: {e}")
    print()

# 第七步：检查环境变量
print("【步骤7】检查环境变量")
print("-" * 80)

env_key = os.getenv("DEEPSEEK_API_KEY")
if env_key:
    print(f"⚠️  发现环境变量 DEEPSEEK_API_KEY")
    print(f"   值: {env_key[:10]}...")
    print()
    
    if env_key in placeholders:
        print("❌ 环境变量中的API密钥是占位符！")
        print()
        print("💡 解决方案：")
        print("   删除或修改环境变量：")
        print("   set DEEPSEEK_API_KEY=")
        print()
    elif env_key != deepseek_key:
        print("⚠️  环境变量中的密钥与配置文件不一致")
        print("   这可能导致系统使用错误的密钥")
        print()
        print("💡 建议：")
        print("   删除环境变量，只使用配置文件：")
        print("   set DEEPSEEK_API_KEY=")
        print()
else:
    print("✅ 未发现DEEPSEEK_API_KEY环境变量（推荐）")
    print()

# 最终报告
print("=" * 80)
print("📋 诊断总结")
print("=" * 80)
print()
print("如果以上所有检查都通过，但系统仍报401错误，请尝试：")
print()
print("1. 清除Python缓存：")
print("   cd 项目根目录")
print("   rmdir /s /q __pycache__")
print("   rmdir /s /q qihuo\\__pycache__")
print("   rmdir /s /q modules\\__pycache__")
print()
print("2. 重启终端/PowerShell/命令提示符")
print()
print("3. 确保从项目根目录运行系统：")
print("   cd D:\\path\\to\\TradingAgents_for_Futures")
print("   streamlit run 期货TradingAgents系统_专业完整版界面.py")
print()
print("4. 如果问题仍然存在，请运行：")
print("   python -c \"from 期货TradingAgents系统_基础架构 import FuturesTradingAgentsConfig; c=FuturesTradingAgentsConfig(); print(c.get('api_settings.deepseek.api_key'))\"")
print("   查看系统实际加载的密钥")
print()
print("5. 最后的方案：重新下载项目")
print("   git clone https://github.com/haoge10241024/TradingAgents_for_Futures.git")
print("   cd TradingAgents_for_Futures")
print("   copy 期货TradingAgents系统_配置文件.example.json 期货TradingAgents系统_配置文件.json")
print("   # 编辑配置文件，填入API密钥")
print("   streamlit run 期货TradingAgents系统_专业完整版界面.py")
print()
print("=" * 80)
print("✅ 诊断完成")
print("=" * 80)

