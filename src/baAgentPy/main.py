"""BA-Agent Python AI Service — hxPy entry point.

This module serves as the main interface for BA-Agent system,
loaded by hxPy containers in Haxall/FIN Framework environment.

Key Features:
- LLM-powered intent parsing using Gemini API
- Rule-based domain engines for FDD, energy optimization, inspection, HMI generation
- Natural language routing via AgentWorkflow
- Haystack Grid ↔ Pandas DataFrame conversion

Usage from AXON:
    session: py(image: "ba-agent-py:latest")
    pyExec(session, "from baAgentPy.main import BaAgentService; svc = BaAgentService()")
    pyEval(session, "svc.ask('诊断一下AHU-01')")
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from baAgentPy.core.agent_workflow import AgentWorkflow, ParsedInstruction
from baAgentPy.services import (
    EnergyOptEngine,
    FddEngine,
    HmiEngine,
    InspectEngine,
    ReportEngine,
    TaggingEngine,
)
from baAgentPy.utils.grid_converter import GridConverter


# ============================================================
# Configuration
# ============================================================

# Gemini API Configuration
# In production, API key will be injected via environment variable
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAz5LOHMBbFhkwzpomDcE50VvnQtimnAoE")

# Gemini 2.5 Flash API Endpoint
MODEL_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview:generateContent?key={API_KEY}"

# Retry configuration
MAX_RETRIES = 5
RETRY_DELAYS = [1, 2, 4, 8, 16]  # seconds
REQUEST_TIMEOUT = 30  # seconds

# System Prompt - integrates ba_agent_prompt_engineering.md rules
SYSTEM_PROMPT = """
你是一位资深的建筑自动化 (BA) 专家，精通 Project Haystack 4.0 语义模型和 FIN Framework 运维流程。

你的任务是解析用户的自然语言指令，并将其转化为结构化的任务 JSON。

## 可用工具与意图定义:
1. `ACTION_DIAGNOSIS`: 用于诊断故障、分析报警原因、查找运行异常的根因。
   - 关键词: 诊断、故障、报警、alarm、诊断、分析、排查
   - 示例: "诊断一下AHU-01"、"分析为什么12楼总是热"、"查看报警根因"

2. `ACTION_OPTIMIZE`: 用于能源优化、设定值调整、节能策略。
   - 关键词: 优化、节能、能耗、设定值、setpoint、optimize、energy
   - 示例: "优化12楼送风温度"、"调整空调参数"、"节能模式"

3. `ACTION_INSPECT`: 用于传感器巡检、健康检查、设备状态查询。
   - 关键词: 巡检、检查、传感器、health、inspect、状态、point
   - 示例: "检查所有温度传感器"、"巡检12楼设备"、"传感器健康评分"

4. `ACTION_HMI`: 用于生成、创建、布置 HMI 监控画面或图形界面。
   - 关键词: hmi、界面、画面、布局、图形、生成、layout
   - 示例: "生成AHU监控画面"、"创建楼层平面图"、"HMI布局"

5. `ACTION_REPORT`: 用于生成日报、运维总结、操作摘要。
   - 关键词: 报告、日报、总结、summary、brief、report
   - 示例: "生成今日运维报告"、"总结昨天的操作"、"日报"

6. `ACTION_QUERY`: 用于查询实时数据、历史趋势或设备状态。
   - 关键词: 查询、数据、趋势、历史、当前、实时、query
   - 示例: "查询AHU-01当前状态"、"最近1小时温度趋势"、"显示所有点位"

## 输出约束:
- 必须且仅能返回合法的 JSON 格式
- 严禁包含任何解释性文字、开场白或格式说明
- JSON 结构必须包含: "intent", "parameters", "thought_process"
- 优先匹配 Haystack 4.0 标签语义
- parameters 必须包含执行所需的具体参数

## 示例输出:

用户: "诊断一下AHU-01最近一直报警"
回复:
{
  "intent": "ACTION_DIAGNOSIS",
  "parameters": {"target_equip": "AHU-01", "time_range": "today"},
  "thought_process": "用户需要分析AHU-01设备的报警原因"
}

用户: "生成12楼的HMI监控画面"
回复:
{
  "intent": "ACTION_HMI",
  "parameters": {"floor": "12", "equip_types": ["AHU", "VAV"]},
  "thought_process": "用户请求生成12楼设备的监控界面布局"
}

用户: "优化节能模式，降低能耗"
回复:
{
  "intent": "ACTION_OPTIMIZE",
  "parameters": {"mode": "energy_save", "target": "building"},
  "thought_process": "用户希望启用节能优化策略"
}

用户: "查询所有温度传感器"
回复:
{
  "intent": "ACTION_QUERY",
  "parameters": {"point_type": "sensor", "metric": "temperature"},
  "thought_process": "用户需要查看温度类传感器的当前数据"
}
"""


# ============================================================
# Request/Response Models
# ============================================================

class ServiceRequest(BaseModel):
    """Incoming request from AXON via pyEval()."""

    action: str = Field(description="Service action: diagnose | optimize | inspect | hmi | report | query")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="Action-specific parameters"
    )


class ServiceResponse(BaseModel):
    """Response returned to AXON via pyEval() return value."""

    ok: bool = True
    action: str
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


# ============================================================
# LLM Integration Layer
# ============================================================

def call_gemini_api(user_query: str, context_info: dict[str, Any] | None = None) -> str:
    """
    Call Gemini 2.5 Flash API for intent parsing with exponential backoff retry.

    Args:
        user_query: Natural language text from user
        context_info: Optional context from Haystack (sites, equipment list, etc.)

    Returns:
        JSON string containing structured intent and parameters
    """
    if not API_KEY:
        return json.dumps({
            "error": "AI_SERVICE_NOT_CONFIGURED",
            "reply": "LLM服务未配置，请检查GEMINI_API_KEY环境变量。"
        }, ensure_ascii=False)

    # Build full instruction with context
    if context_info:
        context_str = json.dumps(context_info, ensure_ascii=False)
        full_instruction = f"{SYSTEM_PROMPT}\n\n## 当前上下文环境:\n{context_str}"
    else:
        full_instruction = SYSTEM_PROMPT

    payload = {
        "contents": [
            {
                "parts": [{"text": user_query}]
            }
        ],
        "systemInstruction": {
            "parts": [{"text": full_instruction}]
        },
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    # Exponential backoff retry logic
    last_error: str | None = None
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            response = _make_request(payload, delay)
            if response.status_code == 200:
                result = response.json()
                # Extract AI returned text content
                content = result.get('candidates', [{}])[0].get('content', {})
                parts = content.get('parts', [])
                if parts and len(parts) > 0:
                    text = parts[0].get('text', "")
                    # Remove markdown code blocks if present
                    if text.startswith('```json'):
                        text = text[7:]
                    if text.endswith('```'):
                        text = text[:-3]
                    return text.strip()  # type: ignore[no-any-return]
                return '{"error": "AI_RESPONSE_FORMAT_ERROR"}'
            else:
                last_error = f"HTTP {response.status_code}"
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(delay)

    # All retries failed
    return json.dumps({
        "error": "AI_SERVICE_UNAVAILABLE",
        "reply": f"AI服务暂时无法连接({last_error})，请稍后再试。系统将使用规则引擎作为备用。"
    }, ensure_ascii=False)


def _make_request(payload: dict[str, Any], delay: float) -> Any:
    """Make a single API request with delay."""
    time.sleep(delay)
    import requests
    return requests.post(
        MODEL_ENDPOINT,
        json=payload,
        timeout=REQUEST_TIMEOUT,
        headers={"Content-Type": "application/json"}
    )


def parse_with_llm(user_text: str, context_json: str = "{}") -> ParsedInstruction:
    """
    Parse user instruction using LLM (Gemini).

    This replaces keyword-based parsing in AgentWorkflow.interpret()
    with intelligent semantic understanding.

    Args:
        user_text: Natural language instruction from user
        context_json: JSON string with Haystack context data

    Returns:
        ParsedInstruction with structured intent and parameters
    """
    try:
        context = json.loads(context_json) if context_json else {}
        ai_raw_response = call_gemini_api(user_text, context)
        ai_instruction = json.loads(ai_raw_response)

        # Validate required fields
        if "error" in ai_instruction:
            # LLM failed, fall back to rule-based
            return _fallback_to_rule_parsing(user_text)

        intent = ai_instruction.get("intent", "unknown")
        parameters = ai_instruction.get("parameters", {})
        thought = ai_instruction.get("thought_process", "")

        # Map generic intents to specific actions
        action_mapping = {
            "ACTION_DIAGNOSIS": "diagnose",
            "ACTION_OPTIMIZE": "optimize",
            "ACTION_INSPECT": "inspect",
            "ACTION_HMI": "hmi",
            "ACTION_REPORT": "report",
            "ACTION_QUERY": "query",
        }

        mapped_action = action_mapping.get(intent, intent)

        return ParsedInstruction(
            action=mapped_action,
            confidence=0.95,  # High confidence from LLM
            payload=parameters,
            raw_text=user_text
        )

    except json.JSONDecodeError:
        return _fallback_to_rule_parsing(user_text)
    except Exception as e:
        # On any error, fall back to rule-based
        return ParsedInstruction(
            action="unknown",
            confidence=0.0,
            payload={"hint": "请重新描述您的需求"},
            raw_text=user_text
        )


def _fallback_to_rule_parsing(user_text: str) -> ParsedInstruction:
    """Fallback to rule-based parsing when LLM is unavailable."""
    from baAgentPy.core.agent_workflow import AgentWorkflow

    # Create a minimal workflow for fallback
    workflow = AgentWorkflow(engines=[
        FddEngine(),
        EnergyOptEngine(),
        InspectEngine(),
        HmiEngine(),
        ReportEngine(),
    ])

    # Use rule-based interpretation
    parsed = workflow.interpret(user_text)

    # Add indication that fallback was used
    if parsed.action == "unknown":
        parsed.payload["_fallback_used"] = True
        parsed.payload["_llm_unavailable"] = True

    return parsed


# ============================================================
# Main Service Class
# ============================================================

def _create_default_workflow() -> AgentWorkflow:
    """Create an AgentWorkflow with all domain engines registered."""
    return AgentWorkflow(engines=[
        FddEngine(),
        EnergyOptEngine(),
        InspectEngine(),
        HmiEngine(),
        ReportEngine(),
        TaggingEngine(),
    ])


class BaAgentService:
    """Central AI service loaded by hxPy.

    Orchestrates:
    - LLM-based intent parsing (Gemini)
    - Rule-based domain engines (FDD, energy, inspection, HMI, report)
    - Haystack Grid conversion for data interchange
    """

    def __init__(self, enable_llm: bool = True) -> None:
        self._converter = GridConverter()
        self._workflow = _create_default_workflow()
        self._llm_enabled = enable_llm and bool(API_KEY)
        self._initialized = True

    @property
    def registered_actions(self) -> list[str]:
        """List all supported service actions."""
        return ["diagnose", "optimize", "inspect", "hmi", "report", "query", "ping"]

    @property
    def registered_engines(self) -> list[str]:
        """List all registered engine names."""
        return list(self._workflow._engines.keys())

    @property
    def llm_status(self) -> dict[str, str]:
        """Get LLM service status."""
        if self._llm_enabled:
            return {"status": "enabled", "provider": "gemini-2.5-flash"}
        else:
            return {"status": "disabled", "reason": "API_KEY not configured"}

    def handle(self, action: str, payload: dict[str, Any] | None = None,
               grid: pd.DataFrame | None = None) -> dict[str, Any]:
        """
        Route a structured action to the appropriate engine.

        Args:
            action: The service action to perform.
            payload: Action-specific parameters as a dict.
            grid: Optional DataFrame with context data.

        Returns:
            Dict that hxPy converts back to a Haystack Grid for AXON consumption.
        """
        if payload is None:
            payload = {}

        if grid is not None:
            payload["grid"] = self._converter.normalize_dataframe(grid)

        # Handle built-in actions directly
        if action == "ping":
            return self._respond_ok(action, self._handle_ping())

        # Route through workflow
        try:
            if self._llm_enabled and action == "ask":
                # Use LLM for natural language parsing
                # payload is a dict when action="ask", extract values safely
                text_val = payload.get("text") if isinstance(payload, dict) else None
                context_val = payload.get("context") if isinstance(payload, dict) else None

                parsed = parse_with_llm(
                    text_val or "",
                    context_val or "{}"
                )

                if parsed.action == "unknown":
                    # LLM couldn't understand, return error
                    return self._respond_error(
                        action,
                        f"无法理解指令: {parsed.raw_text}"
                    )

                # Execute the parsed action
                engine_result = self._workflow.route(parsed.action, parsed.payload)

                # Combine LLM thought process with engine result
                result_data = engine_result.data or {}
                result_data["_llm_confidence"] = parsed.confidence
                result_data["_llm_thought"] = parsed.payload.get("thought_process", "")

                return self._respond_ok(action, result_data)

            elif action in self._workflow.registered_actions:
                # Direct action execution - use rule-based routing
                engine_result = self._workflow.route(action, payload)
                return self._respond_ok(action, engine_result.model_dump())

            else:
                return self._respond_error(
                    action,
                    f"Unknown action: {action}. Available: {self.registered_actions}"
                )

        except ValueError as e:
            return self._respond_error(action, str(e))
        except Exception as e:
            return self._respond_error(action, f"Internal error: {str(e)}")

    def ask(self, text: str, grid: pd.DataFrame | None = None) -> dict[str, Any]:
        """
        Natural language entry point — parse instruction and route.

        This is the primary interface for NL commands from the frontend
        or AXON's agentAsk op.

        Args:
            text: Natural language instruction (Chinese or English).
            grid: Optional DataFrame with context data.

        Returns:
            Dict with action result for hxPy Grid conversion.
        """
        payload: dict[str, Any] = {"text": text}
        if grid is not None:
            payload["grid"] = self._converter.normalize_dataframe(grid)

        # Add context if grid contains site/equip info
        context: dict[str, Any] = {}
        if grid is not None and not grid.empty:
            # Extract context from grid for LLM
            if 'site' in grid.columns:
                sites = grid['site'].dropna().unique().tolist()
                if sites:
                    context["available_sites"] = sites[:5]  # First 5 sites
            if 'equip' in grid.columns:
                equips = grid['equip'].dropna().unique().tolist()
                if equips:
                    context["available_equips"] = equips[:10]  # First 10 equips
            if 'point' in grid.columns:
                points = grid['point'].dropna().unique().tolist()
                if points:
                    context["available_points"] = points[:20]  # First 20 points
            context["context_summary"] = f"系统包含{len(grid)}条记录"

        payload["context"] = json.dumps(context, ensure_ascii=False)

        # Delegate to handle with LLM processing
        return self.handle(action="ask", payload=payload, grid=grid)

    def _respond_ok(self, action: str, result: dict[str, Any]) -> dict[str, Any]:
        """Build a successful response dict."""
        return {
            "status": "ok",
            "action": action,
            "result": result,
            "llm_enabled": self._llm_enabled,
        }

    def _respond_error(self, action: str, message: str) -> dict[str, Any]:
        """Build an error response dict."""
        return {
            "status": "error",
            "action": action,
            "error": message,
            "llm_enabled": self._llm_enabled,
        }

    def _handle_ping(self) -> dict[str, Any]:
        """Health check — verifies service is alive."""
        return {
            "status": "ok",
            "initialized": self._initialized,
            "llm_status": self.llm_status,
            "engines": self.registered_engines,
            "actions": self.registered_actions,
        }


# ============================================================
# Local Debugging Entry Point
# ============================================================

def main() -> None:
    """Local debugging: test BaAgentService outside hxPy."""
    import sys

    print("=" * 60)
    print("BA-Agent Service - Local Testing Mode")
    print("=" * 60)
    print()

    # Check LLM configuration
    api_status = "configured" if API_KEY else "not configured"
    print(f"LLM Status: {api_status}")
    print(f"API Endpoint: {MODEL_ENDPOINT[:50]}...")
    print()

    # Create service instance
    svc = BaAgentService(enable_llm=True)

    print("Registered Actions:", svc.registered_actions)
    print("Registered Engines:", svc.registered_engines)
    print()

    # Test cases
    test_cases = [
        ("诊断一下 AHU-01 的故障", "diagnose"),
        ("优化12楼空调设定值", "optimize"),
        ("检查所有温度传感器状态", "inspect"),
        ("生成12楼AHU监控画面", "hmi"),
        ("生成今日运维报告", "report"),
        ("查询系统状态", "query"),
    ]

    for i, (test_input, expected_action) in enumerate(test_cases, 1):
        print(f"Test {i}: {test_input}")
        print(f"Expected action: {expected_action}")
        print("-" * 40)

        response = svc.ask(test_input)

        # Parse response
        if isinstance(response, str):
            resp_dict = json.loads(response)
        else:
            resp_dict = response

        print(f"Status: {resp_dict.get('status')}")
        print(f"Action: {resp_dict.get('action')}")

        if 'result' in resp_dict:
            result = resp_dict['result']
            if '_llm_confidence' in result:
                print(f"  LLM Confidence: {result['_llm_confidence']}")
            if '_llm_thought' in result:
                thought = result.get('_llm_thought', 'N/A')
                print(f"  LLM Thought: {thought}")

        print()
        print("=" * 60)
