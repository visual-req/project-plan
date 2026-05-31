from __future__ import annotations

import argparse
import json
import os
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .app_config import AppConfig, load_config
from .doc_parser import extract_text_from_docx
from .meta_service import load_estimation_standards, save_estimation_standards
from .services.decompose_service import run as run_decompose
from .services.estimate_service import run as run_estimate
from .services.schedule_service import run as run_schedule
from .storage import atomic_write_text


def _load_config_from_env_or_args() -> AppConfig:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", dest="config_path", default=None)
    args, _ = parser.parse_known_args()
    config_path = args.config_path or os.environ.get("PROJECT_PLAN_CONFIG")
    return load_config(config_path)


CONFIG = _load_config_from_env_or_args()


app = FastAPI(title="Project Plan Analyzer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DocRequest(BaseModel):
    doc_id: str
    lang: str | None = None


def _lang_key(lang: str | None) -> str:
    if not lang:
        return "zh"
    low = lang.lower()
    if low.startswith("zh"):
        return "zh"
    if low.startswith("ja") or low.startswith("jp"):
        return "ja"
    if low.startswith("en"):
        return "en"
    return "zh"


def _doc_dir(doc_id: str) -> Path:
    return CONFIG.paths.outputs_dir / doc_id


def _paths_for_doc(doc_id: str, lang: str | None = None) -> dict[str, Path]:
    lang_key = _lang_key(lang)
    out_dir = _doc_dir(doc_id)
    return {
        "out_dir": out_dir,
        "uploaded_docx": CONFIG.paths.inputs_dir / f"{doc_id}.docx",
        "requirement_text": out_dir / "requirement.txt",
        "decompose_json": out_dir / f"decompose.{lang_key}.json",
        "schedule_json": out_dir / f"schedule.{lang_key}.json",
        "estimate_json": out_dir / f"estimate.{lang_key}.json",
        "llm_raw_decompose": out_dir / f"decompose.{lang_key}.raw.txt",
        "llm_raw_schedule": out_dir / f"schedule.{lang_key}.raw.txt",
        "llm_raw_estimate": out_dir / f"estimate.{lang_key}.raw.txt",
    }


def _load_requirement_text(doc_id: str) -> str:
    p = _paths_for_doc(doc_id)["requirement_text"]
    if not p.exists():
        raise HTTPException(status_code=404, detail="Requirement text not found, upload first")
    return p.read_text(encoding="utf-8")


def _to_http_exception(e: Exception) -> HTTPException:
    if isinstance(e, HTTPException):
        return e
    if isinstance(e, httpx.HTTPError):
        return HTTPException(status_code=502, detail=f"大模型调用失败：{e}")
    if isinstance(e, (json.JSONDecodeError, ValueError)):
        return HTTPException(status_code=502, detail=f"大模型输出解析失败：{e}")
    msg = str(e)
    if "LLM" in msg or "chat/completions" in msg:
        return HTTPException(status_code=502, detail=f"大模型调用失败：{msg}")
    return HTTPException(status_code=500, detail=msg or "Internal Server Error")



async def _ensure_decompose(doc_id: str, lang: str | None) -> dict[str, Any]:
    requirement_text = _load_requirement_text(doc_id)
    paths = _paths_for_doc(doc_id, lang)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "ok": True,
        "llm_enabled": CONFIG.llm.enabled,
        "inputs_dir": str(CONFIG.paths.inputs_dir),
        "outputs_dir": str(CONFIG.paths.outputs_dir),
        "meta_dir": str(CONFIG.paths.meta_dir),
    }


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx is supported")

    CONFIG.paths.inputs_dir.mkdir(parents=True, exist_ok=True)
    CONFIG.paths.outputs_dir.mkdir(parents=True, exist_ok=True)

    while True:
        doc_id = datetime.now().strftime("%Y%m%d%H%M%S")
        paths = _paths_for_doc(doc_id)
        if not paths["out_dir"].exists():
            break
        await asyncio.sleep(1)

    paths["out_dir"].mkdir(parents=True, exist_ok=True)

    content = await file.read()
    paths["uploaded_docx"].write_bytes(content)

    try:
        text = extract_text_from_docx(paths["uploaded_docx"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse docx: {e}") from e

    if not text:
        raise HTTPException(status_code=400, detail="Empty docx content")

    atomic_write_text(paths["requirement_text"], text)
    return {"doc_id": doc_id, "filename": file.filename}


@app.post("/api/decompose")
async def decompose(req: DocRequest) -> JSONResponse:
    try:
        data = await _ensure_decompose(req.doc_id, req.lang)
        return JSONResponse(content=data)
    except Exception as e:
        raise _to_http_exception(e) from e


@app.post("/api/schedule")
async def schedule(req: DocRequest) -> JSONResponse:
    try:
        requirement_text = _load_requirement_text(req.doc_id)
        paths = _paths_for_doc(req.doc_id, req.lang)
        decompose_data = await _ensure_decompose(req.doc_id, req.lang)
        stories_json = Path(paths["decompose_json"]).read_text(encoding="utf-8")
        data = await run_schedule(CONFIG, requirement_text, stories_json, decompose_data, paths, req.lang)
        return JSONResponse(content=data)
    except Exception as e:
        raise _to_http_exception(e) from e


@app.post("/api/estimate")
async def estimate(req: DocRequest) -> JSONResponse:
    try:
        requirement_text = _load_requirement_text(req.doc_id)
        paths = _paths_for_doc(req.doc_id, req.lang)
        decompose_data = await _ensure_decompose(req.doc_id, req.lang)
        stories_json = Path(paths["decompose_json"]).read_text(encoding="utf-8")
        data = await run_estimate(CONFIG, requirement_text, stories_json, decompose_data, paths, req.lang)
        return JSONResponse(content=data)
    except Exception as e:
        raise _to_http_exception(e) from e


@app.get("/api/artifacts/{doc_id}/{name}")
async def artifacts(doc_id: str, name: str, lang: str | None = None) -> FileResponse:
    paths = _paths_for_doc(doc_id, lang)
    allowed = {
        "requirement.txt": paths["requirement_text"],
        "decompose.json": paths["decompose_json"],
        "schedule.json": paths["schedule_json"],
        "estimate.json": paths["estimate_json"],
    }
    if name not in allowed:
        raise HTTPException(status_code=404, detail="Artifact not found")
    p = allowed[name]
    if not p.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(str(p))


@app.get("/api/meta/estimation-standards")
async def get_estimation_standards() -> JSONResponse:
    return JSONResponse(content=load_estimation_standards(CONFIG))


@app.post("/api/meta/estimation-standards")
async def post_estimation_standards(payload: dict[str, Any]) -> JSONResponse:
    data = save_estimation_standards(CONFIG, payload)
    return JSONResponse(content=data)


FRONTEND_DIR = (Path(__file__).resolve().parent.parent / "frontend").resolve()
PUBLIC_DIR = (FRONTEND_DIR / "public").resolve()
SRC_DIR = (FRONTEND_DIR / "src").resolve()

if FRONTEND_DIR.exists():
    class NoCacheStaticFiles(StaticFiles):
        async def get_response(self, path: str, scope):  # type: ignore[override]
            resp = await super().get_response(path, scope)
            resp.headers["Cache-Control"] = "no-store"
            resp.headers["Pragma"] = "no-cache"
            resp.headers["Expires"] = "0"
            return resp

    if SRC_DIR.exists():
        app.mount("/src", NoCacheStaticFiles(directory=str(SRC_DIR), html=False), name="frontend-src")
    if PUBLIC_DIR.exists():
        app.mount("/", NoCacheStaticFiles(directory=str(PUBLIC_DIR), html=True), name="frontend")
