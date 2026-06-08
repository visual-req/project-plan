from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app_config import AppConfig
from backend.llm_client import LlmOutputParseError, chat_completions_json
from backend.storage import atomic_write_json, atomic_write_text, read_json

SYSTEM_PROMPT = "你是严谨的排期与故事地图助手，必须按要求只输出 JSON。"


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


def build_prompt(requirement_text: str, stories_json: str, lang: str | None) -> str:
    output_language = _output_language(lang)
    return f"""你是交付经理。请基于“原始需求 + 用户故事分解结果”，输出一个“迭代排期的用户故事地图（User Story Map）”的数据结构，并严格输出 JSON（不要输出任何额外文字）。

输出 JSON 结构：
{{
  "modules": ["模块1", "模块2"],
  "iterations": [
    {{
      "name": "MVP",
      "lanes": [
        {{
          "module": "模块1",
          "stories": [
            {{
              "id": "US-1",
              "feature": "功能点",
              "title": "简短标题"
            }}
          ]
        }}
      ]
    }}
  ]
}}

要求：
1) modules 为横向列，来自分解结果中的 module，按主流程排序
2) iterations 至少包含 MVP 与 V1 两个，每个 iteration 表示一条横向泳道
3) lanes 必须覆盖 modules 中的所有 module（缺失时用空 stories 数组补齐）
4) stories.id 必须来自给定用户故事列表，且应按优先级/依赖合理分配到迭代
5) 不要输出 Markdown，不要输出解释，只输出 JSON
6) 除 JSON key 以外，所有字段值使用 {output_language}

原始需求：
{requirement_text}

用户故事分解（JSON）：
{stories_json}
"""


async def run(
    config: AppConfig,
    requirement_text: str,
    stories_json: str,
    decompose_data: dict[str, Any],
    paths: dict[str, Any],
    lang: str | None,
) -> dict[str, Any]:
    cached = read_json(paths["schedule_json"])
    if cached:
        if (
            isinstance(cached, dict)
            and cached.get("_meta", {}).get("source") == "llm"
            and isinstance(cached.get("modules"), list)
            and isinstance(cached.get("iterations"), list)
        ):
            return cached
        if not config.llm.enabled:
            return cached

    user_prompt = build_prompt(requirement_text, stories_json, lang)

    try:
        result = await chat_completions_json(config.llm, SYSTEM_PROMPT, user_prompt)
    except LlmOutputParseError as e:
        atomic_write_text(paths["llm_raw_schedule"], e.raw_text)
        raise
    atomic_write_text(paths["llm_raw_schedule"], result.raw_text)
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
    atomic_write_json(paths["schedule_json"], data)
    return data
