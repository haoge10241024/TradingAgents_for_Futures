#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
期货Trading Agents系统 - 研究经理模块
负责协调看涨和看跌研究员的辩论，形成最终研究共识

功能特点：
1. 主持多空辩论流程
2. 评估论点质量和说服力
3. 管理辩论轮次和时间
4. 形成平衡的研究共识
5. 质量控制和标准制定

作者: AI Assistant
版本: 1.0.0
创建时间: 2025-01-19
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

# 导入基础架构和研究员
from 期货TradingAgents系统_基础架构 import (
    FuturesAnalysisState, 
    ModuleAnalysisResult,
    CrossModuleRelationship,
    AnalysisStatus,
    DebateStance
)
from 期货TradingAgents系统_看涨研究员 import (
    FuturesBullResearcher,
    BullishAnalysisResult
)
from 期货TradingAgents系统_看跌研究员 import (
    FuturesBearResearcher, 
    BearishAnalysisResult
)
from 期货TradingAgents系统_工具模块 import (
    DeepSeekAPIClient,
    DataValidator,
    TimeUtils,
    log_execution_time,
    retry_on_failure
)

# ============================================================================
# 1. 研究经理核心数据结构
# ============================================================================

class DebateRoundStatus(Enum):
    """辩论轮次状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ArgumentEvaluation:
    """论点评估"""
    argument: str
    logical_score: float  # 逻辑性评分 (0-10)
    evidence_quality: float  # 证据质量评分 (0-10)
    persuasiveness: float  # 说服力评分 (0-10)
    professional_accuracy: float  # 专业准确性评分 (0-10)
    overall_score: float  # 综合评分 (0-10)
    strengths: List[str] = None  # 优势
    weaknesses: List[str] = None  # 弱点

@dataclass
class DebateRoundResult:
    """单轮辩论结果"""
    round_number: int
    status: DebateRoundStatus
    
    # 双方论点评估
    bull_arguments: List[ArgumentEvaluation] = None
    bear_arguments: List[ArgumentEvaluation] = None
    
    # 轮次分析
    round_winner: str = "tie"  # "bull", "bear", "tie"
    key_insights: List[str] = None
    core_disagreements: List[Dict] = None
    evidence_gaps: List[str] = None
    
    # 质量评估
    debate_quality_score: float = 0.0
    argument_depth: str = "medium"  # "shallow", "medium", "deep"
    
    # 时间信息
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0.0

@dataclass
class ResearchConsensus:
    """研究共识"""
    commodity: str
    analysis_date: str
    consensus_type: str  # "bullish", "bearish", "neutral", "mixed"
    
    # 共识内容
    key_findings: List[str] = None
    agreed_points: List[str] = None
    unresolved_issues: List[str] = None
    
    # 投资建议
    investment_recommendation: str = ""
    confidence_level: float = 0.0
    risk_assessment: str = ""
    
    # 权重分配
    bull_weight: float = 0.5
    bear_weight: float = 0.5
    
    # 支撑数据
    supporting_evidence: Dict = None
    dissenting_views: List[str] = None
    
    # 元数据
    consensus_timestamp: str = ""
    research_quality: str = "medium"  # "low", "medium", "high"

@dataclass
class DebateManagementResult:
    """辩论管理结果"""
    commodity: str
    analysis_date: str
    
    # 辩论过程
    debate_rounds: List[DebateRoundResult] = None
    total_rounds: int = 0
    
    # 最终共识
    final_consensus: ResearchConsensus = None
    
    # 整体评估
    overall_debate_quality: float = 0.0
    research_completeness: float = 0.0
    
    # 时间统计
    total_duration_seconds: float = 0.0
    average_round_duration: float = 0.0
    
    # 元数据
    management_timestamp: str = ""

# ============================================================================
# 2. 研究经理主类
# ============================================================================

class FuturesResearchManager:
    """期货研究经理 - 主持多空辩论，形成研究共识"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.role = "research_manager"
        
        # API配置
        self.deepseek_config = config.get("api_settings", {}).get("deepseek", {})
        self.api_key = self.deepseek_config.get("api_key", "")
        
        # 辩论配置
        self.debate_config = config.get("debate_settings", {})
        self.max_debate_rounds = self.debate_config.get("max_debate_rounds", 2)
        self.debate_timeout = self.debate_config.get("debate_timeout_seconds", 300)
        self.use_reasoning_mode = self.debate_config.get("enable_reasoning_mode", True)
        
        # 评估标准
        self.evaluation_criteria = config.get("researcher_agents", {}).get("research_manager", {}).get("evaluation_criteria", [
            "论点逻辑性", "证据充分性", "专业准确性", "风险收益平衡"
        ])
        
        # 日志
        self.logger = logging.getLogger("FuturesResearchManager")
        
        # 期货品种映射
        self.commodity_names = {
            "RB": "螺纹钢", "HC": "热卷", "I": "铁矿石", "J": "焦炭", "JM": "焦煤",
            "CU": "沪铜", "AL": "沪铝", "ZN": "沪锌", "NI": "沪镍", "AU": "黄金", "AG": "白银",
            "RU": "橡胶", "BU": "沥青", "FU": "燃油", "MA": "甲醇", "TA": "PTA",
            "SR": "白糖", "CF": "棉花", "M": "豆粕", "Y": "豆油", "P": "棕榈油"
        }
    
    @log_execution_time()
    async def manage_research_debate(self, analysis_state: FuturesAnalysisState, 
                                   bull_result: BullishAnalysisResult, 
                                   bear_result: BearishAnalysisResult) -> DebateManagementResult:
        """管理研究员辩论流程"""
        
        self.logger.info(f"开始管理研究辩论: {analysis_state.commodity} ({analysis_state.analysis_date})")
        
        start_time = datetime.now()
        
        # 初始化辩论管理结果
        management_result = DebateManagementResult(
            commodity=analysis_state.commodity,
            analysis_date=analysis_state.analysis_date,
            debate_rounds=[],
            management_timestamp=start_time.isoformat()
        )
        
        try:
            # 1. 预辩论评估
            initial_assessment = await self._conduct_initial_assessment(
                analysis_state, bull_result, bear_result
            )
            
            # 2. 执行辩论轮次
            for round_num in range(1, self.max_debate_rounds + 1):
                self.logger.info(f"开始第 {round_num} 轮辩论...")
                
                round_result = await self._conduct_debate_round(
                    round_num, analysis_state, bull_result, bear_result, 
                    management_result.debate_rounds
                )
                
                management_result.debate_rounds.append(round_result)
                
                # 检查是否需要继续辩论
                if self._should_end_debate(round_result, round_num):
                    self.logger.info(f"辩论在第 {round_num} 轮后结束")
                    break
            
            # 3. 形成最终研究共识
            management_result.final_consensus = await self._form_research_consensus(
                analysis_state, bull_result, bear_result, management_result.debate_rounds
            )
            
            # 4. 计算整体评估指标
            management_result = self._calculate_overall_metrics(management_result, start_time)
            
            self.logger.info(f"辩论管理完成，共识类型: {management_result.final_consensus.consensus_type}")
            
            return management_result
            
        except Exception as e:
            self.logger.error(f"辩论管理失败: {e}")
            
            # 返回失败结果
            management_result.final_consensus = ResearchConsensus(
                commodity=analysis_state.commodity,
                analysis_date=analysis_state.analysis_date,
                consensus_type="failed",
                investment_recommendation="由于辩论管理失败，建议谨慎投资",
                confidence_level=0.3,
                consensus_timestamp=datetime.now().isoformat()
            )
            
            return management_result
    
    async def _conduct_initial_assessment(self, state: FuturesAnalysisState,
                                        bull_result: BullishAnalysisResult,
                                        bear_result: BearishAnalysisResult) -> Dict:
        """进行预辩论评估"""
        
        assessment_prompt = self._build_initial_assessment_prompt(state, bull_result, bear_result)
        
        if self.use_reasoning_mode:
            response = await self._call_deepseek_reasoning(assessment_prompt)
        else:
            response = await self._call_deepseek_chat(assessment_prompt, "初始评估")
        
        try:
            content = response.get("content", "")
            
            # 尝试提取JSON部分
            json_start = content.find("```json")
            json_end = content.find("```", json_start + 7)
            
            if json_start != -1 and json_end != -1:
                json_content = content[json_start + 7:json_end].strip()
                return json.loads(json_content)
            else:
                return {"assessment": "初始评估解析失败"}
                
        except Exception as e:
            self.logger.error(f"初始评估解析失败: {e}")
            return {"assessment": "初始评估失败"}
    
    def _build_initial_assessment_prompt(self, state: FuturesAnalysisState,
                                       bull_result: BullishAnalysisResult,
                                       bear_result: BearishAnalysisResult) -> str:
        """构建初始评估Prompt"""
        
        commodity_name = self.commodity_names.get(state.commodity, state.commodity)
        
        prompt = f"""
你是一位资深的期货研究经理，负责评估看涨和看跌研究员的分析质量，并为即将开始的辩论做准备。

## 基础信息
**品种**: {commodity_name} ({state.commodity})
**分析日期**: {state.analysis_date}

## 看涨研究员分析结果
**综合评分**: {bull_result.bullish_score:.1f}/100
**信念水平**: {bull_result.conviction_level}
**核心论点**: {bull_result.key_arguments}
**看涨因素数量**: {len(bull_result.bullish_factors)}

## 看跌研究员分析结果  
**风险评分**: {bear_result.bearish_score:.1f}/100
**信念水平**: {bear_result.conviction_level}
**核心论点**: {bear_result.key_arguments}
**风险因素数量**: {len(bear_result.bearish_factors)}

## 评估要求

请从研究经理的角度进行初始评估：

1. **双方论点强度对比**
2. **证据质量评估**
3. **潜在分歧点识别**
4. **辩论重点建议**
5. **质量控制建议**

请按JSON格式输出评估结果：

```json
{{
    "bull_strength_assessment": {{
        "logic_score": 8.0,
        "evidence_score": 7.5,
        "persuasiveness": 8.2,
        "main_strengths": ["优势1", "优势2"],
        "main_weaknesses": ["弱点1", "弱点2"]
    }},
    "bear_strength_assessment": {{
        "logic_score": 7.8,
        "evidence_score": 8.0,
        "persuasiveness": 7.5,
        "main_strengths": ["优势1", "优势2"],
        "main_weaknesses": ["弱点1", "弱点2"]
    }},
    "key_disagreement_areas": [
        "分歧点1", "分歧点2", "分歧点3"
    ],
    "debate_focus_suggestions": [
        "建议重点1", "建议重点2"
    ],
    "initial_bias_assessment": "neutral",
    "debate_difficulty_level": "medium"
}}
```
"""
        
        return prompt
    
    async def _conduct_debate_round(self, round_num: int, state: FuturesAnalysisState,
                                  bull_result: BullishAnalysisResult, 
                                  bear_result: BearishAnalysisResult,
                                  previous_rounds: List[DebateRoundResult]) -> DebateRoundResult:
        """执行单轮辩论"""
        
        round_start = datetime.now()
        
        # 构建辩论主持Prompt
        debate_prompt = self._build_debate_moderation_prompt(
            round_num, state, bull_result, bear_result, previous_rounds
        )
        
        # 调用DeepSeek进行辩论主持
        if self.use_reasoning_mode:
            debate_response = await self._call_deepseek_reasoning(debate_prompt)
        else:
            debate_response = await self._call_deepseek_chat(debate_prompt, f"第{round_num}轮辩论")
        
        # 解析辩论结果
        round_result = self._parse_debate_round_result(debate_response, round_num, round_start)
        
        return round_result
    
    def _build_debate_moderation_prompt(self, round_num: int, state: FuturesAnalysisState,
                                      bull_result: BullishAnalysisResult,
                                      bear_result: BearishAnalysisResult,
                                      previous_rounds: List[DebateRoundResult]) -> str:
        """构建辩论主持Prompt"""
        
        commodity_name = self.commodity_names.get(state.commodity, state.commodity)
        
        # 构建历史辩论信息
        history_info = ""
        if previous_rounds:
            history_info = "## 前轮辩论总结\n"
            for prev_round in previous_rounds:
                history_info += f"**第{prev_round.round_number}轮**: 胜方={prev_round.round_winner}, "
                history_info += f"质量={prev_round.debate_quality_score:.1f}\n"
                if prev_round.key_insights:
                    history_info += f"关键洞察: {', '.join(prev_round.key_insights)}\n"
        
        prompt = f"""
你是一位资深的期货研究经理，正在主持{commodity_name}({state.commodity})的第{round_num}轮投资辩论。
你需要客观评估看涨和看跌研究员的论点，促进深度讨论，并识别关键分歧点。

{history_info}

## 看涨研究员观点摘要
- **综合评分**: {bull_result.bullish_score:.1f}/100
- **信念水平**: {bull_result.conviction_level}
- **核心论点**: {bull_result.key_arguments[:3] if bull_result.key_arguments else []}
- **主要看涨因素**: {[f.factor_name for f in bull_result.bullish_factors[:3]] if bull_result.bullish_factors else []}

## 看跌研究员观点摘要
- **风险评分**: {bear_result.bearish_score:.1f}/100  
- **信念水平**: {bear_result.conviction_level}
- **核心论点**: {bear_result.key_arguments[:3] if bear_result.key_arguments else []}
- **主要风险因素**: {[f.factor_name for f in bear_result.bearish_factors[:3]] if bear_result.bearish_factors else []}

## 主持要求

作为研究经理，请主持本轮辩论：

### 🎯 评估论点质量
1. **逻辑严密性**: 双方论证是否逻辑清晰？
2. **证据充分性**: 是否有足够数据支撑？
3. **专业准确性**: 分析是否符合期货市场规律？
4. **说服力**: 论点是否具有说服力？

### ⚖️ 平衡双方观点
1. **优势识别**: 各自最强的论点是什么？
2. **弱点暴露**: 各自论证的薄弱环节？
3. **证据对比**: 哪些证据更有说服力？

### 🔍 深度挖掘分歧
1. **核心分歧**: 双方最根本的分歧在哪里？
2. **数据解读**: 对同一数据的不同解读？
3. **假设差异**: 基础假设有何不同？

### 📊 综合评估
1. **整体说服力**: 综合考虑哪方更有说服力？
2. **风险收益**: 如何平衡风险和收益？
3. **投资时机**: 当前时点的最佳策略？

## 输出格式

请按以下JSON格式输出辩论主持结果：

```json
{{
    "bull_arguments_evaluation": [
        {{
            "argument": "具体论点",
            "logical_score": 8.5,
            "evidence_quality": 7.0,
            "persuasiveness": 8.0,
            "professional_accuracy": 9.0,
            "overall_score": 8.1,
            "strengths": ["优势1", "优势2"],
            "weaknesses": ["弱点1"]
        }}
    ],
    "bear_arguments_evaluation": [
        {{
            "argument": "具体论点",
            "logical_score": 7.5,
            "evidence_quality": 8.5,
            "persuasiveness": 7.0,
            "professional_accuracy": 8.0,
            "overall_score": 7.8,
            "strengths": ["优势1", "优势2"],
            "weaknesses": ["弱点1"]
        }}
    ],
    "key_insights": [
        "关键洞察1",
        "关键洞察2"
    ],
    "core_disagreements": [
        {{
            "issue": "分歧点",
            "bull_view": "看涨观点",
            "bear_view": "看跌观点",
            "resolution_difficulty": 8
        }}
    ],
    "evidence_gaps": [
        "需要补充的证据1",
        "需要补充的证据2"
    ],
    "round_assessment": {{
        "round_winner": "bull",
        "debate_quality_score": 8.2,
        "argument_depth": "deep",
        "bull_performance": 8.1,
        "bear_performance": 7.8
    }},
    "research_direction": {{
        "emerging_consensus": "新兴共识或分歧加深",
        "remaining_uncertainties": ["不确定因素1", "不确定因素2"],
        "additional_research_needed": ["需要补充的研究1"]
    }}
}}
```

请确保评估公正客观，促进建设性讨论。
"""
        
        return prompt
    
    def _parse_debate_round_result(self, response: Dict, round_num: int, 
                                 round_start: datetime) -> DebateRoundResult:
        """解析辩论轮次结果"""
        
        round_end = datetime.now()
        duration = (round_end - round_start).total_seconds()
        
        try:
            content = response.get("content", "")
            
            # 尝试提取JSON部分
            json_start = content.find("```json")
            json_end = content.find("```", json_start + 7)
            
            if json_start != -1 and json_end != -1:
                json_content = content[json_start + 7:json_end].strip()
                debate_data = json.loads(json_content)
            else:
                debate_data = json.loads(content)
            
            # 解析看涨论点评估
            bull_arguments = []
            for arg_data in debate_data.get("bull_arguments_evaluation", []):
                arg_eval = ArgumentEvaluation(
                    argument=arg_data.get("argument", ""),
                    logical_score=arg_data.get("logical_score", 5.0),
                    evidence_quality=arg_data.get("evidence_quality", 5.0),
                    persuasiveness=arg_data.get("persuasiveness", 5.0),
                    professional_accuracy=arg_data.get("professional_accuracy", 5.0),
                    overall_score=arg_data.get("overall_score", 5.0),
                    strengths=arg_data.get("strengths", []),
                    weaknesses=arg_data.get("weaknesses", [])
                )
                bull_arguments.append(arg_eval)
            
            # 解析看跌论点评估
            bear_arguments = []
            for arg_data in debate_data.get("bear_arguments_evaluation", []):
                arg_eval = ArgumentEvaluation(
                    argument=arg_data.get("argument", ""),
                    logical_score=arg_data.get("logical_score", 5.0),
                    evidence_quality=arg_data.get("evidence_quality", 5.0),
                    persuasiveness=arg_data.get("persuasiveness", 5.0),
                    professional_accuracy=arg_data.get("professional_accuracy", 5.0),
                    overall_score=arg_data.get("overall_score", 5.0),
                    strengths=arg_data.get("strengths", []),
                    weaknesses=arg_data.get("weaknesses", [])
                )
                bear_arguments.append(arg_eval)
            
            # 构建轮次结果
            round_result = DebateRoundResult(
                round_number=round_num,
                status=DebateRoundStatus.COMPLETED,
                bull_arguments=bull_arguments,
                bear_arguments=bear_arguments,
                round_winner=debate_data.get("round_assessment", {}).get("round_winner", "tie"),
                key_insights=debate_data.get("key_insights", []),
                core_disagreements=debate_data.get("core_disagreements", []),
                evidence_gaps=debate_data.get("evidence_gaps", []),
                debate_quality_score=debate_data.get("round_assessment", {}).get("debate_quality_score", 5.0),
                argument_depth=debate_data.get("round_assessment", {}).get("argument_depth", "medium"),
                start_time=round_start.isoformat(),
                end_time=round_end.isoformat(),
                duration_seconds=duration
            )
            
            return round_result
            
        except Exception as e:
            self.logger.error(f"解析第{round_num}轮辩论结果失败: {e}")
            
            # 返回默认结果
            return DebateRoundResult(
                round_number=round_num,
                status=DebateRoundStatus.FAILED,
                round_winner="tie",
                key_insights=["辩论解析失败"],
                debate_quality_score=3.0,
                start_time=round_start.isoformat(),
                end_time=round_end.isoformat(),
                duration_seconds=duration
            )
    
    def _should_end_debate(self, round_result: DebateRoundResult, round_num: int) -> bool:
        """判断是否应该结束辩论"""
        
        # 如果辩论质量太低，提前结束
        if round_result.debate_quality_score < 4.0:
            self.logger.warning(f"第{round_num}轮辩论质量过低({round_result.debate_quality_score:.1f})，提前结束")
            return True
        
        # 如果一方明显胜出且质量很高，可以提前结束
        if round_result.round_winner != "tie" and round_result.debate_quality_score > 8.0:
            self.logger.info(f"第{round_num}轮有明确胜方且质量很高，考虑提前结束")
            # 但不是强制结束，让系统继续完成预定轮次
        
        # 达到最大轮次时结束
        if round_num >= self.max_debate_rounds:
            return True
        
        return False
    
    async def _form_research_consensus(self, state: FuturesAnalysisState,
                                     bull_result: BullishAnalysisResult,
                                     bear_result: BearishAnalysisResult,
                                     debate_rounds: List[DebateRoundResult]) -> ResearchConsensus:
        """形成最终研究共识"""
        
        consensus_prompt = self._build_consensus_formation_prompt(
            state, bull_result, bear_result, debate_rounds
        )
        
        if self.use_reasoning_mode:
            response = await self._call_deepseek_reasoning(consensus_prompt)
        else:
            response = await self._call_deepseek_chat(consensus_prompt, "形成共识")
        
        return self._parse_consensus_result(response, state)
    
    def _build_consensus_formation_prompt(self, state: FuturesAnalysisState,
                                        bull_result: BullishAnalysisResult,
                                        bear_result: BearishAnalysisResult,
                                        debate_rounds: List[DebateRoundResult]) -> str:
        """构建共识形成Prompt"""
        
        commodity_name = self.commodity_names.get(state.commodity, state.commodity)
        
        # 汇总辩论结果
        debate_summary = ""
        for round_result in debate_rounds:
            debate_summary += f"**第{round_result.round_number}轮**: 胜方={round_result.round_winner}, "
            debate_summary += f"质量={round_result.debate_quality_score:.1f}\n"
            if round_result.key_insights:
                debate_summary += f"关键洞察: {', '.join(round_result.key_insights)}\n"
        
        prompt = f"""
你是一位资深的期货研究经理，需要基于看涨和看跌研究员的分析以及辩论过程，形成最终的研究共识。

## 基础信息
**品种**: {commodity_name} ({state.commodity})
**分析日期**: {state.analysis_date}

## 研究员分析摘要
### 看涨研究员
- 综合评分: {bull_result.bullish_score:.1f}/100
- 信念水平: {bull_result.conviction_level}
- 核心论点数: {len(bull_result.key_arguments)}

### 看跌研究员  
- 风险评分: {bear_result.bearish_score:.1f}/100
- 信念水平: {bear_result.conviction_level}
- 核心论点数: {len(bear_result.key_arguments)}

## 辩论过程总结
{debate_summary}

## 共识形成要求

请基于以上信息形成平衡的研究共识：

1. **综合评估双方观点的合理性**
2. **识别达成一致的关键点**
3. **明确仍存在分歧的领域**
4. **给出平衡的投资建议**
5. **评估整体研究质量**

请按JSON格式输出研究共识：

```json
{{
    "consensus_type": "bullish",
    "key_findings": [
        "关键发现1",
        "关键发现2",
        "关键发现3"
    ],
    "agreed_points": [
        "双方一致认同的观点1",
        "双方一致认同的观点2"
    ],
    "unresolved_issues": [
        "仍存分歧的问题1",
        "仍存分歧的问题2"
    ],
    "investment_recommendation": "详细的投资建议，包括方向、时机、风险控制",
    "confidence_level": 0.75,
    "risk_assessment": "风险评估描述",
    "bull_weight": 0.6,
    "bear_weight": 0.4,
    "supporting_evidence": {{
        "strongest_bull_points": ["最强看涨论点"],
        "strongest_bear_points": ["最强看跌论点"],
        "key_data_support": ["关键数据支撑"]
    }},
    "dissenting_views": [
        "少数派观点1",
        "少数派观点2"
    ],
    "research_quality": "high"
}}
```
"""
        
        return prompt
    
    def _parse_consensus_result(self, response: Dict, state: FuturesAnalysisState) -> ResearchConsensus:
        """解析共识形成结果"""
        
        try:
            content = response.get("content", "")
            
            # 尝试提取JSON部分
            json_start = content.find("```json")
            json_end = content.find("```", json_start + 7)
            
            if json_start != -1 and json_end != -1:
                json_content = content[json_start + 7:json_end].strip()
                consensus_data = json.loads(json_content)
            else:
                consensus_data = json.loads(content)
            
            # 构建共识对象
            consensus = ResearchConsensus(
                commodity=state.commodity,
                analysis_date=state.analysis_date,
                consensus_type=consensus_data.get("consensus_type", "neutral"),
                key_findings=consensus_data.get("key_findings", []),
                agreed_points=consensus_data.get("agreed_points", []),
                unresolved_issues=consensus_data.get("unresolved_issues", []),
                investment_recommendation=consensus_data.get("investment_recommendation", ""),
                confidence_level=consensus_data.get("confidence_level", 0.5),
                risk_assessment=consensus_data.get("risk_assessment", ""),
                bull_weight=consensus_data.get("bull_weight", 0.5),
                bear_weight=consensus_data.get("bear_weight", 0.5),
                supporting_evidence=consensus_data.get("supporting_evidence", {}),
                dissenting_views=consensus_data.get("dissenting_views", []),
                research_quality=consensus_data.get("research_quality", "medium"),
                consensus_timestamp=datetime.now().isoformat()
            )
            
            return consensus
            
        except Exception as e:
            self.logger.error(f"解析共识结果失败: {e}")
            
            # 返回默认共识
            return ResearchConsensus(
                commodity=state.commodity,
                analysis_date=state.analysis_date,
                consensus_type="neutral",
                key_findings=["共识解析失败，建议重新分析"],
                investment_recommendation="由于共识形成失败，建议保持观望",
                confidence_level=0.3,
                consensus_timestamp=datetime.now().isoformat()
            )
    
    def _calculate_overall_metrics(self, management_result: DebateManagementResult, 
                                 start_time: datetime) -> DebateManagementResult:
        """计算整体评估指标"""
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # 更新基本统计
        management_result.total_rounds = len(management_result.debate_rounds)
        management_result.total_duration_seconds = total_duration
        
        if management_result.total_rounds > 0:
            management_result.average_round_duration = sum(
                r.duration_seconds for r in management_result.debate_rounds
            ) / management_result.total_rounds
        
        # 计算整体辩论质量
        if management_result.debate_rounds:
            management_result.overall_debate_quality = sum(
                r.debate_quality_score for r in management_result.debate_rounds
            ) / len(management_result.debate_rounds)
        
        # 计算研究完整性
        completed_rounds = len([r for r in management_result.debate_rounds if r.status == DebateRoundStatus.COMPLETED])
        management_result.research_completeness = completed_rounds / max(1, self.max_debate_rounds)
        
        return management_result
    
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
    
    async def _call_deepseek_chat(self, prompt: str, task_name: str = "研究管理") -> Dict:
        """调用DeepSeek聊天模式"""
        
        async with DeepSeekAPIClient(self.api_key) as client:
            messages = [
                {
                    "role": "system", 
                    "content": "你是一位专业的期货研究经理，负责主持研究员辩论并形成投资共识。请保持客观公正，确保分析质量。"
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
    
    def get_manager_info(self) -> Dict:
        """获取研究经理信息"""
        return {
            "name": "期货研究经理",
            "role": self.role,
            "max_debate_rounds": self.max_debate_rounds,
            "evaluation_criteria": self.evaluation_criteria,
            "version": "1.0.0"
        }

# ============================================================================
# 3. 测试和演示代码
# ============================================================================

async def test_research_manager():
    """测试研究经理"""
    
    print("👔 测试期货研究经理...")
    
    # 加载配置
    from 期货TradingAgents系统_基础架构 import FuturesTradingAgentsConfig
    config = FuturesTradingAgentsConfig().to_dict()
    
    # 创建研究经理
    research_manager = FuturesResearchManager(config)
    
    print(f"研究经理信息: {research_manager.get_manager_info()}")
    
    # 创建模拟的研究员结果
    from 期货TradingAgents系统_基础架构 import FuturesAnalysisState, ModuleAnalysisResult
    from 期货TradingAgents系统_看涨研究员 import BullishAnalysisResult, BullishFactor
    from 期货TradingAgents系统_看跌研究员 import BearishAnalysisResult, BearishFactor
    
    # 模拟分析状态
    analysis_state = FuturesAnalysisState(
        commodity="RB",
        analysis_date="2025-01-19"
    )
    
    # 模拟看涨结果
    bull_result = BullishAnalysisResult(
        commodity="RB",
        analysis_date="2025-01-19",
        bullish_factors=[
            BullishFactor(
                factor_name="库存去化加速",
                evidence="库存环比下降15%",
                strength=8.5,
                module_source="inventory",
                confidence=0.8
            )
        ],
        key_arguments=["供需基本面改善", "技术面突破确认", "政策环境支持"],
        bullish_score=75.0,
        conviction_level="high",
        overall_confidence=0.8
    )
    
    # 模拟看跌结果
    bear_result = BearishAnalysisResult(
        commodity="RB",
        analysis_date="2025-01-19",
        bearish_factors=[
            BearishFactor(
                factor_name="需求预期下滑",
                evidence="下游开工率下降8%",
                severity=7.5,
                module_source="news",
                confidence=0.75,
                risk_probability=0.7
            )
        ],
        key_arguments=["需求疲弱担忧", "宏观环境不确定", "技术面存在调整风险"],
        bearish_score=65.0,
        conviction_level="medium",
        overall_risk_level=0.7
    )
    
    try:
        # 注意：这需要有效的DeepSeek API密钥
        if config.get("api_settings", {}).get("deepseek", {}).get("api_key"):
            print("\n🎯 开始管理研究辩论...")
            management_result = await research_manager.manage_research_debate(
                analysis_state, bull_result, bear_result
            )
            
            print(f"✅ 辩论管理完成")
            print(f"   总轮次: {management_result.total_rounds}")
            print(f"   共识类型: {management_result.final_consensus.consensus_type}")
            print(f"   信心水平: {management_result.final_consensus.confidence_level:.1%}")
            print(f"   整体质量: {management_result.overall_debate_quality:.1f}")
            
            # 保存结果
            result_file = Path("test_research_management_result.json")
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(management_result), f, ensure_ascii=False, indent=2, default=str)
            
            print(f"   结果已保存到: {result_file}")
        else:
            print("⚠️  未配置DeepSeek API密钥，跳过实际辩论测试")
            print("   请在配置文件中设置api_settings.deepseek.api_key")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n✅ 研究经理测试完成")

if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_research_manager())
