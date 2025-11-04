#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一期货多维数据更新系统 - 修复版本
修复问题:
1. 技术分析数据读取问题
2. 库存数据增减值计算问题
3. 数据更新不完整问题
4. 基差数据质量检查增强
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import time
from typing import Dict, List, Optional, Tuple
import pandas as pd

# 添加模块路径 - 兼容Jupyter环境
try:
    # 在Python脚本中使用__file__
    current_dir = Path(__file__).parent
except NameError:
    # 在Jupyter/IPython环境中使用当前工作目录
    current_dir = Path.cwd()
    
modules_dir = current_dir / "modules"
sys.path.insert(0, str(modules_dir))

# 导入数据检查器和各个更新器
from unified_data_checker import UnifiedDataChecker
from basis_updater import BasisDataUpdater
from inventory_updater import InventoryDataUpdater
from positioning_updater import PositioningDataUpdater
from term_structure_updater import TermStructureUpdater
from technical_updater import TechnicalDataUpdater

class UnifiedFuturesDataUpdaterFixed:
    """统一期货多维数据更新系统 - 修复版本"""
    
    def __init__(self, database_path: str = "qihuo/database"):
        """初始化更新系统"""
        self.database_path = Path(database_path)
        
        # 确保数据库目录存在
        self.database_path.mkdir(parents=True, exist_ok=True)
        
        print(f"🗄️ 数据库路径: {self.database_path}")
        
        # 初始化数据检查器
        self.data_checker = UnifiedDataChecker()
        
        # 初始化各个更新器（传入正确的子目录路径）
        self.updaters = {
            "basis": BasisDataUpdater(str(self.database_path / "basis")),
            "inventory": InventoryDataUpdater(str(self.database_path / "inventory")), 
            "positioning": PositioningDataUpdater(str(self.database_path / "positioning")),
            "term_structure": TermStructureUpdater(str(self.database_path / "term_structure")),
            "technical_analysis": TechnicalDataUpdater(str(self.database_path / "technical_analysis"))
        }
        
        # 更新顺序（基差 → 库存 → 持仓 → 期限结构 → 技术分析）
        self.module_order = ["basis", "inventory", "positioning", "term_structure", "technical_analysis"]
        
        # 初始化统计信息
        self.update_report = {
            "start_time": datetime.now(),
            "target_date": None,
            "modules": {},
            "summary": {
                "total_modules": 0,
                "successful_modules": 0,
                "failed_modules": 0,
                "total_updated_varieties": set(),
                "total_failed_varieties": set(),
                "total_elapsed_time": 0
            }
        }
        
        print("🚀 统一期货多维数据更新系统（修复版）初始化完成")
    
    def show_system_status(self):
        """显示系统当前状态"""
        print("\n" + "="*80)
        print("📊 统一期货多维数据更新系统 - 当前状态")
        print("="*80)
        
        # 获取各板块状态
        status = self.data_checker.get_comprehensive_status()
        
        print(f"📈 各板块数据状态:")
        for module_name, info in status.items():
            if isinstance(info, dict) and 'variety_count' in info:
                print(f"  • {info.get('name', module_name)}: {info['variety_count']} 个品种")
                
                if info.get('date_range') and info['date_range']['start']:
                    start_date = info['date_range']['start'].strftime('%Y-%m-%d')
                    end_date = info['date_range']['end'].strftime('%Y-%m-%d')
                    print(f"    📅 数据范围: {start_date} ~ {end_date}")
                    
                    # 检查数据是否最新
                    today = datetime.now().date()
                    end_date_obj = info['date_range']['end'].date()
                    days_behind = (today - end_date_obj).days
                    
                    if days_behind <= 1:
                        print(f"    ✅ 数据较新")
                    elif days_behind <= 3:
                        print(f"    ⚠️ 数据滞后 {days_behind} 天")
                    else:
                        print(f"    ❌ 数据过期 {days_behind} 天")
        
        # 显示品种一致性分析
        print(f"\n🔍 品种覆盖分析:")
        if 'analysis' in status:
            analysis = status['analysis']
            print(f"  📊 共同品种: {len(analysis.get('common_varieties', []))} 个")
            
            # 显示缺失品种（只显示主要的）
            for module, missing in analysis.get('missing_varieties', {}).items():
                if len(missing) > 0 and len(missing) <= 10:  # 只显示缺失不多的
                    print(f"  ⚠️ {module} 缺少: {', '.join(sorted(missing)[:5])}")
    
    def get_update_mode_and_params(self) -> Tuple[str, datetime, Optional[List[str]], Optional[List[str]]]:
        """获取更新模式和参数"""
        print(f"\n📝 请选择更新模式:")
        print(f"  1. 全板块更新模式 - 更新所有模块的所有品种")
        print(f"  2. 自定义板块更新模式 - 选择特定模块更新")  
        print(f"  3. 全品种更新模式 - 全部模块全部品种")
        print(f"  4. 特定品种更新模式 - 选择特定品种")
        
        while True:
            try:
                choice = input(f"\n请选择 (1-4): ").strip()
                
                if choice == "1":
                    mode = "all_modules"
                    modules = None
                    varieties = None
                    break
                elif choice == "2":
                    mode = "specific_modules"
                    print(f"\n可用模块: {', '.join(self.module_order)}")
                    modules_input = input("请输入要更新的模块（用逗号分隔）: ").strip()
                    modules = [m.strip() for m in modules_input.split(",") if m.strip() in self.module_order]
                    varieties = None
                    
                    if not modules:
                        print("❌ 未选择有效模块，请重新选择")
                        continue
                    print(f"✅ 已选择模块: {', '.join(modules)}")
                    break
                elif choice == "3":
                    mode = "all"
                    modules = None
                    varieties = None
                    break
                elif choice == "4":
                    mode = "specific_varieties"
                    modules = None
                    varieties_input = input("请输入品种代码（用逗号分隔，如: A,RB,AG）: ").strip()
                    varieties = [v.strip().upper() for v in varieties_input.split(",") if v.strip()]
                    
                    if not varieties:
                        print("❌ 未输入有效品种，请重新选择")
                        continue
                    print(f"✅ 已选择品种: {', '.join(varieties)}")
                    break
                else:
                    print("❌ 请输入有效选项 (1-4)")
                    
            except KeyboardInterrupt:
                print(f"\n❌ 用户取消")
                sys.exit(0)
        
        # 获取目标日期
        while True:
            try:
                date_input = input(f"\n📅 请输入目标更新日期 (格式: YYYY-MM-DD, 直接回车使用今天): ").strip()
                
                if not date_input:
                    target_date = datetime.now()
                    break
                else:
                    target_date = datetime.strptime(date_input, "%Y-%m-%d")
                    break
                    
            except ValueError:
                print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
            except KeyboardInterrupt:
                print(f"\n❌ 用户取消")
                sys.exit(0)
        
        return mode, target_date, varieties, modules
    
    def check_data_quality(self, target_date: datetime) -> Dict[str, List[str]]:
        """检查数据质量和完整性"""
        print(f"\n🔍 检查数据质量...")
        
        quality_issues = {}
        
        # 检查各模块数据到目标日期的情况
        for module_name in self.module_order:
            if module_name not in self.updaters:
                continue
                
            try:
                updater = self.updaters[module_name]
                status = updater.get_existing_data_status()
                
                outdated_varieties = []
                
                for variety, info in status.items():
                    if isinstance(info, dict) and 'latest_date' in info:
                        latest_date = datetime.strptime(info['latest_date'], '%Y-%m-%d')
                        if latest_date.date() < target_date.date():
                            days_behind = (target_date.date() - latest_date.date()).days
                            outdated_varieties.append(f"{variety}({days_behind}天)")
                
                if outdated_varieties:
                    quality_issues[module_name] = outdated_varieties
                    print(f"   ⚠️ {module_name}: {len(outdated_varieties)} 个品种需要更新")
                else:
                    print(f"   ✅ {module_name}: 数据为最新")
                    
            except Exception as e:
                print(f"   ❌ {module_name}: 检查失败 - {str(e)[:50]}")
                quality_issues[module_name] = [f"检查失败: {str(e)[:30]}"]
        
        return quality_issues
    
    def run_module_update(self, module_name: str, target_date: datetime, 
                         mode: str = "all", varieties: Optional[List[str]] = None) -> Dict:
        """运行单个模块的更新"""
        print(f"\n🔄 开始更新【{module_name}】模块")
        print("=" * 60)
        
        if module_name not in self.updaters:
            return {
                "module": module_name,
                "status": "error", 
                "error": f"未知模块: {module_name}",
                "elapsed_time": 0,
                "updated_varieties": [],
                "failed_varieties": []
            }
        
        start_time = time.time()
        
        try:
            updater = self.updaters[module_name]
            target_date_str = target_date.strftime("%Y-%m-%d")
            
            # 调用更新器
            if mode == "specific_varieties" and varieties:
                result = updater.update_data(target_date_str, varieties)
            else:
                result = updater.update_data(target_date_str)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # 解析结果
            if isinstance(result, dict):
                status = "success" if result.get("success", False) else "partial"
                updated_varieties = result.get("updated_varieties", [])
                failed_varieties = result.get("failed_varieties", [])
                error_msg = result.get("error", "")
            else:
                # 兼容不同的返回格式
                status = "success"
                updated_varieties = []
                failed_varieties = []
                error_msg = ""
            
            # 显示结果
            print(f"\n📊 【{module_name}】更新结果:")
            print(f"   {'✅' if status == 'success' else '⚠️' if status == 'partial' else '❌'} 状态: {status}")
            
            if updated_varieties:
                print(f"   ✅ 成功更新: {len(updated_varieties)} 个品种")
                if len(updated_varieties) <= 10:
                    print(f"   📝 品种列表: {', '.join(updated_varieties)}")
            
            if failed_varieties:
                print(f"   ❌ 失败品种: {len(failed_varieties)} 个")
                if len(failed_varieties) <= 5:
                    print(f"   📝 失败列表: {', '.join(failed_varieties)}")
            
            if error_msg:
                print(f"   💥 错误信息: {error_msg}")
                
            print(f"   ⏱️ 耗时: {elapsed:.1f} 秒")
            
            return {
                "module": module_name,
                "status": status,
                "updated_varieties": updated_varieties,
                "failed_varieties": failed_varieties,
                "error": error_msg,
                "elapsed_time": elapsed
            }
            
        except Exception as e:
            end_time = time.time()
            elapsed = end_time - start_time
            
            error_msg = str(e)
            print(f"\n❌ 【{module_name}】模块更新失败: {error_msg}")
            
            return {
                "module": module_name,
                "status": "error",
                "error": error_msg,
                "elapsed_time": elapsed,
                "updated_varieties": [],
                "failed_varieties": []
            }
    
    def run_full_update(self, target_date: datetime, mode: str = "all", 
                       varieties: Optional[List[str]] = None, modules: Optional[List[str]] = None):
        """运行完整更新流程"""
        
        self.update_report["target_date"] = target_date.strftime("%Y-%m-%d")
        
        # 确定要更新的模块
        if modules:
            update_modules = [m for m in modules if m in self.module_order]
        else:
            update_modules = self.module_order.copy()
        
        self.update_report["summary"]["total_modules"] = len(update_modules)
        
        print(f"\n🚀 开始统一更新流程")
        print("=" * 80)
        print(f"📅 目标日期: {target_date.strftime('%Y-%m-%d')}")
        print(f"🎯 更新模式: {mode}")
        print(f"🔄 更新模块: {', '.join(update_modules)}")
        if varieties:
            print(f"📋 指定品种: {', '.join(varieties)} ({len(varieties)} 个)")
        
        # 数据质量预检
        quality_issues = self.check_data_quality(target_date)
        if quality_issues:
            print(f"\n⚠️ 发现数据质量问题，将优先更新这些数据")
        
        # 按顺序更新各模块
        all_results = []
        
        for module_name in update_modules:
            result = self.run_module_update(module_name, target_date, mode, varieties)
            all_results.append(result)
            self.update_report["modules"][module_name] = result
            
            # 更新汇总统计
            if result["status"] in ["success", "partial"]:
                self.update_report["summary"]["successful_modules"] += 1
                self.update_report["summary"]["total_updated_varieties"].update(result["updated_varieties"])
            else:
                self.update_report["summary"]["failed_modules"] += 1
            
            self.update_report["summary"]["total_failed_varieties"].update(result["failed_varieties"])
            self.update_report["summary"]["total_elapsed_time"] += result["elapsed_time"]
            
            # 模块间休息
            if module_name != update_modules[-1]:  # 不是最后一个模块
                print(f"\n⏳ 等待 2 秒后继续下一个模块...")
                time.sleep(2)
        
        # 生成总结报告
        self.generate_update_summary(all_results)
        
        # 保存更新报告
        self.save_update_report()
    
    def generate_update_summary(self, results: List[Dict]):
        """生成更新总结"""
        print(f"\n" + "="*80)
        print(f"📋 更新总结报告")
        print("="*80)
        
        total_modules = len(results)
        successful = len([r for r in results if r["status"] in ["success", "partial"]])
        failed = total_modules - successful
        
        total_updated = len(self.update_report["summary"]["total_updated_varieties"])
        total_failed = len(self.update_report["summary"]["total_failed_varieties"])
        total_time = self.update_report["summary"]["total_elapsed_time"]
        
        print(f"📊 整体统计:")
        print(f"  🎯 目标日期: {self.update_report['target_date']}")
        print(f"  ✅ 成功模块: {successful}/{total_modules}")
        print(f"  ❌ 失败模块: {failed}/{total_modules}")
        print(f"  📈 更新品种: {total_updated} 个")
        print(f"  💥 失败品种: {total_failed} 个")
        print(f"  ⏱️ 总耗时: {total_time:.1f} 秒")
        
        # 详细结果
        print(f"\n📋 各模块详情:")
        for result in results:
            status_icon = "✅" if result["status"] == "success" else "⚠️" if result["status"] == "partial" else "❌"
            print(f"  {status_icon} {result['module']}: {result['status']}")
            
            if result["updated_varieties"]:
                print(f"    ✅ 成功: {len(result['updated_varieties'])} 个品种")
            
            if result["failed_varieties"]:
                print(f"    ❌ 失败: {len(result['failed_varieties'])} 个品种")
                
            if result.get("error"):
                print(f"    💥 错误: {result['error'][:50]}")
        
        # 显示需要重试的品种
        if total_failed > 0:
            print(f"\n⚠️ 失败品种建议重试:")
            failed_varieties = list(self.update_report["summary"]["total_failed_varieties"])
            if len(failed_varieties) <= 20:
                print(f"  {', '.join(sorted(failed_varieties))}")
            else:
                print(f"  {', '.join(sorted(failed_varieties)[:20])}... (共{len(failed_varieties)}个)")
    
    def _convert_to_serializable(self, obj):
        """转换对象为JSON可序列化格式"""
        if isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'isoformat'): # Handle other datetime-like objects
            return obj.isoformat()
        else:
            return obj
    
    def save_update_report(self):
        """保存更新报告"""
        try:
            self.update_report["end_time"] = datetime.now()
            self.update_report["summary"]["total_updated_varieties"] = list(self.update_report["summary"]["total_updated_varieties"])
            self.update_report["summary"]["total_failed_varieties"] = list(self.update_report["summary"]["total_failed_varieties"])
            
            # 转换为可序列化格式
            serializable_report = self._convert_to_serializable(self.update_report)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = self.database_path / f"update_report_{timestamp}.json"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_report, f, ensure_ascii=False, indent=2)
            
            print(f"\n💾 更新报告已保存: {report_file}")
            
        except Exception as e:
            print(f"\n❌ 报告保存失败: {e}")
    
    def retry_failed_varieties(self):
        """重试失败的品种"""
        failed_list = list(self.update_report["summary"]["total_failed_varieties"])
        
        if not failed_list:
            print(f"\n✅ 没有需要重试的失败品种")
            return
        
        print(f"\n🔄 准备重试失败品种:")
        print(f"   失败品种: {', '.join(failed_list)} (共{len(failed_list)}个)")
        
        target_date = datetime.strptime(self.update_report["target_date"], "%Y-%m-%d")
        
        # 重置失败统计
        self.update_report["summary"]["total_failed_varieties"] = set()
        
        # 重新运行更新，只针对失败品种
        self.run_full_update(target_date, "specific_varieties", failed_list)

def main():
    """主函数"""
    try:
        # 初始化系统
        updater = UnifiedFuturesDataUpdaterFixed()
        
        # 显示系统状态
        updater.show_system_status()
        
        # 获取用户输入
        mode, target_date, varieties, modules = updater.get_update_mode_and_params()
        
        # 确认更新参数
        print(f"\n" + "=" * 80)
        print(f"⚠️ 确认更新参数:")
        print(f"  📅 目标日期: {target_date.strftime('%Y-%m-%d')}")
        print(f"  🎯 更新模式: {mode}")
        if varieties:
            print(f"  📋 指定品种: {', '.join(varieties)} ({len(varieties)} 个)")
        if modules:
            print(f"  🔧 指定模块: {', '.join(modules)}")
        else:
            print(f"  🔄 将按顺序更新: 基差 → 库存 → 持仓 → 期限结构 → 技术分析")
        
        confirm = input(f"\n是否开始更新？(y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ 用户取消更新")
            return
        
        # 执行更新
        updater.run_full_update(target_date, mode, varieties, modules)
        
        # 询问是否重试失败品种
        while True:
            retry = input(f"\n是否要重试失败的品种？(y/N): ").strip().lower()
            if retry in ['y', 'yes']:
                updater.retry_failed_varieties()
            else:
                break
        
        print(f"\n🎉 统一期货多维数据更新系统运行完成！")
        
    except KeyboardInterrupt:
        print(f"\n\n❌ 用户中断程序")
    except Exception as e:
        print(f"\n\n💥 程序运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
