from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

from backend.adapters.sqlite_catalog import SqliteCatalog


@dataclass
class Candidate:
    run_id: str
    created_at: str
    dir_path: Path
    size_bytes: int


def _parse_dt(s: str) -> datetime:
    # Accept ISO with or without Z
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.now(timezone.utc)


def _dir_size(p: Path) -> int:
    total = 0
    if not p.exists():
        return 0
    for root, _dirs, files in os.walk(p):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
            except Exception:
                pass
    return total


def select_candidates(*, keep_latest: int, max_age_days: Optional[int]) -> Tuple[List[Candidate], List[str]]:
    cat = SqliteCatalog()
    # Order all runs by created_at DESC
    with cat._connect() as conn:  # type: ignore[attr-defined]
        rows = conn.execute(
            "SELECT run_id, created_at FROM runs ORDER BY datetime(created_at) DESC"
        ).fetchall()
    run_ids_ordered = [r[0] for r in rows]
    kept = set(run_ids_ordered[: max(0, keep_latest)])

    # Max age filter
    cutoff = None
    if max_age_days and max_age_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)

    data_root = Path(os.environ.get("HEWSTON_DATA_DIR", "data")) / "backtests"

    cands: List[Candidate] = []
    kept_list: List[str] = []
    for run_id, created_at in rows:
        if run_id in kept:
            kept_list.append(run_id)
            continue
        if cutoff is not None and _parse_dt(created_at) > cutoff:
            # recent enough: keep
            kept_list.append(run_id)
            continue
        d = data_root / run_id
        size = _dir_size(d)
        cands.append(Candidate(run_id=run_id, created_at=created_at, dir_path=d, size_bytes=size))
    return cands, kept_list


def apply_deletions(cands: List[Candidate]) -> Tuple[int, int]:
    """Delete artifact dirs and remove DB rows. Returns (count, bytes)."""
    cat = SqliteCatalog()
    deleted = 0
    bytes_reclaimed = 0
    for c in cands:
        # Remove files first; if fails, skip DB delete
        try:
            if c.dir_path.exists():
                shutil.rmtree(c.dir_path)
        except Exception:
            # Skip DB delete; leave for remediation
            continue
        try:
            with cat._connect() as conn:  # type: ignore[attr-defined]
                conn.execute("DELETE FROM run_metrics WHERE run_id = ?", (c.run_id,))
                conn.execute("DELETE FROM runs WHERE run_id = ?", (c.run_id,))
                conn.commit()
        except Exception:
            # Best-effort: files are gone; log/skip DB error
            pass
        deleted += 1
        bytes_reclaimed += c.size_bytes
    return deleted, bytes_reclaimed


# Typer CLI
try:
    import typer  # type: ignore
except Exception:  # pragma: no cover
    typer = None  # type: ignore


def retention_main(keep_latest: int = 100, max_age_days: Optional[int] = None, apply: bool = False) -> int:
    cands, kept = select_candidates(keep_latest=keep_latest, max_age_days=max_age_days)
    summary: dict[str, Any] = {
        "keep_latest": keep_latest,
        "max_age_days": max_age_days,
        "candidates": [
            {"run_id": c.run_id, "created_at": c.created_at, "dir": str(c.dir_path), "size_bytes": c.size_bytes}
            for c in cands
        ],
        "kept": kept,
        "would_delete_count": len(cands),
        "would_reclaim_bytes": sum(c.size_bytes for c in cands),
        "apply": apply,
    }
    print(json.dumps(summary, indent=2))
    if apply and cands:
        deleted, reclaimed = apply_deletions(cands)
        print(json.dumps({"deleted": deleted, "reclaimed_bytes": reclaimed}))
    elif not apply and cands:
        print("[retention] Refusing to delete without --apply")
    return 0


if typer is not None:
    app = typer.Typer(no_args_is_help=True, add_completion=False)

    @app.command(name="retention")
    def retention_cmd(
        keep_latest: int = typer.Option(100, "--keep-latest"),
        max_age_days: Optional[int] = typer.Option(None, "--max-age", help="Days; if set, delete older than this (except latest N)"),
        apply: bool = typer.Option(False, "--apply", help="Actually delete files and DB rows"),
    ) -> None:
        raise typer.Exit(retention_main(keep_latest=keep_latest, max_age_days=max_age_days, apply=apply))

