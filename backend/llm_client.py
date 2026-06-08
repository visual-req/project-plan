from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
import codecs
import yaml

from .app_config import LlmConfig


@dataclass(frozen=True)
class LlmResult:
    data: dict[str, Any]
    raw_text: str


class LlmOutputParseError(ValueError):
    def __init__(self, message: str, raw_text: str) -> None:
        super().__init__(message)
        self.raw_text = raw_text


def _truncate(text: str, limit: int = 800) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _extract_upstream_error_message(text: str) -> str:
    t = text.strip()
    if not t:
        return ""
    try:
        data = json.loads(t)
    except Exception:
        return _truncate(t)
    if isinstance(data, dict):
        err = data.get("error")
        if isinstance(err, dict) and isinstance(err.get("message"), str):
            return _truncate(err["message"])
        if isinstance(data.get("message"), str):
            return _truncate(str(data["message"]))
        if isinstance(data.get("detail"), str):
            return _truncate(str(data["detail"]))
    return _truncate(t)


def _format_decode_error(candidate: str, e: json.JSONDecodeError) -> str:
    start = max(0, e.pos - 200)
    end = min(len(candidate), e.pos + 200)
    snippet = candidate[start:end].replace("\n", "\\n")
    return (
        f"{e.msg} (line {e.lineno} column {e.colno} char {e.pos})"
        f"，输出片段：{_truncate(snippet, 450)}"
    )


def _repair_json_like(text: str) -> str:
    s = text
    if re.match(r"^\s*\{\\\"", s) and '\\"' in s and '"stories"' not in s:
        try:
            unescaped = codecs.decode(s, "unicode_escape")
            if re.match(r'^\s*\{".*"\s*:', unescaped) or '"stories"' in unescaped:
                s = unescaped
        except Exception:
            pass

    s = re.sub(r",(\s*[\]}])", r"\1", s)
    s = re.sub(r'\\\\"(?=\s*[,}\]])', r'"', s)
    s = re.sub(r'\\"(?=\s*[,}\]])', r'"', s)
    s = re.sub(r'\\"(?=\s*\n\s*")', r'"', s)
    return s


def _salvage_array_of_objects(text: str, key: str) -> list[dict[str, Any]] | None:
    m = re.search(rf'"{re.escape(key)}"\s*:\s*\[', text)
    if not m:
        return None
    i = m.end()

    items: list[dict[str, Any]] = []
    n = len(text)
    while i < n:
        while i < n and text[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        if text[i] == "]":
            break
        if text[i] != "{":
            i += 1
            continue

        start = i
        i += 1
        depth = 1
        in_str = False
        esc = False
        while i < n and depth > 0:
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
            i += 1

        if depth != 0:
            break

        obj_text = text[start:i]
        obj_repaired = _repair_json_like(obj_text)
        try:
            obj = json.loads(obj_repaired)
        except Exception:
            continue
        if isinstance(obj, dict):
            items.append(obj)

    return items or None


def _salvage_partial_result(text: str) -> dict[str, Any] | None:
    stories = _salvage_array_of_objects(text, "stories")
    if stories is not None:
        return {"stories": stories}
    rows = _salvage_array_of_objects(text, "rows")
    if rows is not None:
        return {"rows": rows}
    return None


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        candidate = text
    else:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("No JSON object found in model output")
        candidate = match.group(0)

    json_error: json.JSONDecodeError | None = None
    candidates: list[str] = []
    candidates.append(candidate)
    repaired = _repair_json_like(candidate)
    if repaired != candidate:
        candidates.append(repaired)

    for c in candidates:
        try:
            data = json.loads(c)
            break
        except json.JSONDecodeError as e:
            json_error = e
            data = None
    else:
        for c in candidates:
            try:
                data = yaml.safe_load(c)
                break
            except Exception:
                data = None

        if data is None:
            if json_error is None:
                raise ValueError("大模型输出解析失败：无法解析为 JSON 对象")
            best = repaired if repaired != candidate else candidate
            salvaged = _salvage_partial_result(best)
            if salvaged is not None:
                return salvaged
            raise ValueError(f"大模型输出解析失败：{_format_decode_error(best, json_error)}") from json_error

    if not isinstance(data, dict):
        raise ValueError(f"Model output is not a JSON object (type={type(data).__name__})")
    return data


async def chat_completions_json(
    config: LlmConfig,
    system_prompt: str,
    user_prompt: str,
) -> LlmResult:
    if not config.enabled:
        raise RuntimeError("LLM is disabled (llm.enabled=false)")
    if not config.api_key:
        raise RuntimeError(
            "未配置大模型 API_KEY。请执行：export LLM_API_KEY=\"你的KEY\" 然后重新启动服务。"
        )

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
        try:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            body = resp.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            upstream = _extract_upstream_error_message(e.response.text)
            hint = ""
            if status in (401, 403):
                hint = "请检查 LLM_API_KEY/OPENAI_API_KEY 是否正确，以及 llm.base_url 是否匹配。"
            elif status == 404:
                hint = "请检查 llm.base_url 与 llm.model 是否正确。"
            elif status == 429:
                hint = "可能触发限流/配额不足/并发过高，请稍后重试或降低并发。"
            elif status >= 500:
                hint = "上游服务异常，请稍后重试。"

            msg = f"大模型调用失败：HTTP {status}"
            if upstream:
                msg += f"，上游返回：{upstream}"
            if hint:
                msg += f"。{hint}"
            raise RuntimeError(msg) from e
        except httpx.TimeoutException as e:
            raise RuntimeError(
                f"大模型调用失败：请求超时（timeout_seconds={config.timeout_seconds}）。"
                "请检查网络/上游服务，或适当增大 timeout_seconds。"
            ) from e
        except httpx.RequestError as e:
            raise RuntimeError(
                f"大模型调用失败：无法连接到上游（{type(e).__name__}）。"
                "请检查 llm.base_url、网络代理、DNS、证书等。"
            ) from e

    content = (
        body.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    try:
        data = _extract_json_object(content)
    except ValueError as e:
        raise LlmOutputParseError(str(e), raw_text=content) from e
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
