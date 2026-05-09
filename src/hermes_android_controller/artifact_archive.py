"""Run artifact archiving for OA approval automation."""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import time
from pathlib import Path
from typing import Mapping


RETENTION_DAYS = 15
DEFAULT_STATE_DIR = Path("var/oa_approval")


def archive_payload(kind: str, payload: Mapping[str, object], *, now: dt.datetime | None = None) -> dict[str, object]:
    current = now or dt.datetime.now()
    run_id = f"{kind}-{current.strftime('%Y%m%d-%H%M%S')}"
    run_dir = runs_dir() / run_id
    artifacts_dir = run_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    payload_path = run_dir / "payload.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts = collect_artifacts(payload, artifacts_dir)
    artifacts_path = run_dir / "artifacts.json"
    artifacts_path.write_text(json.dumps(artifacts, ensure_ascii=False, indent=2), encoding="utf-8")
    removed = prune_old_runs()
    return {
        "ok": True,
        "kind": kind,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "payload_path": str(payload_path),
        "artifact_count": len(artifacts),
        "removed_old_runs": removed,
    }


def collect_artifacts(value: object, dest_dir: Path) -> list[dict[str, str]]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, str]] = []
    for source in _iter_artifact_paths(value):
        path = Path(source)
        if not path.exists() or not path.is_file():
            continue
        target = _unique_target(dest_dir, path.name)
        shutil.copy2(path, target)
        copied.append({"source": str(path), "stored": str(target)})
    return copied


def prune_old_runs(retention_days: int = RETENTION_DAYS) -> list[str]:
    cutoff = time.time() - retention_days * 86400
    removed = []
    root = runs_dir()
    if not root.exists():
        return removed
    for child in root.iterdir():
        if not child.is_dir() or child.stat().st_mtime >= cutoff:
            continue
        shutil.rmtree(child)
        removed.append(str(child))
    return removed


def state_dir() -> Path:
    return Path(os.getenv("OA_APPROVAL_STATE_DIR", str(DEFAULT_STATE_DIR)))


def runs_dir() -> Path:
    return state_dir() / "runs"


def _iter_artifact_paths(value: object):
    keys = {
        "xml_path",
        "screenshot_path",
        "last_xml_path",
        "last_screenshot_path",
        "before_xml_path",
        "before_screenshot_path",
        "after_xml_path",
        "after_screenshot_path",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in keys and isinstance(item, str):
                yield item
            else:
                yield from _iter_artifact_paths(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_artifact_paths(item)


def _unique_target(dest_dir: Path, name: str) -> Path:
    target = dest_dir / name
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    counter = 2
    while True:
        candidate = dest_dir / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
