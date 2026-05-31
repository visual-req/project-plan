from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .app_config import LlmConfig


@dataclass(frozen=True)
class LlmResult:
    data: dict[str, Any]
    raw_text: str


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return json.loads(text)
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in model output")
    return json.loads(match.group(0))


async def chat_completions_json(
    config: LlmConfig,
    system_prompt: str,
    user_prompt: str,
) -> LlmResult:
    if not config.enabled:
        raise RuntimeError("LLM is disabled (llm.enabled=false)")

    base_url = config.base_url.rstrip("/")
    url = f"{base_url}/chat/completions"
    headers: dict[str, str] = {}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"

    payload: dict[str, Any] = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    if config.force_json:
        payload["response_format"] = {"type": "json_object"}

    timeout = httpx.Timeout(config.timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        body = resp.json()

    content = (
        body.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    data = _extract_json_object(content)
    return LlmResult(data=data, raw_text=content)


def mock_decompose(requirement_text: str) -> dict[str, Any]:
    lines = [x.strip() for x in requirement_text.splitlines() if x.strip()]
    seeds = lines[:8] if lines else ["需求梳理", "主流程", "异常与校验", "权限与角色", "数据存储", "导入导出", "日志与审计", "性能与体验"]
    stories: list[dict[str, Any]] = []
    for idx, seed in enumerate(seeds, start=1):
        sid = f"US-{idx}"
        stories.append(
            {
                "id": sid,
                "module": "需求分析",
                "feature": "需求拆解",
                "title": seed[:32],
                "user_story": f"作为用户，我想完成「{seed}」，以便实现需求目标。",
                "acceptance_criteria": [f"当我执行「{seed}」时系统返回成功结果", f"当输入不合法时系统给出明确错误提示"],
                "priority": "P1" if idx > 2 else "P0",
                "dependencies": [],
                "notes": "Mock 输出：请在 config.yaml 打开 llm.enabled 并配置模型参数以获得真实结果。",
            }
        )
    return {"stories": stories}


def mock_schedule(stories: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [s.get("id") for s in stories if s.get("id")]
    mvp = ids[: max(4, len(ids) // 2)]
    v1 = ids[len(mvp) :]
    return {
        "backbone": ["获取需求", "分解", "排期", "估算", "输出与复盘"],
        "releases": [
            {"name": "MVP", "themes": [{"name": "核心链路", "story_ids": mvp}]},
            {"name": "V1", "themes": [{"name": "完善与扩展", "story_ids": v1}]},
        ],
    }


def mock_estimate(stories: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for s in stories:
        sid = s.get("id")
        if not sid:
            continue
        rows.append(
            {
                "story_id": sid,
                "complexity": "M",
                "dev_days": 2.0,
                "test_days": 1.0,
                "pm_days": 0.5,
                "risk": "中",
                "assumptions": ["需求范围不发生重大变化"],
            }
        )
    return {"rows": rows}
