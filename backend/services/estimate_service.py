from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.app_config import AppConfig
from backend.llm_client import LlmOutputParseError, chat_completions_json
from backend.meta_service import load_estimation_standards
from backend.storage import atomic_write_json, atomic_write_text, read_json

SYSTEM_PROMPT = "你是严谨的工作量估算助手，必须按要求只输出 JSON。"


def _output_language(lang: str | None) -> str:
    if not lang:
        return "中文"
    low = lang.lower()
    if low.startswith("zh"):
        return "中文"
    if low.startswith("ja") or low.startswith("jp"):
        return "日本語"
    if low.startswith("en"):
        return "English"
    return "中文"


def build_prompt(
    requirement_text: str,
    stories_json: str,
    standards_json: str,
    lang: str | None,
) -> str:
    output_language = _output_language(lang)
    return f"""你是交付经理与技术负责人。请基于“原始需求 + 用户故事分解结果”，为每条用户故事给出标准估算，并严格输出 JSON（不要输出任何额外文字）。

输出 JSON 结构：
{{
  "rows": [
    {{
      "story_id": "US-1",
      "module": "模块名",
      "feature": "功能点",
      "complexity": "S|M|L|XL",
      "dev_days": 2.5,
      "test_days": 1.0,
      "pm_days": 0.5,
      "assumptions": ["假设1", "假设2"]
    }}
  ]
}}

要求：
1) story_id 必须来自给定用户故事列表
2) 天数为 0.5 的倍数
3) assumptions 至少 1 条
4) 不要输出 Markdown，不要输出解释，只输出 JSON
5) module/feature 必须填写，便于表格阅读
6) assumptions 等文案使用 {output_language}
7) 估算需参考“标准估算值”（JSON），在 complexity 选择与天数上保持一致（可在标准估算基础上按 0.5 天粒度微调）

原始需求：
{requirement_text}

用户故事分解（JSON）：
{stories_json}

标准估算值（JSON）：
{standards_json}
"""


async def run(
    config: AppConfig,
    requirement_text: str,
    stories_json: str,
    decompose_data: dict[str, Any],
    paths: dict[str, Any],
    lang: str | None,
) -> dict[str, Any]:
    cached = read_json(paths["estimate_json"])
    if cached:
        if isinstance(cached, dict) and cached.get("_meta", {}).get("source") == "llm":
            rows = cached.get("rows")
            if isinstance(rows, list) and (
                not rows
                or isinstance(rows[0], dict)
                and "module" in rows[0]
                and "feature" in rows[0]
                and "risk" not in rows[0]
            ):
                return cached
        if not config.llm.enabled:
            return cached

    standards = load_estimation_standards(config)
    user_prompt = build_prompt(
        requirement_text, stories_json, json.dumps(standards, ensure_ascii=False), lang
    )

    try:
        result = await chat_completions_json(config.llm, SYSTEM_PROMPT, user_prompt)
    except LlmOutputParseError as e:
        atomic_write_text(paths["llm_raw_estimate"], e.raw_text)
        raise
    atomic_write_text(paths["llm_raw_estimate"], result.raw_text)
    data: dict[str, Any] = dict(result.data)
    data["_meta"] = {
        "source": "llm",
        "lang": lang,
        "model": config.llm.model,
        "base_url": config.llm.base_url,
        "temperature": config.llm.temperature,
        "max_tokens": config.llm.max_tokens,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write_json(paths["estimate_json"], data)
    return data
