#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货Trading Agents系统 - 基础架构
提供系统核心的数据结构和基础功能
"""

import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import pandas as pd

# ============================================================================
# 1. 枚举定义
# ============================================================================

class AnalysisStatus(Enum):
    """分析状态枚举"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    CACHED = "cached"

class DebateStance(Enum):
    """辩论立场枚举"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

# ============================================================================
# 2. 核心数据结构
# ============================================================================

@dataclass
class ModuleAnalysisResult:
    """模块分析结果"""
    module_name: str
    commodity: str
    analysis_date: str
    status: AnalysisStatus
    result_data: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 0.0
    execution_time: float = 0.0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class CrossModuleRelationship:
    """跨模块关系"""
    module1: str
    module2: str
    relationship_type: str
    strength: float
    description: str

@dataclass
class FuturesAnalysisState:
    """期货分析状态"""
    commodity: str
    analysis_date: str
    
    # 六大分析模块结果
    inventory_analysis: Optional[ModuleAnalysisResult] = None
    positioning_analysis: Optional[ModuleAnalysisResult] = None  
    term_structure_analysis: Optional[ModuleAnalysisResult] = None
    technical_analysis: Optional[ModuleAnalysisResult] = None
    basis_analysis: Optional[ModuleAnalysisResult] = None
    news_analysis: Optional[ModuleAnalysisResult] = None
    
    # 跨模块关系
    cross_module_relationships: List[CrossModuleRelationship] = field(default_factory=list)
    
    # 元数据
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    completion_time: Optional[str] = None
    total_execution_time: float = 0.0
    
    def get_analysis_progress(self) -> float:
        """获取分析进度"""
        modules = [
            self.inventory_analysis,
            self.positioning_analysis,
            self.term_structure_analysis,
            self.technical_analysis,
            self.basis_analysis,
            self.news_analysis
        ]
        
        completed_count = sum(1 for module in modules if module and module.status == AnalysisStatus.COMPLETED)
        return completed_count / len(modules)
    
    def get_completed_modules(self) -> List[str]:
        """获取已完成模块列表"""
        completed = []
        modules = {
            'inventory': self.inventory_analysis,
            'positioning': self.positioning_analysis,
            'term_structure': self.term_structure_analysis,
            'technical': self.technical_analysis,
            'basis': self.basis_analysis,
            'news': self.news_analysis
        }
        
        for name, module in modules.items():
            if module and module.status == AnalysisStatus.COMPLETED:
                completed.append(name)
                
        return completed
    
    def get_module_result(self, module_name: str) -> Optional[ModuleAnalysisResult]:
        """获取指定模块结果"""
        module_map = {
            'inventory': self.inventory_analysis,
            'positioning': self.positioning_analysis,
            'term_structure': self.term_structure_analysis,
            'technical': self.technical_analysis,
            'basis': self.basis_analysis,
            'news': self.news_analysis
        }
        return module_map.get(module_name)
    
    def set_module_result(self, module_name: str, result: ModuleAnalysisResult):
        """设置模块结果"""
        if module_name == 'inventory':
            self.inventory_analysis = result
        elif module_name == 'positioning':
            self.positioning_analysis = result
        elif module_name == 'term_structure':
            self.term_structure_analysis = result
        elif module_name == 'technical':
            self.technical_analysis = result
        elif module_name == 'basis':
            self.basis_analysis = result
        elif module_name == 'news':
            self.news_analysis = result

# ============================================================================
# 3. 配置管理系统
# ============================================================================

class FuturesTradingAgentsConfig:
    """期货Trading Agents配置管理器"""
    
    def __init__(self, config_file: str = None, custom_config: Dict = None):
        self.config_file = config_file or "期货TradingAgents系统_配置文件.json"
        self.config = self._load_config()
        
        # 合并自定义配置
        if custom_config:
            self.config.update(custom_config)
        
        # 设置默认值
        self._set_defaults()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"配置文件加载失败: {e}")
                return self._get_default_config()
        else:
            print(f"配置文件不存在: {config_path}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "data_root_dir": "qihuo/database",
            "results_dir": "qihuo/trading_agents_results",
            "logs_dir": "logs",
            "cache_dir": "cache",
            "supported_commodities": [
                "AG", "AU", "CU", "AL", "ZN", "PB", "NI", "SN", "RB", "HC", "I", "JM", "J",
                "BU", "FU", "RU", "NR", "L", "V", "PP", "EG", "TA", "MA", "CF", "SR", "RM",
                "OI", "M", "Y", "A", "C", "CS", "JD", "AP", "CJ", "SA", "FG", "SF", "SM",
                "ZC", "UR", "LH", "PF", "PK", "PS", "LC", "SI"
            ],
            "api_settings": {
                "deepseek": {
                    "api_key": "YOUR_DEEPSEEK_API_KEY_HERE",  # 请配置你的API密钥
                    "base_url": "https://api.deepseek.com/v1",
                    "timeout": 120
                },
                "serper": {
                    "api_key": "YOUR_SERPER_API_KEY_HERE",  # 可选，用于新闻搜索
                    "base_url": "https://google.serper.dev/search"
                }
            },
            "analysis_settings": {
                "use_cache": True,
                "cache_duration": 3600,
                "max_retries": 3,
                "parallel_analysis": True
            },
            "logging": {
                "level": "INFO",
                "console_logging": True,
                "file_logging": True
            }
        }
    
    def _set_defaults(self):
        """设置默认值"""
        defaults = self._get_default_config()
        
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.config.copy()

# ============================================================================
# 4. 分析整合器
# ============================================================================

class FuturesAnalysisIntegrator:
    """期货分析整合器 - 核心控制器"""
    
    def __init__(self, data_root_dir: str = None, config: Dict = None):
        self.data_root_dir = Path(data_root_dir or "qihuo/database")
        self.config = config or {}
        self.logger = logging.getLogger("FuturesAnalysisIntegrator")
        
        # 支持的模块
        self.supported_modules = {
            'inventory': self._run_real_time_inventory_analysis,
            'positioning': self._run_real_time_positioning_analysis,
            'term_structure': self._run_real_time_term_structure_analysis,
            'technical': self._run_real_time_technical_analysis,
            'basis': self._run_real_time_basis_analysis,
            'news': self._run_real_time_news_analysis
        }
    
    async def collect_all_analyses(self, commodity: str, analysis_date: str = None, 
                                 selected_modules: List[str] = None) -> FuturesAnalysisState:
        """收集所有分析模块的结果"""
        if analysis_date is None:
            analysis_date = datetime.now().strftime('%Y-%m-%d')
        
        # 创建分析状态
        analysis_state = FuturesAnalysisState(
            commodity=commodity,
            analysis_date=analysis_date
        )
        
        # 确定要运行的模块
        modules_to_run = selected_modules or list(self.supported_modules.keys())
        
        # 并行运行所有模块
        tasks = []
        for module_name in modules_to_run:
            if module_name in self.supported_modules:
                task = self.supported_modules[module_name](commodity, analysis_date)
                tasks.append((module_name, task))
        
        # 等待所有任务完成
        for module_name, task in tasks:
            try:
                result = await task
                analysis_state.set_module_result(module_name, result)
                self.logger.info(f"模块 {module_name} 分析完成")
            except Exception as e:
                error_result = ModuleAnalysisResult(
                    module_name=module_name,
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.FAILED,
                    error_message=str(e)
                )
                analysis_state.set_module_result(module_name, error_result)
                self.logger.error(f"模块 {module_name} 分析失败: {e}")
        
        # 设置完成时间
        analysis_state.completion_time = datetime.now().isoformat()
        start_time = datetime.fromisoformat(analysis_state.start_time)
        end_time = datetime.fromisoformat(analysis_state.completion_time)
        analysis_state.total_execution_time = (end_time - start_time).total_seconds()
        
        return analysis_state
    
    async def _run_real_time_inventory_analysis(self, commodity: str, analysis_date: str) -> ModuleAnalysisResult:
        """运行实时库存分析"""
        start_time = datetime.now()
        
        try:
            # 导入适配器
            from streamlit_inventory_analysis_adapter import analyze_inventory_for_streamlit
            
            # 调用分析
            result_data = await analyze_inventory_for_streamlit(commodity, analysis_date, use_reasoner=True)
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            if result_data.get("success", False):
                return ModuleAnalysisResult(
                    module_name="inventory",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.COMPLETED,
                    result_data=result_data,
                    confidence_score=result_data.get("confidence_score", 0.75),
                    execution_time=execution_time
                )
            else:
                return ModuleAnalysisResult(
                    module_name="inventory",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.FAILED,
                    error_message=result_data.get("error", "未知错误"),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ModuleAnalysisResult(
                module_name="inventory",
                commodity=commodity,
                analysis_date=analysis_date,
                status=AnalysisStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _run_real_time_positioning_analysis(self, commodity: str, analysis_date: str) -> ModuleAnalysisResult:
        """运行实时持仓分析（改进版 - 支持5大策略）"""
        start_time = datetime.now()
        
        try:
            # 导入改进版适配器
            from 改进版持仓席位分析适配器 import analyze_improved_positioning_for_streamlit
            
            # 调用分析（同步函数，在线程池中运行以避免阻塞）
            import asyncio
            loop = asyncio.get_event_loop()
            result_data = await loop.run_in_executor(
                None, 
                lambda: analyze_improved_positioning_for_streamlit(commodity, analysis_date, use_reasoner=True)
            )
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            if result_data.get("success", False):
                return ModuleAnalysisResult(
                    module_name="positioning",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.COMPLETED,
                    result_data=result_data,
                    confidence_score=result_data.get("overall_confidence", 0.75),
                    execution_time=execution_time
                )
            else:
                return ModuleAnalysisResult(
                    module_name="positioning",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.FAILED,
                    error_message=result_data.get("error", "未知错误"),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ModuleAnalysisResult(
                module_name="positioning",
                commodity=commodity,
                analysis_date=analysis_date,
                status=AnalysisStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _run_real_time_term_structure_analysis(self, commodity: str, analysis_date: str) -> ModuleAnalysisResult:
        """运行实时期限结构分析"""
        start_time = datetime.now()
        
        try:
            # 导入适配器
            from streamlit_ultimate_term_structure_adapter import StreamlitUltimateTermStructureAdapter
            
            # 调用分析（非异步函数）
            adapter = StreamlitUltimateTermStructureAdapter()
            result_data = adapter.analyze_variety_for_streamlit(commodity, analysis_date)
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            if result_data.get("success", False):
                return ModuleAnalysisResult(
                    module_name="term_structure",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.COMPLETED,
                    result_data=result_data,
                    confidence_score=result_data.get("confidence_score", 0.85),
                    execution_time=execution_time
                )
            else:
                return ModuleAnalysisResult(
                    module_name="term_structure",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.FAILED,
                    error_message=result_data.get("error", "未知错误"),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ModuleAnalysisResult(
                module_name="term_structure",
                commodity=commodity,
                analysis_date=analysis_date,
                status=AnalysisStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _run_real_time_technical_analysis(self, commodity: str, analysis_date: str) -> ModuleAnalysisResult:
        """运行实时技术分析"""
        start_time = datetime.now()
        
        try:
            # 导入适配器
            from streamlit_enhanced_technical_adapter import analyze_technical_for_streamlit
            
            # 调用分析
            result_data = await analyze_technical_for_streamlit(commodity, analysis_date)
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            if result_data.get("success", False):
                return ModuleAnalysisResult(
                    module_name="technical",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.COMPLETED,
                    result_data=result_data,
                    confidence_score=result_data.get("confidence_score", 0.7),
                    execution_time=execution_time
                )
            else:
                return ModuleAnalysisResult(
                    module_name="technical",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.FAILED,
                    error_message=result_data.get("error", "未知错误"),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ModuleAnalysisResult(
                module_name="technical",
                commodity=commodity,
                analysis_date=analysis_date,
                status=AnalysisStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _run_real_time_basis_analysis(self, commodity: str, analysis_date: str) -> ModuleAnalysisResult:
        """运行实时基差分析"""
        start_time = datetime.now()
        
        try:
            # 导入适配器
            from streamlit_basis_analysis_adapter import analyze_basis_for_streamlit
            
            # 调用分析
            result_data = await analyze_basis_for_streamlit(commodity, analysis_date)
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            if result_data.get("success", False):
                return ModuleAnalysisResult(
                    module_name="basis",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.COMPLETED,
                    result_data=result_data,
                    confidence_score=result_data.get("confidence_score", 0.75),
                    execution_time=execution_time
                )
            else:
                return ModuleAnalysisResult(
                    module_name="basis",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.FAILED,
                    error_message=result_data.get("error", "未知错误"),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ModuleAnalysisResult(
                module_name="basis",
                commodity=commodity,
                analysis_date=analysis_date,
                status=AnalysisStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time
            )
    
    async def _run_real_time_news_analysis(self, commodity: str, analysis_date: str) -> ModuleAnalysisResult:
        """运行实时新闻分析"""
        start_time = datetime.now()
        
        try:
            # 导入适配器
            from streamlit_improved_news_adapter import analyze_improved_news_for_streamlit
            
            # 获取API密钥（使用self.config而不是config）
            api_key = self.config.get("api_settings", {}).get("deepseek", {}).get("api_key", "YOUR_API_KEY")
            
            # 调用分析
            result_data = analyze_improved_news_for_streamlit(commodity, api_key, analysis_date)
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 构建结果
            if result_data.get("success", False):
                return ModuleAnalysisResult(
                    module_name="news",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.COMPLETED,
                    result_data=result_data,
                    confidence_score=result_data.get("confidence_score", 0.65),
                    execution_time=execution_time
                )
            else:
                return ModuleAnalysisResult(
                    module_name="news",
                    commodity=commodity,
                    analysis_date=analysis_date,
                    status=AnalysisStatus.FAILED,
                    error_message=result_data.get("error", "未知错误"),
                    execution_time=execution_time
                )
                
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ModuleAnalysisResult(
                module_name="news",
                commodity=commodity,
                analysis_date=analysis_date,
                status=AnalysisStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time
            )

    async def run_complete_analysis_flow(self, analysis_state: FuturesAnalysisState) -> Dict[str, Any]:
        """运行完整的分析流程：基础分析 + 辩论风控决策"""

        commodity = analysis_state.commodity
        analysis_date = analysis_state.analysis_date
        start_time = datetime.now()

        self.logger.info(f"开始{commodity}完整分析流程")

        try:
            # 第1阶段：基础数据分析
            self.logger.info("第1阶段：执行基础数据分析模块")

            # 并行执行基础分析模块
            tasks = []
            module_names = ['inventory', 'positioning', 'term_structure', 'technical', 'basis', 'news']

            for module_name in module_names:
                if hasattr(self, f'_run_{module_name}_analysis'):
                    task = getattr(self, f'_run_{module_name}_analysis')(commodity, analysis_date)
                    tasks.append(task)
                else:
                    self.logger.warning(f"模块 {module_name} 的分析方法不存在")

            # 等待所有基础分析完成
            if tasks:
                module_results = await asyncio.gather(*tasks, return_exceptions=True)

                # 处理结果
                for i, result in enumerate(module_results):
                    module_name = module_names[i]
                    if isinstance(result, Exception):
                        self.logger.error(f"{module_name}分析失败: {result}")
                        setattr(analysis_state, f'{module_name}_analysis', None)
                    else:
                        setattr(analysis_state, f'{module_name}_analysis', result)

            # 第2阶段：辩论风控决策
            self.logger.info("第2阶段：执行辩论风控决策分析")
            debate_result = await self.run_optimized_debate_risk_decision(analysis_state)

            # 整合最终结果
            final_result = {
                "commodity": commodity,
                "analysis_date": analysis_date,
                "process_timestamp": datetime.now().isoformat(),

                # 基础分析结果
                "inventory_analysis": analysis_state.inventory_analysis,
                "positioning_analysis": analysis_state.positioning_analysis,
                "term_structure_analysis": analysis_state.term_structure_analysis,
                "technical_analysis": analysis_state.technical_analysis,
                "basis_analysis": analysis_state.basis_analysis,
                "news_analysis": analysis_state.news_analysis,

                # 辩论风控决策结果
                "debate_result": debate_result.get("debate_result"),
                "risk_assessment": debate_result.get("risk_assessment"),
                "trading_decision": debate_result.get("trading_decision"),
                "executive_decision": debate_result.get("executive_decision"),

                # 执行信息
                "execution_time": (datetime.now() - start_time).total_seconds(),
                "success": True
            }

            self.logger.info(f"{commodity}完整分析流程执行成功，耗时: {final_result['execution_time']:.2f}秒")
            return final_result

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"{commodity}完整分析流程失败: {e}")

            return {
                "commodity": commodity,
                "analysis_date": analysis_date,
                "process_timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }

    async def run_optimized_debate_risk_decision(self, analysis_state: FuturesAnalysisState,
                                                debate_rounds: int = 3) -> Dict[str, Any]:
        """运行优化版辩论风控决策分析"""
        try:
            # 导入优化版辩论风控决策系统（让我的prompt修改生效）
            from 优化版辩论风控决策系统 import OptimizedTradingAgentsSystem
            from 期货TradingAgents系统_工具模块 import DeepSeekAPIClient

            # 使用用户配置而非硬编码的默认值
            user_config = self.config.copy() if self.config else {}
            
            # 确保必要的配置存在，但优先使用用户配置
            if "api_settings" not in user_config:
                user_config["api_settings"] = {}
            if "deepseek" not in user_config["api_settings"]:
                user_config["api_settings"]["deepseek"] = {}
            if "serper" not in user_config["api_settings"]:
                user_config["api_settings"]["serper"] = {}
            
            # 设置默认值（仅在用户未配置时）
            user_config["api_settings"]["deepseek"].setdefault("base_url", "https://api.deepseek.com/v1")
            user_config["api_settings"]["deepseek"].setdefault("timeout", 120)
            user_config["api_settings"]["serper"].setdefault("base_url", "https://google.serper.dev/search")
            
            # 兼容旧版配置：如果有单独的deepseek_api_key，也使用它
            if "deepseek_api_key" not in user_config and user_config["api_settings"]["deepseek"].get("api_key"):
                user_config["deepseek_api_key"] = user_config["api_settings"]["deepseek"]["api_key"]
            
            if "logging" not in user_config:
                user_config["logging"] = {
                    "level": "INFO",
                    "console_logging": True,
                    "file_logging": False
                }

            # 创建优化版系统实例（使用用户配置）
            system = OptimizedTradingAgentsSystem(user_config)

            # 执行完整分析
            result = await system.run_complete_analysis(analysis_state, debate_rounds)

            # 转换数据结构以匹配Streamlit界面期望的格式
            converted_result = self._convert_result_for_streamlit(result)
            return converted_result

        except Exception as e:
            self.logger.error(f"辩论风控决策分析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "commodity": analysis_state.commodity,
                "analysis_date": analysis_state.analysis_date,
                "debate_section": {
                    "winner": "未知",
                    "scores": {
                        "bull": 0.0,
                        "bear": 0.0
                    },
                    "summary": f"辩论过程因API连接问题中断: {str(e)}",
                    "rounds": []
                },
                "trading_section": {
                    "strategy_type": "暂停交易",
                    "position_size": 0.0,
                    "risk_reward_ratio": "N/A",
                    "time_horizon": "短期",
                    "reasoning": f"API连接问题导致无法进行有效分析: {str(e)}",
                    "entry_points": ["等待系统恢复后重新分析"],
                    "exit_points": ["立即停止所有交易活动"],
                    "specific_contracts": ["暂停所有合约交易"],
                    "execution_plan": "暂停交易，等待系统恢复",
                    "market_conditions": f"系统异常，无法获取市场数据: {str(e)}"
                },
                "risk_section": {
                    "overall_risk": "高风险",
                    "position_limit": 0.0,
                    "stop_loss": "立即止损",
                    "manager_opinion": f"由于API连接问题，建议暂停所有交易活动: {str(e)}"
                },
                "decision_section": {
                    "final_decision": "持有观望",
                    "position_size": 0.0,
                    "confidence": "0%",
                    "rationale": ["系统技术问题"],
                    "execution_plan": "暂停交易，等待系统恢复",
                    "monitoring_points": ["系统恢复状态", "API连接状态"],
                    "cio_statement": f"由于技术问题，暂时无法做出投资决策。建议等待系统恢复后重新分析。错误详情: {str(e)}"
                },
                "process_timestamp": datetime.now().isoformat()
            }
    
    def convert_numeric_to_text_confidence(self, confidence_value) -> str:
        """将数值信心度转换为文字格式"""
        if isinstance(confidence_value, (int, float)):
            if confidence_value >= 0.7:
                return "高"
            elif confidence_value >= 0.5:
                return "中"
            else:
                return "低"
        else:
            return str(confidence_value)  # 如果已经是文字，直接返回
    
    def _convert_result_for_streamlit(self, result) -> Dict:
        """将OptimizedTradingAgentsSystem的结果转换为Streamlit界面期望的格式"""
        try:
            # 转换辩论结果
            debate_result = result.get("debate_result", {})
            debate_section = {
                "winner": str(debate_result.get("final_winner", "未知")),
                "scores": {
                    "bull": debate_result.get("bull_score", 0.0),
                    "bear": debate_result.get("bear_score", 0.0)
                },
                "summary": debate_result.get("debate_summary", "暂无总结"),
                "rounds": debate_result.get("detailed_rounds", [])
            }
            
            # 转换交易员决策
            trading_decision = result.get("trading_decision", {})
            trading_section = {
                "strategy_type": trading_decision.get("strategy_type", "未知"),
                "position_size": trading_decision.get("position_size", "未知"),
                "risk_reward_ratio": trading_decision.get("risk_reward_ratio", "未知"),
                "time_horizon": trading_decision.get("time_horizon", "未知"),
                "reasoning": trading_decision.get("reasoning", "暂无逻辑"),
                "entry_points": trading_decision.get("entry_points", []),
                "exit_points": trading_decision.get("exit_points", []),
                "specific_contracts": trading_decision.get("specific_contracts", []),
                "execution_plan": trading_decision.get("execution_plan", "暂无执行计划"),
                "market_conditions": trading_decision.get("market_conditions", "暂无市场条件分析")
            }
            
            # 转换风险评估 - 修复：从正确位置提取风控经理意见
            risk_assessment = result.get("risk_assessment", {})
            
            # 获取风控经理的推理意见
            risk_manager_decision = risk_assessment.get("risk_manager_decision", {})
            manager_reasoning = risk_manager_decision.get("reasoning", "暂无意见")
            
            # 构建风险评估结果 - 修复：正确提取风险等级和仓位限制
            overall_risk_level = risk_assessment.get("overall_risk_level")
            if hasattr(overall_risk_level, 'value'):
                # 枚举对象，获取其值
                overall_risk_text = overall_risk_level.value
            else:
                overall_risk_text = str(overall_risk_level) if overall_risk_level else "未知"
            
            # ✅ 修复：键名应该是position_limit而不是position_size_limit
            position_size_limit = risk_assessment.get("position_limit", "未设定")  # 从字典获取
            if isinstance(position_size_limit, (int, float)):
                # 处理数值型（如0.05 = 5%），确保不会为0
                if position_size_limit <= 0:
                    position_size_limit = 0.03  # 风控最低限制3%
                position_limit_text = f"{position_size_limit * 100:.1f}%"
            elif isinstance(position_size_limit, str) and position_size_limit not in ["", "0", "0.0", "待评估"]:
                # 处理字符串型（如"5-8%"）
                position_limit_text = position_size_limit
            else:
                # 🔥 风控绝不允许"待评估"，必须给出具体限制
                position_limit_text = "3.0%"  # 保守的风控标准
            
            # 🔥 修复：正确访问RiskAssessment对象的属性
            if hasattr(risk_assessment, '__dict__'):
                # RiskAssessment对象，通过属性访问
                stop_loss_advice = getattr(risk_assessment, 'stop_loss_level', 0.02)
                manager_opinion = getattr(risk_assessment, 'risk_manager_opinion', '暂无意见')
                key_factors = getattr(risk_assessment, 'key_risk_factors', ["市场波动风险", "流动性风险", "杠杆风险"])
                mitigation_measures = getattr(risk_assessment, 'risk_mitigation', [
                    "严格执行三级风控体系",
                    "实时监控仓位和止损", 
                    "定期评估市场变化",
                    "及时调整风控参数"
                ])
            else:
                # 字典类型，通过键访问
                stop_loss_advice = risk_assessment.get("stop_loss_level", 0.02)
                manager_opinion = risk_assessment.get("risk_manager_opinion", "暂无意见")
                key_factors = risk_assessment.get("key_risk_factors", ["市场波动风险", "流动性风险", "杠杆风险"])
                mitigation_measures = risk_assessment.get("risk_mitigation", [
                    "严格执行三级风控体系",
                    "实时监控仓位和止损", 
                    "定期评估市场变化",
                    "及时调整风控参数"
                ])
            
            # 格式化止损建议
            if isinstance(stop_loss_advice, (int, float)):
                stop_loss_text = f"建议止损位: {stop_loss_advice:.1%}"
            else:
                stop_loss_text = str(stop_loss_advice)
            
            risk_section = {
                "overall_risk": overall_risk_text,
                "position_limit": position_limit_text,
                "stop_loss": stop_loss_text,
                "manager_opinion": manager_opinion,
                "key_factors": key_factors,
                "mitigation_measures": mitigation_measures
            }
            
            # 转换CIO决策
            executive_decision = result.get("executive_decision", {})
            
            # 🔥 修复：正确处理ExecutiveDecision对象的属性访问，统一使用高/中/低格式
            if hasattr(executive_decision, '__dict__'):
                # 对象类型，通过属性访问
                operational_decision = getattr(executive_decision, 'operational_decision', '中性策略')
                directional_view = getattr(executive_decision, 'directional_view', '中性')
                
                # ✅ 🔥 关键修复：直接获取字符串格式的信心度，不再进行任何转换
                # operational_confidence和directional_confidence应该已经是字符串格式（低/中/高）
                operational_confidence = getattr(executive_decision, 'operational_confidence', '中')
                directional_confidence = getattr(executive_decision, 'directional_confidence', '中')
                
                print(f"🐛 DEBUG [数据转换]: operational_confidence原始值 = {operational_confidence} (type: {type(operational_confidence)})")
                print(f"🐛 DEBUG [数据转换]: directional_confidence原始值 = {directional_confidence} (type: {type(directional_confidence)})")
                
                # 🔥 关键修复：如果不是标准格式，不要使用confidence_level进行转换
                # 因为confidence_level是整体决策信心度，不等于operational_confidence（操作信心度）
                # operational_confidence应该来自风控评估，必须直接使用，不能被其他值覆盖
                if operational_confidence not in ['高', '中', '低']:
                    print(f"⚠️ WARNING [数据转换]: operational_confidence格式异常='{operational_confidence}'，使用默认值'低'")
                    operational_confidence = '低'  # 🔥 修复：默认为保守的"低"
                
                if directional_confidence not in ['高', '中', '低']:
                    print(f"⚠️ WARNING [数据转换]: directional_confidence格式异常='{directional_confidence}'，使用默认值'中'")
                    directional_confidence = '中'
                        
                final_decision = getattr(executive_decision, 'final_decision', '未知')
                position_size = getattr(executive_decision, 'position_size', 0.0)
                cio_statement = getattr(executive_decision, 'cio_statement', '暂无声明')
                execution_plan = getattr(executive_decision, 'execution_plan', '暂无执行计划')
                monitoring_points = getattr(executive_decision, 'monitoring_points', [])
            else:
                # 字典类型，通过键访问
                operational_decision = executive_decision.get("operational_decision", "中性策略")
                directional_view = executive_decision.get("directional_view", "中性")
                
                # 🔥 修复：直接获取字符串格式的信心度，不进行转换
                operational_confidence = executive_decision.get("operational_confidence", "中")
                directional_confidence = executive_decision.get("directional_confidence", "中")
                
                print(f"🐛 DEBUG [数据转换-字典分支]: operational_confidence = {operational_confidence} (type: {type(operational_confidence)})")
                print(f"🐛 DEBUG [数据转换-字典分支]: directional_confidence = {directional_confidence} (type: {type(directional_confidence)})")
                
                # 验证格式
                if operational_confidence not in ['高', '中', '低']:
                    print(f"⚠️ WARNING [数据转换-字典分支]: operational_confidence格式异常='{operational_confidence}'，使用默认值'低'")
                    operational_confidence = '低'
                
                if directional_confidence not in ['高', '中', '低']:
                    print(f"⚠️ WARNING [数据转换-字典分支]: directional_confidence格式异常='{directional_confidence}'，使用默认值'中'")
                    directional_confidence = '中'
                
                final_decision = executive_decision.get("final_decision", "未知")
                position_size = executive_decision.get("position_size", 0.0)
                cio_statement = executive_decision.get("cio_statement", "暂无声明")
                execution_plan = executive_decision.get("execution_plan", "暂无执行计划")
                monitoring_points = executive_decision.get("monitoring_points", [])
                
            # 格式化显示值
            if isinstance(position_size, (int, float)) and position_size > 0:
                position_size_text = f"{position_size * 100:.1f}%"
            else:
                position_size_text = "待确定"
                
            decision_section = {
                "operational_decision": operational_decision,      # 🔥 操作决策
                "directional_view": directional_view,             # 🔥 方向判断
                "operational_confidence": operational_confidence,  # 🔥 操作信心度
                "directional_confidence": directional_confidence, # 🔥 方向信心度
                "final_decision": final_decision,
                "position_size": position_size_text,
                "confidence": operational_confidence,
                "rationale": [],  # 🔥 删除决策理由显示
                "execution_plan": execution_plan,
                "monitoring_points": monitoring_points,
                "cio_statement": cio_statement,
                "stop_loss": None  # 🔥 删除止损标准显示
            }
            
            # 返回转换后的结果
            return {
                "success": True,
                "commodity": result.get("commodity", "未知"),
                "analysis_date": result.get("analysis_date", "未知"),
                "debate_section": debate_section,
                "trading_section": trading_section,
                "risk_section": risk_section,
                "decision_section": decision_section,
                "process_timestamp": result.get("process_timestamp", datetime.now().isoformat())
            }
            
        except Exception as e:
            self.logger.error(f"数据转换失败: {e}")
            # 返回默认结构
            return {
                "success": False,
                "error": f"数据转换失败: {str(e)}",
                "commodity": result.get("commodity", "未知"),
                "analysis_date": result.get("analysis_date", "未知"),
                "debate_section": {"winner": "未知", "scores": {"bull": 0.0, "bear": 0.0}, "summary": "数据转换失败", "rounds": []},
                "trading_section": {"strategy_type": "暂停交易", "position_size": "0%", "risk_reward_ratio": "N/A", "time_horizon": "短期", "reasoning": "数据转换失败"},
                "risk_section": {"overall_risk": "高风险", "position_limit": "0%", "stop_loss": "立即止损", "manager_opinion": "数据转换失败"},
                "decision_section": {
                    "final_decision": "持有观望", 
                    "position_size": "0%", 
                    "confidence": "0%", 
                    "rationale": ["数据转换失败"],
                    "execution_plan": "暂停交易，等待系统恢复",
                    "monitoring_points": ["系统状态监控"],
                    "cio_statement": "数据转换失败"
                },
                "process_timestamp": datetime.now().isoformat()
            }

# ============================================================================
# 5. 测试函数
# ============================================================================

def test_infrastructure():
    """测试基础架构功能"""
    print("🧪 测试基础架构功能...")
    
    # 测试配置管理
    config = FuturesTradingAgentsConfig()
    print(f"✅ 配置加载成功，数据目录: {config.get('data_root_dir')}")
    
    # 测试分析状态
    analysis_state = FuturesAnalysisState(
        commodity="RB",
        analysis_date="2025-01-09"
    )
    
    # 添加模块结果
    inventory_result = ModuleAnalysisResult(
        module_name="inventory",
        commodity="RB", 
        analysis_date="2025-01-09",
        status=AnalysisStatus.COMPLETED,
        result_data={"test": "data"},
        confidence_score=0.85
    )
    
    analysis_state.set_module_result("inventory", inventory_result)
    print(f"✅ 分析进度: {analysis_state.get_analysis_progress():.1%}")
    print(f"✅ 完成模块: {analysis_state.get_completed_modules()}")
    
    # 测试分析整合器
    integrator = FuturesAnalysisIntegrator()
    print("✅ 分析整合器创建成功")
    
    print("✅ 基础架构测试完成")

if __name__ == "__main__":
    test_infrastructure()
