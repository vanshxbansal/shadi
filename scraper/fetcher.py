import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

import requests

import config
from scraper.pagination import get_total_pages


def session_cookies(session: requests.Session) -> dict[str, str]:
    return {cookie.name: cookie.value for cookie in session.cookies}


def create_session_from_cookies(cookies: dict[str, str]) -> requests.Session:
    session = requests.Session()
    session.headers.update(config.BROWSER_HEADERS)
    for name, value in cookies.items():
        session.cookies.set(name, value, domain="www.aspv.in")
    return session


def fetch_page(
    session: requests.Session,
    page: int,
    retries: int = config.MAX_RETRIES,
) -> str:
    url = f"{config.VIVAH_URL}?page={page}&"
    headers = {**config.BROWSER_HEADERS, "referer": config.VIVAH_URL}

    last_error: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = session.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            if "Registration No." not in resp.text and "pagination" not in resp.text:
                raise ValueError(f"Unexpected response for page {page}")
            return resp.text
        except Exception as exc:
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch page {page}: {last_error}")


def _fetch_page_task(cookies: dict[str, str], page: int) -> tuple[int, str]:
    session = create_session_from_cookies(cookies)
    return page, fetch_page(session, page)


def fetch_all_pages(
    session: requests.Session,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    cache_html: bool = True,
    workers: Optional[int] = None,
) -> list[str]:
    worker_count = workers or config.CONCURRENT_WORKERS
    first_html = fetch_page(session, 1)
    total_pages = get_total_pages(first_html)
    page_html: dict[int, str] = {1: first_html}
    cookies = session_cookies(session)

    if cache_html:
        config.ensure_dirs()
        (config.HTML_DIR / "page_1.html").write_text(first_html, encoding="utf-8")

    completed = 1
    progress_lock = threading.Lock()

    def report(page: int):
        nonlocal completed
        with progress_lock:
            completed += 1
            if on_progress:
                on_progress(
                    completed,
                    total_pages,
                    f"Fetched page {page} ({completed}/{total_pages})",
                )

    if on_progress:
        on_progress(1, total_pages, "Fetched page 1 (1/{0})".format(total_pages))

    if total_pages > 1:
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_fetch_page_task, cookies, page): page
                for page in range(2, total_pages + 1)
            }
            for future in as_completed(futures):
                page, html = future.result()
                page_html[page] = html
                if cache_html:
                    (config.HTML_DIR / f"page_{page}.html").write_text(html, encoding="utf-8")
                report(page)

    return [page_html[page] for page in range(1, total_pages + 1)]
