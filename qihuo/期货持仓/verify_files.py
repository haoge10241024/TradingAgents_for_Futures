#!/usr/bin/env python3
"""
期货持仓分析系统 - 文件完整性验证脚本
验证所有必需文件是否存在并可正常导入
"""

import os
import sys
from pathlib import Path

def check_file_exists(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (缺失)")
        return False

def check_directory_exists(dirpath, description):
    """检查目录是否存在"""
    if os.path.exists(dirpath) and os.path.isdir(dirpath):
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description}: {dirpath} (缺失)")
        return False

def main():
    """主验证函数"""
    print("=" * 60)
    print("期货持仓分析系统 - 文件完整性验证")
    print("=" * 60)
    
    all_good = True
    
    # 检查根目录文件
    print("\n📁 根目录文件:")
    files_to_check = [
        ("README.md", "项目说明文档"),
        ("LICENSE", "开源许可证"),
        ("CHANGELOG.md", "更新日志"),
        ("CONTRIBUTING.md", "贡献指南"),
        ("GITHUB_UPLOAD_GUIDE.md", "GitHub上传指南"),
        ("FILE_LIST.md", "文件清单"),
    ]
    
    for filename, desc in files_to_check:
        if not check_file_exists(filename, desc):
            all_good = False
    
    # 检查配置文件
    print("\n⚙️ 配置文件:")
    config_files = [
        ("requirements.txt", "生产环境依赖"),
        ("requirements-dev.txt", "开发环境依赖"),
        (".python-version", "Python版本"),
        (".gitignore", "Git忽略配置"),
    ]
    
    for filename, desc in config_files:
        if not check_file_exists(filename, desc):
            all_good = False
    
    # 检查核心代码文件
    print("\n🐍 核心代码文件:")
    code_files = [
        ("streamlit_app.py", "主应用程序"),
        ("cloud_data_fetcher.py", "云端数据获取器"),
        ("futures_analyzer.py", "分析引擎"),
        ("performance_optimizer.py", "性能优化模块"),
        ("config.py", "系统配置"),
        ("utils.py", "工具函数"),
        ("app.py", "启动脚本"),
    ]
    
    for filename, desc in code_files:
        if not check_file_exists(filename, desc):
            all_good = False
    
    # 检查测试文件
    print("\n🧪 测试文件:")
    test_files = [
        ("test_auto_skip.py", "自动跳过功能测试"),
        ("test_system.py", "系统功能测试"),
    ]
    
    for filename, desc in test_files:
        if not check_file_exists(filename, desc):
            all_good = False
    
    # 检查目录结构
    print("\n📂 目录结构:")
    directories = [
        (".streamlit", "Streamlit配置目录"),
        (".github", "GitHub配置目录"),
        (".github/workflows", "GitHub Actions目录"),
        ("docs", "文档目录"),
        ("data", "数据目录"),
    ]
    
    for dirname, desc in directories:
        if not check_directory_exists(dirname, desc):
            all_good = False
    
    # 检查特定配置文件
    print("\n🔧 特定配置文件:")
    specific_files = [
        (".streamlit/config.toml", "Streamlit配置"),
        (".github/workflows/ci.yml", "CI/CD工作流"),
        ("data/.gitkeep", "数据目录保持文件"),
    ]
    
    for filename, desc in specific_files:
        if not check_file_exists(filename, desc):
            all_good = False
    
    # 检查文档文件
    print("\n📚 文档文件:")
    doc_files = [
        ("docs/QUICK_START_GUIDE.md", "快速开始指南"),
        ("docs/AUTO_SKIP_FEATURES.md", "自动跳过功能详解"),
        ("docs/API_REFERENCE.md", "API参考文档"),
        ("docs/FAQ.md", "常见问题解答"),
    ]
    
    for filename, desc in doc_files:
        if not check_file_exists(filename, desc):
            all_good = False
    
    # 尝试导入核心模块
    print("\n🔍 模块导入测试:")
    try:
        import streamlit
        print("✅ streamlit 导入成功")
    except ImportError as e:
        print(f"❌ streamlit 导入失败: {e}")
        all_good = False
    
    try:
        import pandas
        print("✅ pandas 导入成功")
    except ImportError as e:
        print(f"❌ pandas 导入失败: {e}")
        all_good = False
    
    try:
        import akshare
        print("✅ akshare 导入成功")
    except ImportError as e:
        print(f"❌ akshare 导入失败: {e}")
        all_good = False
    
    # 检查本地模块
    try:
        sys.path.insert(0, '.')
        import config
        print(f"✅ config 模块导入成功 (版本: {config.VERSION})")
    except ImportError as e:
        print(f"❌ config 模块导入失败: {e}")
        all_good = False
    
    try:
        import cloud_data_fetcher
        print("✅ cloud_data_fetcher 模块导入成功")
    except ImportError as e:
        print(f"❌ cloud_data_fetcher 模块导入失败: {e}")
        all_good = False
    
    # 最终结果
    print("\n" + "=" * 60)
    if all_good:
        print("🎉 所有文件验证通过！系统已准备好部署到GitHub和Streamlit Cloud")
        print("📋 文件统计:")
        
        # 统计文件数量
        total_files = 0
        for root, dirs, files in os.walk('.'):
            total_files += len(files)
        
        print(f"   - 总文件数: {total_files}")
        print(f"   - 代码文件: 8个")
        print(f"   - 配置文件: 4个") 
        print(f"   - 文档文件: 8个")
        print(f"   - 测试文件: 2个")
        
        print("\n🚀 下一步操作:")
        print("   1. 将整个目录上传到GitHub")
        print("   2. 在Streamlit Cloud中连接仓库")
        print("   3. 选择 streamlit_app.py 作为主文件")
        print("   4. 等待自动部署完成")
        
    else:
        print("⚠️ 发现缺失文件，请检查并补充完整")
        
    print("=" * 60)
    return all_good

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 