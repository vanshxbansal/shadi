import threading
import uuid
from typing import Any, Callable, Optional

from scraper.fetcher import fetch_all_pages
from scraper.parser import parse_profiles_from_pages
from scraper.session import create_session, ensure_authenticated, load_config
from services.excel import export_scrape_results


class JobManager:
    def __init__(self):
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, job_id: str) -> Optional[dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def start_scrape(self) -> str:
        job_id = str(uuid.uuid4())
        with self._lock:
            self._jobs[job_id] = {
                "id": job_id,
                "status": "queued",
                "progress": 0,
                "message": "Starting...",
                "logs": [],
                "result": None,
                "error": None,
            }

        thread = threading.Thread(target=self._run_scrape, args=(job_id,), daemon=True)
        thread.start()
        return job_id

    def _update(self, job_id: str, **kwargs):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(kwargs)

    def _append_log(self, job_id: str, message: str):
        with self._lock:
            if job_id in self._jobs:
                logs = self._jobs[job_id].setdefault("logs", [])
                logs.append(message)
                if len(logs) > 200:
                    self._jobs[job_id]["logs"] = logs[-200:]

    def _run_scrape(self, job_id: str):
        try:
            self._update(job_id, status="logging_in", message="Logging in...", progress=0)
            session = create_session()
            ok, msg = ensure_authenticated(session)
            if not ok:
                raise RuntimeError(msg)
            self._append_log(job_id, msg)

            cfg = load_config()

            def on_fetch_progress(current: int, total: int, message: str):
                pct = int((current / total) * 70) if total else 0
                self._update(
                    job_id,
                    status="fetching",
                    progress=pct,
                    message=f"Fetching pages {current}/{total} (parallel)",
                )
                if current == 1 or current == total or current % 10 == 0:
                    self._append_log(job_id, message)

            self._update(job_id, status="fetching", message="Fetching pages...", progress=1)
            pages = fetch_all_pages(session, on_progress=on_fetch_progress)

            self._update(job_id, status="parsing", message="Parsing biodata...", progress=75)
            records = parse_profiles_from_pages(pages)
            self._append_log(job_id, f"Parsed {len(records)} profiles")

            self._update(job_id, status="comparing", message="Comparing with baseline...", progress=85)
            summary = export_scrape_results(
                records,
                baseline_file=cfg.get("baseline_file", ""),
                pages_fetched=len(pages),
            )
            self._append_log(
                job_id,
                f"Found {summary['new_count']} new profiles (baseline: {summary['baseline_count']})",
            )

            self._update(
                job_id,
                status="done",
                progress=100,
                message="Scrape complete",
                result={
                    "summary": summary,
                    "new_preview": self._preview_records(records, summary),
                },
            )
        except Exception as exc:
            self._update(
                job_id,
                status="error",
                message=str(exc),
                error=str(exc),
            )

    def _preview_records(self, all_records: list[dict], summary: dict) -> list[dict]:
        from services.excel import find_new_records, get_baseline_path, read_excel

        baseline_path = get_baseline_path(summary.get("baseline_file") or "")
        baseline = read_excel(baseline_path) if baseline_path else []
        new_records = find_new_records(all_records, baseline)
        preview_cols = ["registration_no", "name", "gender", "date_of_birth", "phone_number", "location"]
        preview = []
        for row in new_records[:50]:
            preview.append({col: row.get(col, "") for col in preview_cols})
        return preview


job_manager = JobManager()
