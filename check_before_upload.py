#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub上传前安全检查脚本
运行此脚本确保不会泄露敏感信息
"""
import os
import re
from pathlib import Path

def check_sensitive_info():
    """检查敏感信息"""
    print("=" * 60)
    print("GitHub上传前安全检查")
    print("=" * 60)
    
    issues = []
    warnings = []
    root = Path(".")
    
    print("\n检查1: API密钥配置文件...")
    # 1. 检查API密钥配置文件是否存在
    if (root / "config.py").exists():
        issues.append("config.py 存在（应删除或重命名为config.example.py）")
    else:
        print("  [OK] config.py 不存在")
    
    if (root / "期货TradingAgents系统_配置文件.json").exists():
        issues.append("期货TradingAgents系统_配置文件.json 存在（应删除）")
    else:
        print("  [OK] 配置文件.json 不存在")
    
    print("\n检查2: 模板文件...")
    # 2. 检查模板文件是否存在
    if not (root / "config.example.py").exists():
        warnings.append("config.example.py 不存在（建议提供）")
    else:
        print("  [OK] config.example.py 存在")
    
    if not (root / "期货TradingAgents系统_配置文件.example.json").exists():
        warnings.append("期货TradingAgents系统_配置文件.example.json 不存在（建议提供）")
    else:
        print("  [OK] 配置文件模板存在")
    
    print("\n检查3: 搜索API密钥...")
    # 3. 搜索可能的API密钥
    api_key_pattern = re.compile(r'sk-[a-zA-Z0-9]{20,}')
    serper_pattern = re.compile(r'[a-f0-9]{40,}')
    
    for py_file in root.rglob("*.py"):
        if '.git' in str(py_file) or '__pycache__' in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            if api_key_pattern.search(content):
                if 'example' not in py_file.name.lower():
                    issues.append(f"{py_file} 可能包含DeepSeek API密钥")
        except Exception:
            pass
    
    for json_file in root.rglob("*.json"):
        if '.git' in str(json_file):
            continue
        try:
            content = json_file.read_text(encoding='utf-8', errors='ignore')
            if api_key_pattern.search(content):
                if 'example' not in json_file.name.lower():
                    issues.append(f"{json_file} 可能包含API密钥")
        except Exception:
            pass
    
    if not any("API密钥" in issue for issue in issues):
        print("  [OK] 未发现API密钥")
    
    print("\n检查4: 绝对路径...")
    # 4. 检查绝对路径
    path_patterns = [
        (r'[CD]:\\', 'Windows绝对路径'),
        (r'/Users/[^/]+', 'macOS用户目录'),
        (r'/home/[^/]+', 'Linux用户目录'),
    ]
    
    for py_file in root.rglob("*.py"):
        if '.git' in str(py_file) or '__pycache__' in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            for pattern, desc in path_patterns:
                if re.search(pattern, content):
                    # 排除注释和文档字符串中的路径
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if re.search(pattern, line) and not line.strip().startswith('#'):
                            if '"' in line or "'" in line:  # 可能是实际的路径字符串
                                warnings.append(f"{py_file}:{i} 包含{desc}")
                                break
        except Exception:
            pass
    
    if not warnings or not any("路径" in w for w in warnings):
        print("  [OK] 未发现硬编码路径")
    
    print("\n检查5: .gitignore配置...")
    # 5. 检查.gitignore
    gitignore_file = root / ".gitignore"
    if not gitignore_file.exists():
        issues.append(".gitignore 文件不存在")
    else:
        gitignore_content = gitignore_file.read_text(encoding='utf-8')
        required_patterns = [
            'config.py',
            '配置文件.json',
            '*.log',
        ]
        for pattern in required_patterns:
            if pattern not in gitignore_content:
                warnings.append(f".gitignore 中未找到 {pattern}")
        
        if not warnings or not any(".gitignore" in w for w in warnings):
            print("  [OK] .gitignore 配置正确")
    
    print("\n检查6: 大文件...")
    # 6. 检查大文件
    large_files = []
    for file in root.rglob("*"):
        if file.is_file() and '.git' not in str(file):
            try:
                size_mb = file.stat().st_size / (1024 * 1024)
                if size_mb > 10:
                    large_files.append((str(file), f"{size_mb:.1f}MB"))
            except Exception:
                pass
    
    if large_files:
        print("  [!] 发现大文件（>10MB）：")
        for file, size in large_files[:5]:
            print(f"      - {file}: {size}")
        if len(large_files) > 5:
            print(f"      ... 还有 {len(large_files)-5} 个大文件")
        warnings.append(f"发现 {len(large_files)} 个大文件")
    else:
        print("  [OK] 未发现过大文件")
    
    print("\n检查7: 必需文档...")
    # 7. 检查必需文档
    required_docs = [
        'README.md',
        'requirements.txt',
        'LICENSE',
        '.gitignore',
    ]
    for doc in required_docs:
        if not (root / doc).exists():
            warnings.append(f"缺少 {doc}")
        else:
            print(f"  [OK] {doc} 存在")
    
    # 输出结果
    print("\n" + "=" * 60)
    print("检查结果")
    print("=" * 60)
    
    if issues:
        print("\n[错误] 发现以下严重问题（必须修复）：")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    
    if warnings:
        print("\n[警告] 发现以下问题（建议修复）：")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    if not issues and not warnings:
        print("\n[SUCCESS] 所有检查通过！")
        print("\n可以安全上传到GitHub。")
        print("\n建议的上传步骤：")
        print("  1. git add .")
        print("  2. git commit -m 'Initial commit'")
        print("  3. git push origin main")
        return True
    elif not issues:
        print("\n[PASS] 未发现严重问题，但有一些警告。")
        print("建议修复警告后再上传。")
        return True
    else:
        print("\n[FAIL] 发现严重问题，请修复后再上传！")
        print("\n修复建议：")
        print("  1. 删除包含API密钥的配置文件")
        print("  2. 确保.gitignore正确配置")
        print("  3. 再次运行此检查脚本")
        return False

if __name__ == "__main__":
    success = check_sensitive_info()
    import sys
    sys.exit(0 if success else 1)

