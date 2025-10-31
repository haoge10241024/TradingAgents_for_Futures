#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货Trading Agents系统 - 看跌研究员模块
专门针对期货市场设计的空头分析专家

功能特点：
1. 基于6个分析模块的深度看跌分析
2. 期货市场专用的空头逻辑
3. 风险因素识别和评估
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
    """安全的JSON序列化，处理numpy数据类型"""
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
# 1. 看跌研究员核心数据结构
# ============================================================================

@dataclass
class BearishFactor:
    """看跌因素"""
    factor_name: str
    evidence: str
    severity: float  # 1-10 (风险严重程度)
    module_source: str
    confidence: float  # 0-1
    risk_probability: float  # 0-1 (风险发生概率)
    supporting_data: Dict = None

@dataclass
class RiskCatalyst:
    """风险催化剂"""
    catalyst_name: str
    trigger_probability: float  # 0-1
    impact_severity: str  # "low", "medium", "high"
    timeline: str  # "immediate", "short_term", "medium_term"
    description: str
    mitigation_difficulty: str  # "easy", "moderate", "difficult"

@dataclass
class BearishAnalysisResult:
    """看跌分析结果"""
    commodity: str
    analysis_date: str
    researcher_type: str = "bear"
    
    # 核心分析结果
    bearish_factors: List[BearishFactor] = None
    risk_catalysts: List[RiskCatalyst] = None
    downside_targets: Dict[str, float] = None
    risk_scenarios: List[Dict] = None
    
    # 辩论准备
    key_arguments: List[str] = None
    debate_points: Dict = None
    counter_bull_arguments: List[str] = None
    
    # 评估指标
    overall_risk_level: float = 0.0
    bearish_score: float = 0.0  # 0-100
    conviction_level: str = "medium"  # "low", "medium", "high"
    
    # 元数据
    analysis_timestamp: str = ""
    reasoning_process: str = ""

# ============================================================================
# 2. 看跌研究员主类
# ============================================================================

class FuturesBearResearcher:
    """期货看跌研究员 - 专业的空头分析专家"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.stance = DebateStance.BEARISH
        self.expertise_areas = [
            "供应过剩风险",
            "资金面看跌信号",
            "技术面下跌风险", 
            "基差套利风险",
            "消息面负面因素",
            "系统性风险评估"
        ]
        
        # API配置
        self.deepseek_config = config.get("api_settings", {}).get("deepseek", {})
        self.api_key = self.deepseek_config.get("api_key", "")
        
        # 分析参数
        self.confidence_bias = config.get("researcher_agents", {}).get("bear_researcher", {}).get("confidence_bias", 0.1)
        self.use_reasoning_mode = config.get("debate_settings", {}).get("enable_reasoning_mode", True)
        
        # 日志
        self.logger = logging.getLogger("FuturesBearResearcher")
        
        # 期货品种映射
        self.commodity_names = {
            "RB": "螺纹钢", "HC": "热卷", "I": "铁矿石", "J": "焦炭", "JM": "焦煤",
            "CU": "沪铜", "AL": "沪铝", "ZN": "沪锌", "NI": "沪镍", "AU": "黄金", "AG": "白银",
            "RU": "橡胶", "BU": "沥青", "FU": "燃油", "MA": "甲醇", "TA": "PTA",
            "SR": "白糖", "CF": "棉花", "M": "豆粕", "Y": "豆油", "P": "棕榈油"
        }
    
    @log_execution_time()
    @retry_on_failure(max_retries=2)
    async def analyze_bearish_perspective(self, analysis_state: FuturesAnalysisState) -> BearishAnalysisResult:
        """从看跌角度深度分析期货市场风险"""
        
        self.logger.info(f"开始看跌分析: {analysis_state.commodity} ({analysis_state.analysis_date})")
        
        # 1. 预处理和验证数据
        validated_state = self._validate_analysis_state(analysis_state)
        
        # 2. 构建看跌分析Prompt
        analysis_prompt = self._build_bearish_analysis_prompt(validated_state)
        
        # 3. 调用DeepSeek进行分析
        if self.use_reasoning_mode:
            analysis_response = await self._call_deepseek_reasoning(analysis_prompt)
        else:
            analysis_response = await self._call_deepseek_chat(analysis_prompt)
        
        # 4. 解析分析结果
        bearish_result = self._parse_analysis_response(analysis_response, validated_state)
        
        # 5. 准备辩论要点
        bearish_result.debate_points = self._prepare_debate_points(bearish_result, validated_state)
        
        # 6. 计算综合评分
        bearish_result = self._calculate_bearish_scores(bearish_result, validated_state)
        
        self.logger.info(f"看跌分析完成，风险评分: {bearish_result.bearish_score:.1f}")
        
        return bearish_result
    
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
    
    def _build_bearish_analysis_prompt(self, state: FuturesAnalysisState) -> str:
        """构建看跌分析的专用Prompt"""
        
        commodity_name = self.commodity_names.get(state.commodity, state.commodity)
        
        # 收集各模块数据
        module_data = self._collect_module_data(state)
        
        # 收集跨模块关联数据
        relationship_data = self._collect_relationship_data(state)
        
        prompt = f"""
你是一位拥有15年期货市场经验的资深看跌研究员，专门从空头角度分析期货投资风险。
你的任务是基于以下全面的分析数据，从看跌角度深度分析{commodity_name}({state.commodity})的投资风险。

## 基础信息
**品种**: {commodity_name} ({state.commodity})
**分析日期**: {state.analysis_date}
**分析模式**: 看跌研究员专业风险分析

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

## 专业风险分析要求

作为资深看跌研究员，请从以下维度进行深度风险分析：

### 🚨 供应过剩风险
1. **库存堆积风险**: 库存是否存在过度累积？去库存进度是否低于预期？
2. **产能释放压力**: 新增产能是否对市场造成供应压力？
3. **仓单集中风险**: 仓单是否大量增加？是否存在集中交割风险？
4. **季节性供应**: 是否面临季节性供应高峰？

### 💸 资金面看跌信号
1. **主力资金撤离**: 主力是否在减仓或建立空头仓位？
2. **聪明钱警示**: 知情资金是否看空？持仓效率是否下降？
3. **流动性风险**: 是否存在流动性枯竭风险？
4. **资金成本上升**: 融资成本上升是否影响持仓意愿？

### 📉 技术面下跌风险
1. **趋势恶化**: 技术趋势是否转向下跌？
2. **支撑破位**: 关键支撑位是否已经失守？
3. **动量衰减**: 上涨动量是否明显衰减？
4. **形态恶化**: 是否出现看跌技术形态？

### ⚖️ 基差套利风险
1. **基差结构恶化**: 基差结构是否不利期货？
2. **套利压力**: 是否存在大量套利盘压制？
3. **交割风险**: 临近交割月是否存在交割压力？

### 📰 消息面负面因素
1. **政策风险**: 政策环境是否转向不利？
2. **需求萎缩**: 下游需求是否出现萎缩信号？
3. **宏观环境**: 宏观经济是否面临下行压力？
4. **突发事件**: 是否存在潜在的黑天鹅风险？

### 🔗 系统性风险评估
1. **连锁反应**: 该品种下跌是否会引发连锁反应？
2. **相关性风险**: 相关品种的风险是否会传导？
3. **市场情绪**: 市场情绪是否过于乐观存在修正风险？
4. **估值风险**: 当前价位是否存在高估风险？

## 输出要求

请按以下JSON格式输出详细的看跌风险分析结果：

```json
{{
    "bearish_factors": [
        {{
            "factor_name": "具体看跌风险因素名称",
            "evidence": "支撑该风险的具体证据",
            "severity": 8.5,
            "module_source": "数据来源模块",
            "confidence": 0.85,
            "risk_probability": 0.8,
            "supporting_data": {{
                "key_metrics": "关键风险指标",
                "trend_direction": "恶化趋势",
                "historical_comparison": "历史风险对比"
            }}
        }}
    ],
    "risk_catalysts": [
        {{
            "catalyst_name": "风险催化剂名称",
            "trigger_probability": 0.7,
            "impact_severity": "high",
            "timeline": "short_term",
            "description": "详细描述催化剂的触发机制",
            "mitigation_difficulty": "difficult"
        }}
    ],
    "downside_targets": {{
        "short_term": "短期下跌目标及理由",
        "medium_term": "中期下跌目标及理由",
        "long_term": "长期风险底线及理由"
    }},
    "risk_scenarios": [
        {{
            "scenario_name": "风险情景名称",
            "probability": 0.6,
            "impact": "预期影响",
            "triggers": ["触发条件1", "触发条件2"],
            "mitigation": "应对措施"
        }}
    ],
    "key_arguments": [
        "核心看跌论点1：具体且有说服力",
        "核心看跌论点2：基于风险数据支撑",
        "核心看跌论点3：逻辑清晰完整"
    ],
    "reasoning_process": "详细的风险分析推理过程，展示从数据到风险结论的逻辑链条",
    "overall_risk_level": 0.8,
    "conviction_level": "high"
}}
```

## 分析原则

1. **风险导向**: 重点识别和评估各类风险因素
2. **证据支撑**: 所有风险判断必须有具体数据支撑
3. **逻辑严密**: 确保风险分析逻辑清晰完整
4. **专业准确**: 符合期货市场风险管理标准
5. **辩论准备**: 为与看涨研究员的辩论做好充分准备
6. **客观理性**: 避免过度悲观，保持专业客观

请开始你的专业看跌风险分析。
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
                    "content": "你是一位专业的期货看跌研究员，拥有丰富的空头风险分析经验。请基于提供的数据进行专业的风险分析。"
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
    
    def _fix_json_content(self, content: str) -> str:
        """修复常见的JSON格式错误"""
        import re
        
        # 移除多余的逗号
        content = re.sub(r',\s*}', '}', content)
        content = re.sub(r',\s*]', ']', content)
        
        # 修复未闭合的字符串（简单处理）
        # 查找未闭合的引号
        quote_count = content.count('"') - content.count('\\"')  # 减去转义的引号
        if quote_count % 2 != 0:
            # 如果引号数量为奇数，可能有未闭合的字符串，在末尾添加引号
            content = content.rstrip() + '"'
        
        # 确保JSON对象正确闭合
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces > close_braces:
            content += '}' * (open_braces - close_braces)
        
        open_brackets = content.count('[')
        close_brackets = content.count(']')
        if open_brackets > close_brackets:
            content += ']' * (open_brackets - close_brackets)
        
        return content
    
    def _extract_info_from_text(self, content: str) -> dict:
        """从文本中提取分析信息（当JSON解析失败时使用）"""
        import re
        
        # 基础分析数据结构
        analysis_data = {
            "bearish_factors": [],
            "risk_catalysts": [],
            "key_arguments": ["基于文本分析提取的信息"],
            "overall_risk_level": 0.5,
            "conviction_level": "medium",
            "reasoning_process": content[:500] + "..." if len(content) > 500 else content
        }
        
        # 尝试提取看跌因素
        bearish_patterns = [
            r'看跌.*?因素[:：](.+?)(?=\n|$)',
            r'风险.*?因子[:：](.+?)(?=\n|$)',
            r'负面.*?影响[:：](.+?)(?=\n|$)'
        ]
        
        for pattern in bearish_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                factor_text = match.strip()
                if factor_text and len(factor_text) > 10:
                    analysis_data["bearish_factors"].append({
                        "factor_name": factor_text[:50] + "..." if len(factor_text) > 50 else factor_text,
                        "evidence": factor_text,
                        "severity": 5.0,
                        "module_source": "text_extraction",
                        "confidence": 0.6
                    })
        
        # 如果没有提取到有效因素，添加一个通用的
        if not analysis_data["bearish_factors"]:
            analysis_data["bearish_factors"].append({
                "factor_name": "API响应解析问题",
                "evidence": "无法正确解析API返回的分析结果",
                "severity": 3.0,
                "module_source": "error_fallback",
                "confidence": 0.3
            })
        
        return analysis_data
    
    def _parse_analysis_response(self, response: Dict, state: FuturesAnalysisState) -> BearishAnalysisResult:
        """解析分析响应结果"""
        
        try:
            content = response.get("content", "")
            analysis_data = None
            
            # 尝试提取JSON部分
            json_start = content.find("```json")
            json_end = content.find("```", json_start + 7)
            
            if json_start != -1 and json_end != -1:
                json_content = content[json_start + 7:json_end].strip()
                try:
                    analysis_data = json.loads(json_content)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"JSON块解析失败: {e}")
                    # 尝试修复常见的JSON错误
                    json_content = self._fix_json_content(json_content)
                    try:
                        analysis_data = json.loads(json_content)
                    except json.JSONDecodeError:
                        analysis_data = None
            
            # 如果JSON块解析失败，尝试直接解析整个内容
            if analysis_data is None:
                try:
                    analysis_data = json.loads(content)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"完整内容JSON解析失败: {e}")
                    # 尝试修复并再次解析
                    fixed_content = self._fix_json_content(content)
                    try:
                        analysis_data = json.loads(fixed_content)
                    except json.JSONDecodeError:
                        # 如果所有解析都失败，使用文本分析提取信息
                        analysis_data = self._extract_info_from_text(content)
            
            if not analysis_data:
                raise Exception("无法解析API响应内容")
            
            # 解析看跌因素
            bearish_factors = []
            for factor_data in analysis_data.get("bearish_factors", []):
                factor = BearishFactor(
                    factor_name=factor_data.get("factor_name", ""),
                    evidence=factor_data.get("evidence", ""),
                    severity=factor_data.get("severity", 5.0),
                    module_source=factor_data.get("module_source", "unknown"),
                    confidence=factor_data.get("confidence", 0.5),
                    risk_probability=factor_data.get("risk_probability", 0.5),
                    supporting_data=factor_data.get("supporting_data", {})
                )
                bearish_factors.append(factor)
            
            # 解析风险催化剂
            risk_catalysts = []
            for catalyst_data in analysis_data.get("risk_catalysts", []):
                catalyst = RiskCatalyst(
                    catalyst_name=catalyst_data.get("catalyst_name", ""),
                    trigger_probability=catalyst_data.get("trigger_probability", 0.5),
                    impact_severity=catalyst_data.get("impact_severity", "medium"),
                    timeline=catalyst_data.get("timeline", "medium_term"),
                    description=catalyst_data.get("description", ""),
                    mitigation_difficulty=catalyst_data.get("mitigation_difficulty", "moderate")
                )
                risk_catalysts.append(catalyst)
            
            # 构建结果对象
            result = BearishAnalysisResult(
                commodity=state.commodity,
                analysis_date=state.analysis_date,
                bearish_factors=bearish_factors,
                risk_catalysts=risk_catalysts,
                downside_targets=analysis_data.get("downside_targets", {}),
                risk_scenarios=analysis_data.get("risk_scenarios", []),
                key_arguments=analysis_data.get("key_arguments", []),
                overall_risk_level=analysis_data.get("overall_risk_level", 0.5),
                conviction_level=analysis_data.get("conviction_level", "medium"),
                reasoning_process=analysis_data.get("reasoning_process", ""),
                analysis_timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"解析分析响应失败: {e}")
            
            # 返回默认结果
            return BearishAnalysisResult(
                commodity=state.commodity,
                analysis_date=state.analysis_date,
                bearish_factors=[],
                risk_catalysts=[],
                key_arguments=["分析解析失败，请检查API响应格式"],
                overall_risk_level=0.5,
                conviction_level="low",
                analysis_timestamp=datetime.now().isoformat()
            )
    
    def _prepare_debate_points(self, result: BearishAnalysisResult, state: FuturesAnalysisState) -> Dict:
        """准备辩论要点"""
        
        # 按严重程度排序看跌因素
        sorted_factors = sorted(result.bearish_factors, key=lambda x: x.severity * x.confidence, reverse=True)
        
        # 准备主要论点
        main_arguments = []
        for factor in sorted_factors[:3]:  # 取前3个最严重的风险
            main_arguments.append({
                "argument": factor.factor_name,
                "evidence": factor.evidence,
                "severity": factor.severity,
                "probability": factor.risk_probability,
                "source": factor.module_source
            })
        
        # 准备反驳多头的论点
        counter_bull_points = [
            "供应压力将逐步显现并压制价格",
            "技术面显示明显的下跌风险信号",
            "资金面出现撤离迹象值得警惕",
            "宏观环境和政策风险不容忽视",
            "当前估值水平存在明显高估风险"
        ]
        
        # 准备风险证据支撑
        risk_evidence = {
            "high_risk_factors": len([f for f in result.bearish_factors if f.severity > 7]),
            "immediate_risks": len([c for c in result.risk_catalysts if c.timeline == "immediate"]),
            "risk_indicators": [
                f"整体风险水平: {result.overall_risk_level:.1%}",
                f"看跌因素数量: {len(result.bearish_factors)}",
                f"风险催化剂数量: {len(result.risk_catalysts)}"
            ]
        }
        
        debate_points = {
            "main_arguments": main_arguments,
            "counter_bull_points": counter_bull_points,
            "risk_evidence": risk_evidence,
            "key_talking_points": result.key_arguments,
            "risk_scenarios": result.risk_scenarios,
            "confidence_level": result.overall_risk_level
        }
        
        return debate_points
    
    def _calculate_bearish_scores(self, result: BearishAnalysisResult, state: FuturesAnalysisState) -> BearishAnalysisResult:
        """计算综合看跌评分"""
        
        # 计算风险因素分数
        factor_score = 0
        if result.bearish_factors:
            factor_score = sum(f.severity * f.confidence * f.risk_probability for f in result.bearish_factors) / len(result.bearish_factors)
        
        # 计算催化剂分数
        catalyst_score = 0
        if result.risk_catalysts:
            severity_weights = {"low": 1, "medium": 2, "high": 3}
            catalyst_score = sum(
                c.trigger_probability * severity_weights.get(c.impact_severity, 1) 
                for c in result.risk_catalysts
            ) / len(result.risk_catalysts)
        
        # 计算跨模块风险一致性分数
        risk_consistency_score = 0
        if state.cross_relationships:
            # 风险一致性：关联度高但逻辑不一致可能暗示风险
            risk_signals = sum(
                r.correlation_strength * (1 if not r.logical_consistency else 0.5)
                for r in state.cross_relationships
            ) / len(state.cross_relationships)
            risk_consistency_score = risk_signals
        
        # 综合评分 (0-100)
        bearish_score = (
            factor_score * 0.4 +  # 看跌因素权重40%
            catalyst_score * 0.3 +  # 催化剂权重30%
            risk_consistency_score * 10 * 0.2 +  # 风险一致性权重20%
            result.overall_risk_level * 10 * 0.1  # 整体风险权重10%
        ) * 10  # 转换为0-100分
        
        # 应用信心偏差（看跌研究员倾向于发现更多风险）
        bearish_score = min(100, bearish_score + self.confidence_bias * 100)
        
        # 更新结果
        result.bearish_score = bearish_score
        
        # 根据分数确定信念水平
        if bearish_score >= 80:
            result.conviction_level = "high"
        elif bearish_score >= 60:
            result.conviction_level = "medium"
        else:
            result.conviction_level = "low"
        
        return result
    
    def get_researcher_info(self) -> Dict:
        """获取研究员信息"""
        return {
            "name": "期货看跌研究员",
            "stance": self.stance.value,
            "expertise_areas": self.expertise_areas,
            "confidence_bias": self.confidence_bias,
            "version": "1.0.0"
        }

# ============================================================================
# 3. 测试和演示代码
# ============================================================================

async def test_bear_researcher():
    """测试看跌研究员"""
    
    print("🐻 测试期货看跌研究员...")
    
    # 加载配置
    from 期货TradingAgents系统_基础架构 import FuturesTradingAgentsConfig
    config = FuturesTradingAgentsConfig().to_dict()
    
    # 创建看跌研究员
    bear_researcher = FuturesBearResearcher(config)
    
    print(f"研究员信息: {bear_researcher.get_researcher_info()}")
    
    # 创建模拟的分析状态
    from 期货TradingAgents系统_基础架构 import FuturesAnalysisState, ModuleAnalysisResult
    
    # 模拟库存分析结果（偏空）
    inventory_result = ModuleAnalysisResult(
        module_name="inventory",
        commodity="RB",
        analysis_date="2025-01-19",
        status=AnalysisStatus.COMPLETED,
        result_data={
            "库存水平": "偏高",
            "库存趋势": "上升", 
            "仓单变化": "大幅增加",
            "供需平衡": "供应过剩"
        },
        confidence_score=0.8
    )
    
    # 模拟技术分析结果（偏空）
    technical_result = ModuleAnalysisResult(
        module_name="technical",
        commodity="RB",
        analysis_date="2025-01-19",
        status=AnalysisStatus.COMPLETED,
        result_data={
            "趋势方向": "下跌",
            "技术指标": "疲弱",
            "支撑破位": "关键支撑失守",
            "动量": "衰减"
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
            print("\n🔍 开始看跌风险分析...")
            bearish_result = await bear_researcher.analyze_bearish_perspective(analysis_state)
            
            print(f"✅ 看跌分析完成")
            print(f"   风险评分: {bearish_result.bearish_score:.1f}")
            print(f"   信念水平: {bearish_result.conviction_level}")
            print(f"   看跌因素数量: {len(bearish_result.bearish_factors)}")
            print(f"   风险催化剂数量: {len(bearish_result.risk_catalysts)}")
            
            # 保存结果
            result_file = Path("test_bear_analysis_result.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(bearish_result), f, ensure_ascii=False, indent=2, default=str)
            
            print(f"   结果已保存到: {result_file}")
        else:
            print("⚠️  未配置DeepSeek API密钥，跳过实际分析测试")
            print("   请在配置文件中设置api_settings.deepseek.api_key")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n✅ 看跌研究员测试完成")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_bear_researcher())
