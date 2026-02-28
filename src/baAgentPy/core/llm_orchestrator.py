"""LLM-powered orchestrator — unified routing and intent parsing.

Merges AgentWorkflow's engine registry/routing with LLM-based intent parsing.
This is the single entry point for all AI operations in BA-Agent.

Responsibilities:
    - Engine registration and action routing (from AgentWorkflow)
    - Rule-based intent parsing via keyword patterns
    - LLM-based intent parsing via Gemini API
    - Unified handle()/ask() interface with flat response format
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from baAgentPy.core.agent_workflow import ParsedInstruction, _INTENT_PATTERNS
from baAgentPy.services.base import BaseEngine, EngineResult


# ── LLM Configuration ──

# Gemini API Configuration
API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAz5LOHMBbFhkwzpomDcE50VvnQtimnAoE")

# Gemini 2.5 Flash API Endpoint
MODEL_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview:generateContent?key={API_KEY}"

# Retry configuration
MAX_RETRIES = 5
RETRY_DELAYS = [1, 2, 4, 8, 16]  # seconds
REQUEST_TIMEOUT = 30  # seconds

# System Prompt for intent parsing
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

用户: "优化节能模式，降低能耗"
回复:
{
  "intent": "ACTION_OPTIMIZE",
  "parameters": {"mode": "energy_save", "target": "building"},
  "thought_process": "用户希望启用节能优化策略"
}
"""

# LLM intent → engine action mapping
_INTENT_ACTION_MAP: dict[str, str] = {
    "ACTION_DIAGNOSIS": "diagnose",
    "ACTION_OPTIMIZE": "optimize",
    "ACTION_INSPECT": "inspect",
    "ACTION_HMI": "hmi",
    "ACTION_REPORT": "report",
    "ACTION_QUERY": "query",
}


# ── LLM API Functions ──


def _call_gemini_api(user_query: str, context_info: dict[str, Any] | None = None) -> str:
    """Call Gemini 2.5 Flash API for intent parsing with exponential backoff retry."""
    if not API_KEY:
        return json.dumps({
            "error": "AI_SERVICE_NOT_CONFIGURED",
            "reply": "LLM服务未配置，请检查GEMINI_API_KEY环境变量。"
        }, ensure_ascii=False)

    if context_info:
        context_str = json.dumps(context_info, ensure_ascii=False)
        full_instruction = f"{SYSTEM_PROMPT}\n\n## 当前上下文环境:\n{context_str}"
    else:
        full_instruction = SYSTEM_PROMPT

    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": full_instruction}]},
        "generationConfig": {"responseMimeType": "application/json"},
    }

    last_error: str | None = None
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            response = _make_request(payload, delay)
            if response.status_code == 200:
                result = response.json()
                content = result.get("candidates", [{}])[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "")
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.endswith("```"):
                        text = text[:-3]
                    return text.strip()  # type: ignore[no-any-return]
                return '{"error": "AI_RESPONSE_FORMAT_ERROR"}'
            else:
                last_error = f"HTTP {response.status_code}"
        except Exception as e:
            last_error = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(delay)

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
        headers={"Content-Type": "application/json"},
    )


# ── LLMOrchestrator ──


class LLMOrchestrator:
    """Unified orchestrator for BA-Agent AI operations.

    Combines engine registry/routing (previously in AgentWorkflow) with
    LLM-based intent parsing and flat response format generation.

    Usage:
        orchestrator = LLMOrchestrator(engines=[...], enable_llm=True)
        result = orchestrator.handle("diagnose", {"alarm_id": "..."})
        result = orchestrator.ask("诊断一下AHU-01的报警")
    """

    def __init__(
        self,
        engines: list[BaseEngine] | None = None,
        enable_llm: bool = True,
    ) -> None:
        self._engines: dict[str, BaseEngine] = {}
        self._action_map: dict[str, BaseEngine] = {}
        self._llm_enabled = enable_llm and bool(API_KEY)

        if engines:
            for engine in engines:
                self.register_engine(engine)

    def register_engine(self, engine: BaseEngine) -> None:
        """Register a domain engine and index its actions."""
        self._engines[engine.name] = engine
        for action in engine.actions:
            self._action_map[action] = engine

    @property
    def registered_actions(self) -> list[str]:
        """List all actions supported by registered engines."""
        return list(self._action_map.keys())

    @property
    def registered_engines(self) -> list[str]:
        """List all registered engine names."""
        return list(self._engines.keys())

    @property
    def llm_enabled(self) -> bool:
        return self._llm_enabled

    @property
    def llm_status(self) -> dict[str, str]:
        """Get LLM service status."""
        if self._llm_enabled:
            return {"status": "enabled", "provider": "gemini-2.5-flash"}
        return {"status": "disabled", "reason": "API_KEY not configured"}

    # ── Engine Routing ──

    def route(self, action: str, payload: dict[str, Any] | None = None) -> EngineResult:
        """Route a structured action to the appropriate engine.

        Args:
            action: The action name (e.g., 'diagnose', 'optimize').
            payload: Action-specific data.

        Returns:
            EngineResult from the domain engine.

        Raises:
            ValueError: If no engine is registered for the action.
        """
        if payload is None:
            payload = {}

        engine = self._action_map.get(action)
        if engine is None:
            raise ValueError(
                f"No engine registered for action '{action}'. "
                f"Available: {self.registered_actions}"
            )

        return engine.execute(action, payload)

    # ── Rule-based Intent Parsing ──

    def interpret(self, text: str) -> ParsedInstruction:
        """Parse a natural language instruction using keyword patterns.

        Reuses _INTENT_PATTERNS from agent_workflow for backward compatibility.
        """
        text_clean = text.strip()
        best_action = ""
        best_confidence = 0.0
        match_count = 0

        for pattern, action, base_confidence in _INTENT_PATTERNS:
            matches = pattern.findall(text_clean)
            if matches:
                adjusted = min(base_confidence + len(matches) * 0.05, 0.95)
                if adjusted > best_confidence:
                    best_action = action
                    best_confidence = adjusted
                    match_count = len(matches)

        if not best_action:
            return ParsedInstruction(
                action="unknown",
                confidence=0.0,
                payload={"hint": "Could not parse instruction. Try: diagnose, optimize, inspect, hmi, report, tag"},
                raw_text=text_clean,
            )

        return ParsedInstruction(
            action=best_action,
            confidence=best_confidence,
            payload={"match_count": match_count},
            raw_text=text_clean,
        )

    # ── LLM Intent Parsing ──

    def interpret_with_llm(self, text: str, context_json: str = "{}") -> ParsedInstruction:
        """Parse user instruction using LLM (Gemini).

        Falls back to rule-based parsing if LLM fails.
        """
        try:
            context = json.loads(context_json) if context_json else {}
            ai_raw = _call_gemini_api(text, context)
            ai_data = json.loads(ai_raw)

            if "error" in ai_data:
                return self.interpret(text)

            intent = ai_data.get("intent", "unknown")
            parameters = ai_data.get("parameters", {})

            mapped_action = _INTENT_ACTION_MAP.get(intent, intent)

            return ParsedInstruction(
                action=mapped_action,
                confidence=0.95,
                payload=parameters,
                raw_text=text,
            )

        except json.JSONDecodeError:
            return self.interpret(text)
        except Exception:
            return ParsedInstruction(
                action="unknown",
                confidence=0.0,
                payload={"hint": "请重新描述您的需求"},
                raw_text=text,
            )

    # ── Unified Entry Points ──

    def handle(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Route a structured action and return flat response dict.

        Args:
            action: The service action to perform.
            payload: Action-specific parameters.

        Returns:
            Flat dict with ok, action, r_* keys (for hxPy Grid conversion).
        """
        if payload is None:
            payload = {}

        if action == "ping":
            return self._respond_ok(action, self._handle_ping())

        try:
            if action == "ask":
                text = payload.get("text", "")

                if self._llm_enabled:
                    context_val = payload.get("context", "{}")
                    parsed = self.interpret_with_llm(text, context_val or "{}")
                else:
                    parsed = self.interpret(text)

                if parsed.action == "unknown":
                    return self._respond_error(action, f"无法理解指令: {parsed.raw_text}")

                engine_result = self.route(parsed.action, parsed.payload)
                result_data = self._flatten_engine_result(engine_result)

                if self._llm_enabled:
                    result_data["_llm_confidence"] = parsed.confidence
                    result_data["_llm_thought"] = parsed.payload.get("thought_process", "")

                return self._respond_ok(parsed.action, result_data)

            elif action in self._action_map:
                engine_result = self.route(action, payload)
                result_data = self._flatten_engine_result(engine_result)
                return self._respond_ok(action, result_data)

            else:
                all_actions = self.registered_actions + ["ping", "ask"]
                return self._respond_error(
                    action,
                    f"Unknown action: {action}. Available: {all_actions}"
                )

        except ValueError as e:
            return self._respond_error(action, str(e))
        except Exception as e:
            return self._respond_error(action, f"Internal error: {str(e)}")

    def ask(self, text: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Natural language entry point — parse instruction and route.

        Args:
            text: Natural language instruction (Chinese or English).
            payload: Optional additional payload data (grid, context, etc.).

        Returns:
            Flat response dict for hxPy Grid conversion.
        """
        ask_payload: dict[str, Any] = {"text": text}
        if payload:
            ask_payload.update(payload)
        return self.handle(action="ask", payload=ask_payload)

    # ── Response Helpers ──

    @staticmethod
    def _flatten_engine_result(engine_result: EngineResult) -> dict[str, Any]:
        """Flatten an EngineResult into a simple dict for response building."""
        result_data = engine_result.data or {}
        result_data["status"] = engine_result.status
        result_data["message"] = engine_result.message
        if engine_result.confidence is not None:
            result_data["confidence"] = engine_result.confidence
        return result_data

    @staticmethod
    def _respond_ok(action: str, result: dict[str, Any]) -> dict[str, Any]:
        """Build a successful response dict with flat r_ prefixed keys."""
        out: dict[str, Any] = {"ok": True, "action": action}
        for key, value in result.items():
            out[f"r_{key}"] = value
        return out

    @staticmethod
    def _respond_error(action: str, message: str) -> dict[str, Any]:
        """Build an error response dict."""
        return {"ok": False, "action": action, "error": message}

    def _handle_ping(self) -> dict[str, Any]:
        """Health check — verifies service is alive."""
        return {
            "status": "ok",
            "initialized": True,
            "llm_status": self.llm_status,
            "engines": self.registered_engines,
            "actions": self.registered_actions,
        }
