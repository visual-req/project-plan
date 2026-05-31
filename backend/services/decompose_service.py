from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app_config import AppConfig
from backend.llm_client import chat_completions_json
from backend.storage import atomic_write_json, atomic_write_text, read_json

SYSTEM_PROMPT = "你是严谨的需求分析助手，必须按要求只输出 JSON。"


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


def build_prompt(requirement_text: str, lang: str | None) -> str:
    output_language = _output_language(lang)
    return f"""你是资深产品经理与交付经理。请把下面的原始需求分解为“用户故事”表格数据，并严格输出 JSON（不要输出任何额外文字）。

输出 JSON 结构：
{{
  "stories": [
    {{
      "id": "US-1",
      "module": "模块名",
      "feature": "功能点",
      "title": "简短标题",
      "user_story": "作为…我想…以便…",
      "acceptance_criteria": ["AC1", "AC2"],
      "priority": "P0|P1|P2",
      "dependencies": ["US-2"],
      "notes": "实现要点/边界/异常"
    }}
  ]
}}

要求：
1) 至少输出 8 条用户故事，覆盖主流程与异常流程
2) acceptance_criteria 必须可验收、具体、可测试
3) dependencies 若无依赖请输出空数组
4) 不要输出 Markdown，不要输出表格文本，只输出 JSON
5) module/feature 必须填写，用于分组与故事地图整理
6) 除 JSON key 以外，所有字段值使用 {output_language}

原始需求：
{requirement_text}
"""


async def run(config: AppConfig, requirement_text: str, paths: dict[str, Any], lang: str | None) -> dict[str, Any]:
    cached = read_json(paths["decompose_json"])
    if cached:
        if isinstance(cached, dict) and cached.get("_meta", {}).get("source") == "llm":
            stories = cached.get("stories")
            if isinstance(stories, list) and (
                not stories
                or isinstance(stories[0], dict)
                and "module" in stories[0]
                and "feature" in stories[0]
            ):
                return cached
        if not config.llm.enabled:
            return cached

    user_prompt = build_prompt(requirement_text, lang)

    result = await chat_completions_json(config.llm, SYSTEM_PROMPT, user_prompt)
    atomic_write_text(paths["llm_raw_decompose"], result.raw_text)
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
    atomic_write_json(paths["decompose_json"], data)
    return data

