from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PathsConfig:
    work_dir: Path
    inputs_dir: Path
    outputs_dir: Path
    meta_dir: Path


@dataclass(frozen=True)
class LlmConfig:
    enabled: bool
    base_url: str
    api_key: str
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: float
    force_json: bool


@dataclass(frozen=True)
class JenkinsConfig:
    enabled: bool
    base_url: str
    username: str
    api_token: str
    timeout_seconds: float
    verify_ssl: bool


@dataclass(frozen=True)
class SonarConfig:
    enabled: bool
    base_url: str
    token: str
    organization: str
    project_key: str
    timeout_seconds: float
    verify_ssl: bool


@dataclass(frozen=True)
class AppConfig:
    paths: PathsConfig
    llm: LlmConfig
    jenkins: JenkinsConfig
    sonar: SonarConfig


def _deep_get(data: dict[str, Any], path: str, default: Any) -> Any:
    cur: Any = data
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def _find_config_file(start: Path) -> Path | None:
    cur = start.resolve()
    for _ in range(6):
        candidate = cur / "backend" / "config.yaml"
        if candidate.exists():
            return candidate
        candidate = cur / "config.yaml"
        if candidate.exists():
            return candidate
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def load_config(config_path: str | None = None) -> AppConfig:
    config_file = Path(config_path).expanduser().resolve() if config_path else _find_config_file(Path.cwd())
    data: dict[str, Any] = {}
    if config_file and config_file.exists():
        data = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}

    work_dir = Path(str(_deep_get(data, "paths.work_dir", "/work")))
    inputs_dir = Path(str(_deep_get(data, "paths.inputs_dir", str(work_dir / "inputs"))))
    outputs_dir = Path(str(_deep_get(data, "paths.outputs_dir", str(work_dir / "outputs"))))
    meta_dir = Path(str(_deep_get(data, "paths.meta_dir", str(work_dir / "meta"))))

    llm = LlmConfig(
        enabled=bool(_deep_get(data, "llm.enabled", False)),
        base_url=str(_deep_get(data, "llm.base_url", "")),
        api_key=str(
            _deep_get(data, "llm.api_key", "")
            or os.environ.get("LLM_API_KEY", "")
            or os.environ.get("OPENAI_API_KEY", "")
        ),
        model=str(_deep_get(data, "llm.model", "gpt-4.1-mini")),
        temperature=float(_deep_get(data, "llm.temperature", 0.2)),
        max_tokens=int(_deep_get(data, "llm.max_tokens", 2000)),
        timeout_seconds=float(_deep_get(data, "llm.timeout_seconds", 60)),
        force_json=bool(_deep_get(data, "llm.force_json", True)),
    )

    jenkins = JenkinsConfig(
        enabled=bool(_deep_get(data, "jenkins.enabled", False)),
        base_url=str(_deep_get(data, "jenkins.base_url", "") or os.environ.get("JENKINS_BASE_URL", "")),
        username=str(_deep_get(data, "jenkins.username", "") or os.environ.get("JENKINS_USERNAME", "")),
        api_token=str(_deep_get(data, "jenkins.api_token", "") or os.environ.get("JENKINS_API_TOKEN", "")),
        timeout_seconds=float(_deep_get(data, "jenkins.timeout_seconds", 30)),
        verify_ssl=bool(_deep_get(data, "jenkins.verify_ssl", True)),
    )

    sonar = SonarConfig(
        enabled=bool(_deep_get(data, "sonar.enabled", False)),
        base_url=str(_deep_get(data, "sonar.base_url", "") or os.environ.get("SONAR_BASE_URL", "")),
        token=str(_deep_get(data, "sonar.token", "") or os.environ.get("SONAR_TOKEN", "")),
        organization=str(_deep_get(data, "sonar.organization", "") or os.environ.get("SONAR_ORGANIZATION", "")),
        project_key=str(_deep_get(data, "sonar.project_key", "") or os.environ.get("SONAR_PROJECT_KEY", "")),
        timeout_seconds=float(_deep_get(data, "sonar.timeout_seconds", 30)),
        verify_ssl=bool(_deep_get(data, "sonar.verify_ssl", True)),
    )

    try:
        inputs_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback_work = (Path.cwd().resolve() / "work")
        work_dir = fallback_work
        inputs_dir = fallback_work / "inputs"
        outputs_dir = fallback_work / "outputs"
        meta_dir = fallback_work / "meta"
        inputs_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        meta_dir.mkdir(parents=True, exist_ok=True)

    paths = PathsConfig(work_dir=work_dir, inputs_dir=inputs_dir, outputs_dir=outputs_dir, meta_dir=meta_dir)

    return AppConfig(paths=paths, llm=llm, jenkins=jenkins, sonar=sonar)
