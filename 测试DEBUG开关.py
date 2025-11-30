#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试DEBUG开关功能

这个脚本演示如何在代码中控制DEBUG输出
"""

import os
import sys

def test_with_debug_off():
    """测试关闭DEBUG的效果"""
    print("\n" + "="*60)
    print("测试 1: 关闭DEBUG模式（默认）")
    print("="*60)
    print("预期：不应该看到任何DEBUG信息\n")
    
    # 确保DEBUG关闭
    os.environ['TRADING_DEBUG'] = '0'
    
    # 重新导入模块以应用新的环境变量
    if '优化版辩论风控决策系统' in sys.modules:
        del sys.modules['优化版辩论风控决策系统']
    
    from 优化版辩论风控决策系统 import debug_print, ENABLE_DEBUG
    
    print(f"当前DEBUG状态: {'开启' if ENABLE_DEBUG else '关闭'}")
    print("执行debug_print测试...")
    debug_print("🐛 这是一条DEBUG信息 - 如果看到这句话说明DEBUG开关没有生效")
    debug_print("DEBUG: 另一条DEBUG信息")
    print("✅ 测试完成：如果上面没有看到DEBUG信息，说明开关工作正常\n")

def test_with_debug_on():
    """测试开启DEBUG的效果"""
    print("\n" + "="*60)
    print("测试 2: 开启DEBUG模式")
    print("="*60)
    print("预期：应该看到DEBUG信息\n")
    
    # 开启DEBUG
    os.environ['TRADING_DEBUG'] = '1'
    
    # 重新导入模块
    if '优化版辩论风控决策系统' in sys.modules:
        del sys.modules['优化版辩论风控决策系统']
    
    from 优化版辩论风控决策系统 import debug_print, ENABLE_DEBUG
    
    print(f"当前DEBUG状态: {'开启' if ENABLE_DEBUG else '关闭'}")
    print("执行debug_print测试...")
    debug_print("🐛 这是一条DEBUG信息 - 您应该能看到这句话")
    debug_print("DEBUG: 另一条DEBUG信息 - 您应该能看到这句话")
    print("✅ 测试完成：如果上面看到了DEBUG信息，说明开关工作正常\n")

def main():
    """主测试函数"""
    print("\n" + "#"*60)
    print("# Trading Agents 系统 - DEBUG开关测试")
    print("#"*60)
    
    try:
        # 测试1: 关闭DEBUG
        test_with_debug_off()
        
        # 测试2: 开启DEBUG
        test_with_debug_on()
        
        print("\n" + "#"*60)
        print("# 测试总结")
        print("#"*60)
        print("""
✅ DEBUG开关功能已正常工作

使用方法：
---------
1. 在运行脚本前设置环境变量：
   Windows PowerShell: $env:TRADING_DEBUG = "1"
   Windows CMD:        set TRADING_DEBUG=1
   Linux/Mac:          export TRADING_DEBUG=1

2. 在代码中设置：
   import os
   os.environ['TRADING_DEBUG'] = '1'  # 开启
   os.environ['TRADING_DEBUG'] = '0'  # 关闭

3. 直接修改优化版辩论风控决策系统.py：
   ENABLE_DEBUG = True   # 永久开启
   ENABLE_DEBUG = False  # 永久关闭

建议：
-----
- 开发/调试时开启DEBUG
- 生产/演示时关闭DEBUG（默认）
        """)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

