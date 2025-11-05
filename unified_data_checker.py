#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一期货多维数据状态检查器
分析各板块数据状态，提供品种对比和数据范围信息
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# 数据库根目录 - 修改为相对路径
DATABASE_ROOT = Path("qihuo/database")

# 各板块配置
MODULES_CONFIG = {
    "basis": {
        "name": "基差数据",
        "path": DATABASE_ROOT / "basis",
        "data_file": "basis_summary.json",  # 实际文件是JSON格式
        "date_column": "date"
    },
    "inventory": {
        "name": "库存数据", 
        "path": DATABASE_ROOT / "inventory",
        "data_file": "inventory.csv",
        "date_column": "date"
    },
    "positioning": {
        "name": "持仓数据",
        "path": DATABASE_ROOT / "positioning", 
        "data_file": "positioning_summary.json",  # 实际文件是JSON格式
        "date_column": "date"
    },
    "term_structure": {
        "name": "期限结构数据",
        "path": DATABASE_ROOT / "term_structure",
        "data_file": "term_structure.csv", 
        "date_column": "date"
    },
    "technical_analysis": {
        "name": "技术分析数据",
        "path": DATABASE_ROOT / "technical_analysis",
        "data_file": "ohlc_data.csv",
        "date_column": "date"
    }
}

class UnifiedDataChecker:
    """统一数据状态检查器"""
    
    def __init__(self, database_root: Optional[str] = None):
        """
        初始化检查器
        
        Args:
            database_root: 数据库根目录路径，默认为None则使用相对路径qihuo/database
        """
        self.modules_data = {}
        self.analysis_result = {}
        
        # 如果指定了自定义路径，则更新配置
        if database_root:
            global DATABASE_ROOT
            DATABASE_ROOT = Path(database_root)
            for module in MODULES_CONFIG.values():
                module["path"] = DATABASE_ROOT / module["path"].name
    
    def get_comprehensive_status(self) -> Dict:
        """
        获取各板块综合状态（供外部调用）
        
        Returns:
            包含各板块状态的字典
        """
        status = {}
        
        for module_name in MODULES_CONFIG.keys():
            module_data = self.scan_module_data(module_name)
            status[module_name] = module_data
        
        # 添加品种分析
        status['analysis'] = self._analyze_varieties()
        
        return status
        
    def scan_module_data(self, module_name: str) -> Dict:
        """扫描单个模块的数据状态"""
        print(f"🔍 扫描 {MODULES_CONFIG[module_name]['name']}...")
        
        config = MODULES_CONFIG[module_name]
        module_path = config["path"]
        data_file = config["data_file"]
        date_column = config["date_column"]
        
        module_info = {
            "name": config["name"],
            "varieties": {},
            "variety_count": 0,
            "total_records": 0,
            "date_range": {"start": None, "end": None},
            "status": "success"
        }
        
        if not module_path.exists():
            module_info["status"] = "not_found"
            print(f"   ❌ 目录不存在: {module_path}")
            return module_info
            
        # 扫描品种目录
        variety_dirs = [d for d in module_path.iterdir() if d.is_dir()]
        
        for variety_dir in variety_dirs:
            variety = variety_dir.name
            variety_file = variety_dir / data_file
            
            variety_info = {
                "records": 0,
                "start_date": None,
                "end_date": None,
                "file_exists": False,
                "status": "no_data"
            }
            
            if variety_file.exists():
                try:
                    # 读取数据（支持CSV和JSON格式）
                    if variety_file.suffix == '.json':
                        import json
                        with open(variety_file, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        # JSON summary文件特殊处理：标记为有数据
                        if isinstance(json_data, dict):
                            variety_info.update({
                                "records": 1,  # JSON summary文件
                                "file_exists": True,
                                "status": "has_data"
                            })
                            module_info["total_records"] += 1
                    else:
                        df = pd.read_csv(variety_file)
                        
                        if len(df) > 0 and date_column in df.columns:
                            # 处理日期列 - 统一处理逻辑
                            if df[date_column].dtype == 'object':
                                # 尝试解析日期
                                try:
                                    df[date_column] = pd.to_datetime(df[date_column])
                                except:
                                    # 如果是20250816这种格式
                                    df[date_column] = pd.to_datetime(df[date_column], format='%Y%m%d', errors='coerce')
                            elif df[date_column].dtype in ['int64', 'float64']:
                                # 数字格式的日期，如20250816
                                df[date_column] = pd.to_datetime(df[date_column].astype(str), format='%Y%m%d', errors='coerce')
                            else:
                                df[date_column] = pd.to_datetime(df[date_column])
                            
                            # 去掉无效日期
                            df = df.dropna(subset=[date_column])
                            
                            if len(df) > 0:
                                variety_info.update({
                                    "records": len(df),
                                    "start_date": df[date_column].min(),
                                    "end_date": df[date_column].max(),
                                    "file_exists": True,
                                    "status": "has_data"
                                })
                                
                                module_info["total_records"] += len(df)
                                
                                # 更新模块整体日期范围
                                if module_info["date_range"]["start"] is None or df[date_column].min() < module_info["date_range"]["start"]:
                                    module_info["date_range"]["start"] = df[date_column].min()
                                if module_info["date_range"]["end"] is None or df[date_column].max() > module_info["date_range"]["end"]:
                                    module_info["date_range"]["end"] = df[date_column].max()
                        
                except Exception as e:
                    variety_info["status"] = f"error: {str(e)[:50]}"
                    print(f"   ⚠️ {variety}: 读取失败 - {str(e)[:50]}")
            
            module_info["varieties"][variety] = variety_info
        
        # 计算有效品种数量
        valid_varieties = [v for v, info in module_info["varieties"].items() if info["status"] == "has_data"]
        module_info["variety_count"] = len(valid_varieties)
        
        print(f"   ✅ 找到 {module_info['variety_count']} 个有效品种，共 {module_info['total_records']:,} 条记录")
        
        return module_info
    
    def analyze_all_modules(self) -> Dict:
        """分析所有模块数据"""
        print("🚀 统一期货多维数据状态检查")
        print("=" * 80)
        
        # 扫描各个模块
        for module_name in MODULES_CONFIG.keys():
            self.modules_data[module_name] = self.scan_module_data(module_name)
        
        # 分析品种分布
        self.analysis_result = self._analyze_varieties()
        
        return {
            "modules": self.modules_data,
            "analysis": self.analysis_result,
            "scan_time": datetime.now().isoformat()
        }
    
    def _analyze_varieties(self) -> Dict:
        """分析品种分布和差异"""
        print(f"\n📊 品种分布分析")
        print("-" * 50)
        
        # 收集各模块的有效品种
        module_varieties = {}
        all_varieties = set()
        
        for module_name, module_data in self.modules_data.items():
            if module_data["status"] == "success":
                valid_varieties = set([
                    v for v, info in module_data["varieties"].items() 
                    if info["status"] == "has_data"
                ])
                module_varieties[module_name] = valid_varieties
                all_varieties.update(valid_varieties)
                
                print(f"  {module_data['name']}: {len(valid_varieties)} 个品种")
        
        # 找出各模块共同的品种
        if module_varieties:
            common_varieties = set.intersection(*module_varieties.values())
        else:
            common_varieties = set()
        
        print(f"\n🎯 共同品种: {len(common_varieties)} 个")
        if common_varieties:
            common_list = sorted(list(common_varieties))
            for i in range(0, len(common_list), 10):
                print(f"  {', '.join(common_list[i:i+10])}")
        
        # 分析各模块缺失和多余的品种
        print(f"\n📋 品种差异分析:")
        module_differences = {}
        
        for module_name, varieties in module_varieties.items():
            module_name_cn = MODULES_CONFIG[module_name]["name"]
            
            # 相对于其他模块多出的品种
            other_varieties = set()
            for other_module, other_vars in module_varieties.items():
                if other_module != module_name:
                    other_varieties.update(other_vars)
            
            extra_varieties = varieties - other_varieties
            missing_varieties = other_varieties - varieties
            
            module_differences[module_name] = {
                "extra": sorted(list(extra_varieties)),
                "missing": sorted(list(missing_varieties))
            }
            
            print(f"\n  {module_name_cn}:")
            print(f"    多出品种: {len(extra_varieties)} 个")
            if extra_varieties:
                extra_list = sorted(list(extra_varieties))
                for i in range(0, len(extra_list), 10):
                    print(f"      {', '.join(extra_list[i:i+10])}")
            
            print(f"    缺少品种: {len(missing_varieties)} 个") 
            if missing_varieties:
                missing_list = sorted(list(missing_varieties))
                for i in range(0, len(missing_list), 10):
                    print(f"      {', '.join(missing_list[i:i+10])}")
        
        return {
            "all_varieties": sorted(list(all_varieties)),
            "all_varieties_count": len(all_varieties),
            "common_varieties": sorted(list(common_varieties)),
            "common_varieties_count": len(common_varieties),
            "module_varieties": {k: sorted(list(v)) for k, v in module_varieties.items()},
            "missing_varieties": {k: v["missing"] for k, v in module_differences.items()}
        }
    
    def display_detailed_summary(self):
        """显示详细的数据摘要"""
        print(f"\n📈 详细数据摘要")
        print("=" * 80)
        
        for module_name, module_data in self.modules_data.items():
            if module_data["status"] != "success":
                continue
                
            print(f"\n【{module_data['name']}】")
            print(f"  品种数量: {module_data['variety_count']} 个")
            print(f"  记录总数: {module_data['total_records']:,} 条")
            
            if module_data["date_range"]["start"] and module_data["date_range"]["end"]:
                start_str = module_data["date_range"]["start"].strftime('%Y-%m-%d')
                end_str = module_data["date_range"]["end"].strftime('%Y-%m-%d')
                print(f"  时间范围: {start_str} 至 {end_str}")
            
            # 显示前20个品种的详细信息
            valid_varieties = [
                (v, info) for v, info in module_data["varieties"].items() 
                if info["status"] == "has_data"
            ]
            
            if valid_varieties:
                print(f"  品种详情 (前20个):")
                for i, (variety, info) in enumerate(sorted(valid_varieties)[:20]):
                    start_str = info["start_date"].strftime('%Y-%m-%d') if info["start_date"] else "无"
                    end_str = info["end_date"].strftime('%Y-%m-%d') if info["end_date"] else "无"
                    print(f"    {variety:>3}: {info['records']:>6,} 条  ({start_str} ~ {end_str})")
                
                if len(valid_varieties) > 20:
                    print(f"    ... 还有 {len(valid_varieties) - 20} 个品种")
    
    def save_report(self, output_path: Optional[Path] = None):
        """保存检查报告"""
        if output_path is None:
            output_path = Path("unified_data_status_report.json")
        
        # 准备可序列化的数据
        report_data = {
            "scan_time": datetime.now().isoformat(),
            "modules": {},
            "analysis": self.analysis_result
        }
        
        # 处理模块数据
        for module_name, module_data in self.modules_data.items():
            processed_module = module_data.copy()
            
            # 转换日期为字符串
            if processed_module["date_range"]["start"]:
                processed_module["date_range"]["start"] = processed_module["date_range"]["start"].isoformat()
            if processed_module["date_range"]["end"]:
                processed_module["date_range"]["end"] = processed_module["date_range"]["end"].isoformat()
            
            # 处理品种数据中的日期
            for variety, variety_info in processed_module["varieties"].items():
                if variety_info["start_date"]:
                    variety_info["start_date"] = variety_info["start_date"].isoformat()
                if variety_info["end_date"]:
                    variety_info["end_date"] = variety_info["end_date"].isoformat()
            
            report_data["modules"][module_name] = processed_module
        
        # 保存报告
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            print(f"\n💾 检查报告已保存: {output_path}")
        except Exception as e:
            print(f"\n❌ 报告保存失败: {e}")
        
        return output_path

def main():
    """主函数"""
    checker = UnifiedDataChecker()
    
    # 执行分析
    result = checker.analyze_all_modules()
    
    # 显示详细摘要
    checker.display_detailed_summary()
    
    # 保存报告
    checker.save_report()
    
    return checker

if __name__ == "__main__":
    main()

