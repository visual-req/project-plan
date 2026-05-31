from __future__ import annotations

from pathlib import Path
from typing import Any

from .app_config import AppConfig
from .storage import atomic_write_json, read_json


def estimation_standards_path(config: AppConfig) -> Path:
    return config.paths.meta_dir / "estimation_standards.json"


def load_estimation_standards(config: AppConfig) -> dict[str, Any]:
    path = estimation_standards_path(config)
    data = read_json(path)
    if isinstance(data, dict):
        if "types" in data and "matrix" in data:
            return data
        if "complexity" in data and isinstance(data.get("complexity"), list):
            migrated = _migrate_old_schema(data)
            config.paths.meta_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_json(path, migrated)
            return migrated

    default = _default_estimation_standards()
    config.paths.meta_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, default)
    return default


def save_estimation_standards(config: AppConfig, data: dict[str, Any]) -> dict[str, Any]:
    path = estimation_standards_path(config)
    config.paths.meta_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, data)
    return data


def _default_complexity_rows() -> list[dict[str, Any]]:
    return [
        {"key": "S", "dev_days": 1.0, "test_days": 0.5, "pm_days": 0.5},
        {"key": "M", "dev_days": 2.0, "test_days": 1.0, "pm_days": 0.5},
        {"key": "L", "dev_days": 4.0, "test_days": 2.0, "pm_days": 1.0},
        {"key": "XL", "dev_days": 7.0, "test_days": 3.0, "pm_days": 1.5},
    ]


def _default_types() -> list[dict[str, Any]]:
    return [
        {"key": "crud", "label": "CRUD"},
        {"key": "import_export", "label": "文件导入导出"},
        {"key": "scheduler", "label": "定时任务"},
        {"key": "reporting", "label": "报表展示"},
        {"key": "business_rules", "label": "业务规则/校验"},
        {"key": "calculation_engine", "label": "复杂计算/计费"},
        {"key": "data_processing", "label": "数据处理/聚合"},
        {"key": "auth_permission", "label": "登录与权限"},
        {"key": "integration_api", "label": "外部接口/第三方集成"},
        {"key": "notification", "label": "消息通知"},
        {"key": "workflow", "label": "流程/审批/状态机"},
        {"key": "search", "label": "搜索与筛选"},
        {"key": "data_migration", "label": "数据迁移/初始化"},
        {"key": "performance_cache", "label": "性能优化/缓存"},
        {"key": "devops", "label": "部署/配置/CI-CD"},
        {"key": "monitoring_logging", "label": "日志/监控/告警"},
    ]


def _default_estimation_standards() -> dict[str, Any]:
    types = _default_types()
    matrix: dict[str, Any] = {}
    base = _default_complexity_rows()
    for t in types:
        matrix[t["key"]] = [dict(x) for x in base]
    return {
        "types": types,
        "matrix": matrix,
        "rule": {"day_increment": 0.5},
    }


def _migrate_old_schema(old: dict[str, Any]) -> dict[str, Any]:
    types = _default_types()
    matrix: dict[str, Any] = {}
    base = old.get("complexity")
    base_rows = base if isinstance(base, list) else _default_complexity_rows()
    for t in types:
        matrix[t["key"]] = [dict(x) for x in base_rows]
    rule = old.get("rule") if isinstance(old.get("rule"), dict) else {"day_increment": 0.5}
    return {
        "types": types,
        "matrix": matrix,
        "rule": rule,
    }
