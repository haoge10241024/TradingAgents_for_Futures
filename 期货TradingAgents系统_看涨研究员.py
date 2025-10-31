#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货Trading Agents系统 - 看涨研究员模块
专门针对期货市场设计的多头分析专家

功能特点：
1. 基于6个分析模块的深度看涨分析
2. 期货市场专用的多头逻辑
3. 跨模块数据关联利用
4. 专业的辩论论点准备
5. DeepSeek推理模式支持

作者: AI Assistant
版本: 1.0.0
创建时间: 2025-01-19
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import numpy as np
import pandas as pd
from pathlib import Path

# 自定义JSON序列化函数
def safe_json_dumps(data, **kwargs):
    """安全的JSON序列化，处理numpy数据类型和路径对象"""
    def convert_types(obj, _seen=None):
        if _seen is None:
            _seen = set()
        
        # 防止递归
        obj_id = id(obj)
        if obj_id in _seen:
            return str(obj)  # 递归对象转为字符串
        _seen.add(obj_id)
        
        try:
            if isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, pd.Timestamp):
                return obj.isoformat()
            elif isinstance(obj, (Path, type(Path()))):  # 处理Path和WindowsPath对象
                return str(obj)
            elif hasattr(obj, '__fspath__'):  # 处理所有路径对象
                return str(obj)
            elif hasattr(obj, 'item'):  # numpy scalar
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_types(v, _seen.copy()) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_types(v, _seen.copy()) for v in obj]
            elif isinstance(obj, tuple):
                return [convert_types(v, _seen.copy()) for v in obj]
            return obj
        except Exception:
            # 如果转换失败，返回字符串表示
            return str(obj)
        finally:
            _seen.discard(obj_id)
    
    converted_data = convert_types(data)
    return json.dumps(converted_data, **kwargs)

# 导入基础架构
from 期货TradingAgents系统_基础架构 import (
    FuturesAnalysisState, 
    ModuleAnalysisResult,
    CrossModuleRelationship,
    AnalysisStatus,
    DebateStance
)
from 期货TradingAgents系统_工具模块 import (
    DeepSeekAPIClient,
    DataValidator,
    TimeUtils,
    log_execution_time,
    retry_on_failure
)

# ============================================================================
# 1. 看涨研究员核心数据结构
# ============================================================================

@dataclass
class BullishFactor:
    """看涨因素"""
    factor_name: str
    evidence: str
    strength: float  # 1-10
    module_source: str
    confidence: float  # 0-1
    supporting_data: Dict = None

@dataclass
class GrowthCatalyst:
    """增长催化剂"""
    catalyst_name: str
    probability: float  # 0-1
    impact_level: str  # "low", "medium", "high"
    timeline: str  # "short_term", "medium_term", "long_term"
    description: str

@dataclass
class BullishAnalysisResult:
    """看涨分析结果"""
    commodity: str
    analysis_date: str
    researcher_type: str = "bull"
    
    # 核心分析结果
    bullish_factors: List[BullishFactor] = None
    growth_catalysts: List[GrowthCatalyst] = None
    upside_targets: Dict[str, float] = None
    risk_mitigation: List[Dict] = None
    
    # 辩论准备
    key_arguments: List[str] = None
    debate_points: Dict = None
    counter_bear_arguments: List[str] = None
    
    # 评估指标
    overall_confidence: float = 0.0
    bullish_score: float = 0.0  # 0-100
    conviction_level: str = "medium"  # "low", "medium", "high"
    
    # 元数据
    analysis_timestamp: str = ""
    reasoning_process: str = ""

# ============================================================================
# 2. 看涨研究员主类
# ============================================================================

class FuturesBullResearcher:
    """期货看涨研究员 - 专业的多头分析专家"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.stance = DebateStance.BULLISH
        self.expertise_areas = [
            "供需基本面看涨因素",
            "资金面看涨信号", 
            "技术面上涨动能",
            "基差套利机会",
            "消息面积极因素",
            "跨模块协同效应"
        ]
        
        # API配置
        self.deepseek_config = config.get("api_settings", {}).get("deepseek", {})
        self.api_key = self.deepseek_config.get("api_key", "")
        
        # 分析参数
        self.confidence_bias = config.get("researcher_agents", {}).get("bull_researcher", {}).get("confidence_bias", 0.1)
        self.use_reasoning_mode = config.get("debate_settings", {}).get("enable_reasoning_mode", True)
        
        # 日志
        self.logger = logging.getLogger("FuturesBullResearcher")
        
        # 期货品种映射
        self.commodity_names = {
            "RB": "螺纹钢", "HC": "热卷", "I": "铁矿石", "J": "焦炭", "JM": "焦煤",
            "CU": "沪铜", "AL": "沪铝", "ZN": "沪锌", "NI": "沪镍", "AU": "黄金", "AG": "白银",
            "RU": "橡胶", "BU": "沥青", "FU": "燃油", "MA": "甲醇", "TA": "PTA",
            "SR": "白糖", "CF": "棉花", "M": "豆粕", "Y": "豆油", "P": "棕榈油"
        }
    
    @log_execution_time()
    @retry_on_failure(max_retries=2)
    async def analyze_bullish_perspective(self, analysis_state: FuturesAnalysisState) -> BullishAnalysisResult:
        """从看涨角度深度分析期货市场"""
        
        self.logger.info(f"开始看涨分析: {analysis_state.commodity} ({analysis_state.analysis_date})")
        
        # 1. 预处理和验证数据
        validated_state = self._validate_analysis_state(analysis_state)
        
        # 2. 构建看涨分析Prompt
        analysis_prompt = self._build_bullish_analysis_prompt(validated_state)
        
        # 3. 调用DeepSeek进行分析
        if self.use_reasoning_mode:
            analysis_response = await self._call_deepseek_reasoning(analysis_prompt)
        else:
            analysis_response = await self._call_deepseek_chat(analysis_prompt)
        
        # 4. 解析分析结果
        bullish_result = self._parse_analysis_response(analysis_response, validated_state)
        
        # 5. 准备辩论要点
        bullish_result.debate_points = self._prepare_debate_points(bullish_result, validated_state)
        
        # 6. 计算综合评分
        bullish_result = self._calculate_bullish_scores(bullish_result, validated_state)
        
        self.logger.info(f"看涨分析完成，综合评分: {bullish_result.bullish_score:.1f}")
        
        return bullish_result
    
    def _validate_analysis_state(self, state: FuturesAnalysisState) -> FuturesAnalysisState:
        """验证和预处理分析状态"""
        
        # 验证基础数据
        if not DataValidator.validate_commodity_code(state.commodity):
            raise ValueError(f"无效的商品代码: {state.commodity}")
        
        if not DataValidator.validate_date_format(state.analysis_date):
            raise ValueError(f"无效的日期格式: {state.analysis_date}")
        
        # 检查完成的模块数量
        completed_modules = state.get_completed_modules()
        if len(completed_modules) < 3:
            self.logger.warning(f"只有 {len(completed_modules)} 个模块完成分析，可能影响分析质量")
        
        self.logger.info(f"数据验证通过，已完成模块: {completed_modules}")
        
        return state
    
    def _build_bullish_analysis_prompt(self, state: FuturesAnalysisState) -> str:
        """构建看涨分析的专用Prompt"""
        
        commodity_name = self.commodity_names.get(state.commodity, state.commodity)
        
        # 收集各模块数据
        module_data = self._collect_module_data(state)
        
        # 收集跨模块关联数据
        relationship_data = self._collect_relationship_data(state)
        
        prompt = f"""
你是一位拥有15年期货市场经验的资深看涨研究员，专门从多头角度分析期货投资机会。
你的任务是基于以下全面的分析数据，从看涨角度深度分析{commodity_name}({state.commodity})的投资机会。

## 基础信息
**品种**: {commodity_name} ({state.commodity})
**分析日期**: {state.analysis_date}
**分析模式**: 看涨研究员专业分析

## 各模块分析数据

### 📊 库存与仓单分析
{safe_json_dumps(module_data.get('inventory', {}), ensure_ascii=False, indent=2)}

### 💰 持仓席位分析
{safe_json_dumps(module_data.get('positioning', {}), ensure_ascii=False, indent=2)}

### 📈 期限结构分析
{safe_json_dumps(module_data.get('term_structure', {}), ensure_ascii=False, indent=2)}

### 🔍 技术面分析
{safe_json_dumps(module_data.get('technical', {}), ensure_ascii=False, indent=2)}

### ⚖️ 基差分析
{safe_json_dumps(module_data.get('basis', {}), ensure_ascii=False, indent=2)}

### 📰 新闻分析
{safe_json_dumps(module_data.get('news', {}), ensure_ascii=False, indent=2)}

## 跨模块关联分析
{safe_json_dumps(relationship_data, ensure_ascii=False, indent=2)}

## 专业分析要求

作为资深看涨研究员，请从以下维度进行深度分析：

### 🔍 供需基本面看涨因素
1. **库存水平分析**: 当前库存是否支持价格上涨？库存去化速度如何？
2. **仓单变化解读**: 仓单增减是否暗示供应紧张或需求增强？
3. **供需平衡判断**: 未来供需格局是否有利于价格上涨？
4. **季节性因素**: 是否存在季节性需求旺季支撑？

### 💰 资金面看涨信号
1. **主力资金动向**: 主力是否在积极建立多头仓位？
2. **聪明钱分析**: 知情资金是否看涨？持仓效率如何？
3. **席位集中度**: 多头集中度是否上升？
4. **资金流向**: 增量资金是否流入？

### 📈 技术面上涨动能
1. **趋势分析**: 技术趋势是否支持上涨？
2. **突破信号**: 是否出现有效的技术突破？
3. **动量指标**: 上涨动量是否充足？
4. **支撑阻力**: 支撑位是否稳固？阻力位是否可突破？

### ⚖️ 基差套利机会
1. **基差结构**: 当前基差结构是否有利现货？
2. **套利空间**: 是否存在期现套利机会？
3. **基差收敛**: 基差收敛方向是否支持期货上涨？

### 📰 消息面积极因素
1. **政策环境**: 政策是否有利于该品种？
2. **产业动态**: 产业链上下游是否有积极变化？
3. **宏观环境**: 宏观经济环境是否支持商品上涨？
4. **市场情绪**: 市场预期是否转向乐观？

### 🔄 跨模块协同效应
1. **数据一致性**: 各模块结论是否相互支撑？
2. **信号强度**: 跨模块信号的综合强度如何？
3. **逻辑链条**: 是否形成完整的看涨逻辑链？
4. **关键驱动**: 最核心的看涨驱动因素是什么？

## 输出要求

请按以下JSON格式输出详细的看涨分析结果：

```json
{{
    "bullish_factors": [
        {{
            "factor_name": "具体看涨因素名称",
            "evidence": "支撑该因素的具体证据",
            "strength": 8.5,
            "module_source": "数据来源模块",
            "confidence": 0.85,
            "supporting_data": {{
                "key_metrics": "关键指标",
                "trend_direction": "趋势方向",
                "historical_comparison": "历史对比"
            }}
        }}
    ],
    "growth_catalysts": [
        {{
            "catalyst_name": "增长催化剂名称",
            "probability": 0.8,
            "impact_level": "high",
            "timeline": "medium_term",
            "description": "详细描述催化剂的作用机制"
        }}
    ],
    "upside_targets": {{
        "short_term": "短期目标价位及理由",
        "medium_term": "中期目标价位及理由",
        "long_term": "长期目标价位及理由"
    }},
    "risk_mitigation": [
        {{
            "risk": "潜在风险描述",
            "mitigation": "风险缓解措施",
            "monitoring": "需要监控的指标"
        }}
    ],
    "key_arguments": [
        "核心看涨论点1：具体且有说服力",
        "核心看涨论点2：基于数据支撑",
        "核心看涨论点3：逻辑清晰完整"
    ],
    "reasoning_process": "详细的分析推理过程，展示从数据到结论的逻辑链条",
    "overall_confidence": 0.85,
    "conviction_level": "high"
}}
```

## 分析原则

1. **数据驱动**: 所有论点必须有具体数据支撑
2. **逻辑严密**: 确保分析逻辑清晰完整
3. **专业准确**: 符合期货市场规律和专业标准
4. **辩论准备**: 为与看跌研究员的辩论做好充分准备
5. **风险意识**: 在看涨的同时也要识别和管理风险

请开始你的专业看涨分析。
"""
        
        return prompt
    
    def _collect_module_data(self, state: FuturesAnalysisState) -> Dict:
        """收集各模块的分析数据"""
        
        module_data = {}
        
        modules = {
            'inventory': state.inventory_analysis,
            'positioning': state.positioning_analysis,
            'term_structure': state.term_structure_analysis,
            'technical': state.technical_analysis,
            'basis': state.basis_analysis,
            'news': state.news_analysis
        }
        
        for name, analysis in modules.items():
            if analysis and analysis.status == AnalysisStatus.COMPLETED:
                module_data[name] = {
                    "status": "completed",
                    "confidence": analysis.confidence_score,
                    "data": analysis.result_data,
                    "execution_time": analysis.execution_time
                }
            else:
                module_data[name] = {
                    "status": "unavailable",
                    "reason": analysis.error_message if analysis else "module not executed"
                }
        
        return module_data
    
    def _collect_relationship_data(self, state: FuturesAnalysisState) -> Dict:
        """收集跨模块关联数据"""
        
        relationship_data = {}
        
        for relationship in state.cross_relationships:
            relationship_data[relationship.relationship_type] = {
                "modules": relationship.modules_involved,
                "correlation_strength": relationship.correlation_strength,
                "logical_consistency": relationship.logical_consistency,
                "evidence_strength": relationship.evidence_strength,
                "data": relationship.relationship_data
            }
        
        return relationship_data
    
    async def _call_deepseek_reasoning(self, prompt: str) -> Dict:
        """调用DeepSeek推理模式"""
        
        async with DeepSeekAPIClient(self.api_key) as client:
            response = await client.reasoning_completion(
                prompt=prompt,
                model=self.deepseek_config.get("reasoning_model", "deepseek-reasoner"),
                temperature=self.deepseek_config.get("temperature", 0.1),
                max_tokens=self.deepseek_config.get("max_tokens", 4000)
            )
            
            if not response.get("success"):
                raise Exception(f"DeepSeek推理调用失败: {response.get('error')}")
            
            return response
    
    async def _call_deepseek_chat(self, prompt: str) -> Dict:
        """调用DeepSeek聊天模式"""
        
        async with DeepSeekAPIClient(self.api_key) as client:
            messages = [
                {
                    "role": "system", 
                    "content": "你是一位专业的期货看涨研究员，拥有丰富的多头分析经验。请基于提供的数据进行专业的看涨分析。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            response = await client.chat_completion(
                messages=messages,
                model=self.deepseek_config.get("model", "deepseek-chat"),
                temperature=self.deepseek_config.get("temperature", 0.1),
                max_tokens=self.deepseek_config.get("max_tokens", 4000)
            )
            
            if not response.get("success"):
                raise Exception(f"DeepSeek聊天调用失败: {response.get('error')}")
            
            return response
    
    def _parse_analysis_response(self, response: Dict, state: FuturesAnalysisState) -> BullishAnalysisResult:
        """解析分析响应结果"""
        
        try:
            content = response.get("content", "")
            
            # 尝试提取JSON部分
            json_start = content.find("```json")
            json_end = content.find("```", json_start + 7)
            
            if json_start != -1 and json_end != -1:
                json_content = content[json_start + 7:json_end].strip()
                analysis_data = json.loads(json_content)
            else:
                # 如果没有找到JSON块，尝试直接解析整个内容
                analysis_data = json.loads(content)
            
            # 解析看涨因素
            bullish_factors = []
            for factor_data in analysis_data.get("bullish_factors", []):
                factor = BullishFactor(
                    factor_name=factor_data.get("factor_name", ""),
                    evidence=factor_data.get("evidence", ""),
                    strength=factor_data.get("strength", 5.0),
                    module_source=factor_data.get("module_source", "unknown"),
                    confidence=factor_data.get("confidence", 0.5),
                    supporting_data=factor_data.get("supporting_data", {})
                )
                bullish_factors.append(factor)
            
            # 解析增长催化剂
            growth_catalysts = []
            for catalyst_data in analysis_data.get("growth_catalysts", []):
                catalyst = GrowthCatalyst(
                    catalyst_name=catalyst_data.get("catalyst_name", ""),
                    probability=catalyst_data.get("probability", 0.5),
                    impact_level=catalyst_data.get("impact_level", "medium"),
                    timeline=catalyst_data.get("timeline", "medium_term"),
                    description=catalyst_data.get("description", "")
                )
                growth_catalysts.append(catalyst)
            
            # 构建结果对象
            result = BullishAnalysisResult(
                commodity=state.commodity,
                analysis_date=state.analysis_date,
                bullish_factors=bullish_factors,
                growth_catalysts=growth_catalysts,
                upside_targets=analysis_data.get("upside_targets", {}),
                risk_mitigation=analysis_data.get("risk_mitigation", []),
                key_arguments=analysis_data.get("key_arguments", []),
                overall_confidence=analysis_data.get("overall_confidence", 0.5),
                conviction_level=analysis_data.get("conviction_level", "medium"),
                reasoning_process=analysis_data.get("reasoning_process", ""),
                analysis_timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"解析分析响应失败: {e}")
            
            # 返回默认结果
            return BullishAnalysisResult(
                commodity=state.commodity,
                analysis_date=state.analysis_date,
                bullish_factors=[],
                growth_catalysts=[],
                key_arguments=["分析解析失败，请检查API响应格式"],
                overall_confidence=0.3,
                conviction_level="low",
                analysis_timestamp=datetime.now().isoformat()
            )
    
    def _prepare_debate_points(self, result: BullishAnalysisResult, state: FuturesAnalysisState) -> Dict:
        """准备辩论要点"""
        
        # 按强度排序看涨因素
        sorted_factors = sorted(result.bullish_factors, key=lambda x: x.strength, reverse=True)
        
        # 准备主要论点
        main_arguments = []
        for factor in sorted_factors[:3]:  # 取前3个最强的因素
            main_arguments.append({
                "argument": factor.factor_name,
                "evidence": factor.evidence,
                "strength": factor.strength,
                "source": factor.module_source
            })
        
        # 准备反驳空头的论点
        counter_bear_points = [
            "供需基本面改善趋势不可逆转",
            "技术面突破确认上涨动能充足",
            "主力资金积极布局显示机构看好",
            "政策环境和宏观背景支持商品上涨",
            "风险因素可控且有相应对冲措施"
        ]
        
        # 准备证据支撑
        evidence_support = {
            "data_quality": len([f for f in result.bullish_factors if f.confidence > 0.7]),
            "cross_module_consistency": len([r for r in state.cross_relationships if r.logical_consistency]),
            "conviction_indicators": [
                f"信心水平: {result.overall_confidence:.1%}",
                f"看涨因素数量: {len(result.bullish_factors)}",
                f"催化剂数量: {len(result.growth_catalysts)}"
            ]
        }
        
        debate_points = {
            "main_arguments": main_arguments,
            "counter_bear_points": counter_bear_points,
            "evidence_support": evidence_support,
            "key_talking_points": result.key_arguments,
            "risk_acknowledgment": result.risk_mitigation,
            "confidence_level": result.overall_confidence
        }
        
        return debate_points
    
    def _calculate_bullish_scores(self, result: BullishAnalysisResult, state: FuturesAnalysisState) -> BullishAnalysisResult:
        """计算综合看涨评分"""
        
        # 计算基础分数
        factor_score = 0
        if result.bullish_factors:
            factor_score = sum(f.strength * f.confidence for f in result.bullish_factors) / len(result.bullish_factors)
        
        # 计算催化剂分数
        catalyst_score = 0
        if result.growth_catalysts:
            impact_weights = {"low": 1, "medium": 2, "high": 3}
            catalyst_score = sum(
                c.probability * impact_weights.get(c.impact_level, 1) 
                for c in result.growth_catalysts
            ) / len(result.growth_catalysts)
        
        # 计算跨模块一致性分数
        consistency_score = 0
        if state.cross_relationships:
            consistency_score = sum(
                r.correlation_strength for r in state.cross_relationships if r.logical_consistency
            ) / len(state.cross_relationships)
        
        # 综合评分 (0-100)
        bullish_score = (
            factor_score * 0.4 +  # 看涨因素权重40%
            catalyst_score * 0.3 +  # 催化剂权重30%
            consistency_score * 10 * 0.2 +  # 一致性权重20%
            result.overall_confidence * 10 * 0.1  # 整体信心权重10%
        ) * 10  # 转换为0-100分
        
        # 应用信心偏差
        bullish_score = min(100, bullish_score + self.confidence_bias * 100)
        
        # 更新结果
        result.bullish_score = bullish_score
        
        # 根据分数确定信念水平
        if bullish_score >= 80:
            result.conviction_level = "high"
        elif bullish_score >= 60:
            result.conviction_level = "medium"
        else:
            result.conviction_level = "low"
        
        return result
    
    def get_researcher_info(self) -> Dict:
        """获取研究员信息"""
        return {
            "name": "期货看涨研究员",
            "stance": self.stance.value,
            "expertise_areas": self.expertise_areas,
            "confidence_bias": self.confidence_bias,
            "version": "1.0.0"
        }

# ============================================================================
# 3. 测试和演示代码
# ============================================================================

async def test_bull_researcher():
    """测试看涨研究员"""
    
    print("🐂 测试期货看涨研究员...")
    
    # 加载配置
    from 期货TradingAgents系统_基础架构 import FuturesTradingAgentsConfig
    config = FuturesTradingAgentsConfig().to_dict()
    
    # 创建看涨研究员
    bull_researcher = FuturesBullResearcher(config)
    
    print(f"研究员信息: {bull_researcher.get_researcher_info()}")
    
    # 创建模拟的分析状态
    from 期货TradingAgents系统_基础架构 import FuturesAnalysisState, ModuleAnalysisResult
    
    # 模拟库存分析结果
    inventory_result = ModuleAnalysisResult(
        module_name="inventory",
        commodity="RB",
        analysis_date="2025-01-19",
        status=AnalysisStatus.COMPLETED,
        result_data={
            "库存水平": "偏低",
            "库存趋势": "下降", 
            "仓单变化": "减少",
            "供需平衡": "偏紧"
        },
        confidence_score=0.8
    )
    
    # 模拟技术分析结果
    technical_result = ModuleAnalysisResult(
        module_name="technical",
        commodity="RB",
        analysis_date="2025-01-19",
        status=AnalysisStatus.COMPLETED,
        result_data={
            "趋势方向": "上涨",
            "技术指标": "强势",
            "突破信号": "有效突破",
            "动量": "充足"
        },
        confidence_score=0.85
    )
    
    # 创建分析状态
    analysis_state = FuturesAnalysisState(
        commodity="RB",
        analysis_date="2025-01-19"
    )
    analysis_state.inventory_analysis = inventory_result
    analysis_state.technical_analysis = technical_result
    
    try:
        # 注意：这需要有效的DeepSeek API密钥
        if config.get("api_settings", {}).get("deepseek", {}).get("api_key"):
            print("\n🔍 开始看涨分析...")
            bullish_result = await bull_researcher.analyze_bullish_perspective(analysis_state)
            
            print(f"✅ 看涨分析完成")
            print(f"   综合评分: {bullish_result.bullish_score:.1f}")
            print(f"   信念水平: {bullish_result.conviction_level}")
            print(f"   看涨因素数量: {len(bullish_result.bullish_factors)}")
            print(f"   催化剂数量: {len(bullish_result.growth_catalysts)}")
            
            # 保存结果
            result_file = Path("test_bull_analysis_result.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(bullish_result), f, ensure_ascii=False, indent=2, default=str)
            
            print(f"   结果已保存到: {result_file}")
        else:
            print("⚠️  未配置DeepSeek API密钥，跳过实际分析测试")
            print("   请在配置文件中设置api_settings.deepseek.api_key")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n✅ 看涨研究员测试完成")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_bull_researcher())

