#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件诊断脚本 - 帮助用户找出配置问题
"""
import json
import sys
from pathlib import Path

def diagnose_config():
    """诊断配置文件"""
    print("=" * 70)
    print("期货TradingAgents系统 - 配置诊断工具")
    print("=" * 70)
    print()
    
    # 1. 检查当前工作目录
    current_dir = Path.cwd()
    print(f"[1] 当前工作目录: {current_dir}")
    print()
    
    # 2. 查找配置文件
    config_file = "期货TradingAgents系统_配置文件.json"
    config_path = Path(config_file)
    
    print(f"[2] 查找配置文件: {config_file}")
    print(f"    完整路径: {config_path.absolute()}")
    
    if config_path.exists():
        print("    [OK] 配置文件存在")
    else:
        print("    [ERROR] 配置文件不存在！")
        print()
        print("    可能的原因:")
        print("    1. 配置文件不在当前目录")
        print("    2. 文件名拼写错误")
        print("    3. 还没有创建配置文件")
        print()
        print("    解决方法:")
        print("    1. 确保在项目根目录运行此脚本")
        print("    2. 复制 期货TradingAgents系统_配置文件.example.json")
        print("    3. 重命名为 期货TradingAgents系统_配置文件.json")
        print("    4. 编辑文件，填入您的API密钥")
        print()
        return False
    print()
    
    # 3. 读取配置文件
    print(f"[3] 读取配置文件...")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("    [OK] 配置文件读取成功")
    except json.JSONDecodeError as e:
        print(f"    [ERROR] JSON格式错误: {e}")
        print()
        print("    可能的原因:")
        print("    1. JSON格式不正确（缺少逗号、引号等）")
        print("    2. 文件编码问题")
        print()
        print("    解决方法:")
        print("    1. 使用JSON验证工具检查格式")
        print("    2. 确保文件是UTF-8编码")
        return False
    except Exception as e:
        print(f"    [ERROR] 读取失败: {e}")
        return False
    print()
    
    # 4. 检查API配置结构
    print(f"[4] 检查配置结构...")
    
    if "api_settings" not in config:
        print("    [ERROR] 缺少 'api_settings' 配置项")
        return False
    print("    [OK] 找到 'api_settings'")
    
    if "deepseek" not in config["api_settings"]:
        print("    [ERROR] 缺少 'api_settings.deepseek' 配置项")
        return False
    print("    [OK] 找到 'api_settings.deepseek'")
    
    if "api_key" not in config["api_settings"]["deepseek"]:
        print("    [ERROR] 缺少 'api_settings.deepseek.api_key' 配置项")
        return False
    print("    [OK] 找到 'api_settings.deepseek.api_key'")
    print()
    
    # 5. 检查API密钥
    print(f"[5] 检查API密钥...")
    api_key = config["api_settings"]["deepseek"]["api_key"]
    
    print(f"    API密钥值: {api_key[:10]}...{api_key[-8:]}")
    print(f"    API密钥长度: {len(api_key)}")
    
    # 检查是否是占位符
    if api_key in ["YOUR_DEEPSEEK_API_KEY_HERE", "YOUR_API_KEY_HERE", "sk-your-api-key-here"]:
        print("    [ERROR] API密钥还是占位符，没有填写真实密钥！")
        print()
        print("    解决方法:")
        print("    1. 访问 https://platform.deepseek.com/api_keys")
        print("    2. 创建API密钥")
        print("    3. 复制密钥（格式: sk-xxxxxxxxxx）")
        print("    4. 替换配置文件中的 'YOUR_DEEPSEEK_API_KEY_HERE'")
        return False
    
    # 检查格式
    if not api_key.startswith("sk-"):
        print("    [WARN] API密钥格式异常：不是以 'sk-' 开头")
        print("    请确认这是正确的DeepSeek API密钥")
    else:
        print("    [OK] API密钥格式正确（sk- 开头）")
    
    if len(api_key) < 20:
        print("    [WARN] API密钥长度异常：可能不完整")
    else:
        print("    [OK] API密钥长度正常")
    print()
    
    # 6. 显示完整配置
    print(f"[6] 配置信息摘要:")
    print(f"    Base URL: {config['api_settings']['deepseek'].get('base_url', 'N/A')}")
    print(f"    Model: {config['api_settings']['deepseek'].get('model', 'N/A')}")
    print(f"    Reasoning Model: {config['api_settings']['deepseek'].get('reasoning_model', 'N/A')}")
    print()
    
    # 7. 测试API密钥（可选）
    print(f"[7] 是否需要测试API密钥？(y/n): ", end='')
    try:
        choice = input().strip().lower()
        if choice == 'y':
            print()
            print("    正在测试API密钥...")
            import httpx
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "测试"}],
                "max_tokens": 10
            }
            
            try:
                with httpx.Client(timeout=30) as client:
                    response = client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        print("    [OK] API密钥有效！可以正常使用")
                        return True
                    elif response.status_code == 401:
                        print("    [ERROR] API密钥无效（401认证失败）")
                        print(f"    响应: {response.text[:200]}")
                        return False
                    else:
                        print(f"    [WARN] API返回状态码: {response.status_code}")
                        print(f"    响应: {response.text[:200]}")
                        return False
            except Exception as e:
                print(f"    [ERROR] 测试失败: {e}")
                return False
    except KeyboardInterrupt:
        print("\n    跳过测试")
    
    print()
    print("=" * 70)
    print("[OK] 配置文件结构正确")
    print("     如果系统仍然报错，请:")
    print("     1. 完全关闭并重启系统")
    print("     2. 确保在项目根目录启动系统")
    print("     3. 删除 __pycache__ 和 qihuo/cache/ 清除缓存")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    try:
        diagnose_config()
    except Exception as e:
        print(f"\n[ERROR] 诊断过程出错: {e}")
        import traceback
        traceback.print_exc()

