import json
import os
from typing import Optional

import requests

import config


def load_config() -> dict:
    if config.CONFIG_FILE.exists():
        with open(config.CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    return {
        "mobile": (data.get("mobile") or os.environ.get("MOBILE", "")).strip(),
        "phpsessid": (data.get("phpsessid") or os.environ.get("PHPSESSID", "")).strip(),
        "baseline_file": (data.get("baseline_file") or os.environ.get("BASELINE_FILE", "")).strip(),
    }


def save_config(
    mobile: Optional[str] = None,
    phpsessid: Optional[str] = None,
    baseline_file: Optional[str] = None,
) -> dict:
    config.ensure_dirs()
    current = load_config()
    if mobile is not None:
        current["mobile"] = mobile.strip()
    if phpsessid is not None:
        current["phpsessid"] = phpsessid.strip()
    if baseline_file is not None:
        current["baseline_file"] = baseline_file.strip()
    with open(config.CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return current


def save_session_cookies(session: requests.Session) -> None:
    config.ensure_dirs()
    cookies = {c.name: c.value for c in session.cookies}
    with open(config.SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)


def load_session_cookies(session: requests.Session) -> None:
    if not config.SESSION_FILE.exists():
        return
    with open(config.SESSION_FILE, encoding="utf-8") as f:
        cookies = json.load(f)
    for name, value in cookies.items():
        session.cookies.set(name, value, domain="www.aspv.in")


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(config.BROWSER_HEADERS)
    load_session_cookies(session)
    cfg = load_config()
    if cfg.get("phpsessid"):
        session.cookies.set("PHPSESSID", cfg["phpsessid"], domain="www.aspv.in")
    return session


def login(session: requests.Session, mobile: str) -> bool:
    session.get(config.LOGIN_URL, timeout=config.REQUEST_TIMEOUT)
    resp = session.post(
        config.LOGIN_URL,
        files={"password": (None, mobile), "submit": (None, "Submit")},
        headers={
            **config.BROWSER_HEADERS,
            "referer": config.LOGIN_URL,
            "origin": "https://www.aspv.in",
        },
        allow_redirects=False,
        timeout=config.REQUEST_TIMEOUT,
    )
    location = resp.headers.get("location", "")
    success = resp.status_code == 302 and "vivahsamiti" in location.lower()
    if success:
        save_session_cookies(session)
    return success


def ensure_authenticated(session: requests.Session) -> tuple[bool, str]:
    cfg = load_config()
    mobile = cfg.get("mobile", "").strip()
    phpsessid = cfg.get("phpsessid", "").strip()

    if mobile:
        if login(session, mobile):
            return True, "Logged in successfully"
        if phpsessid:
            session.cookies.set("PHPSESSID", phpsessid, domain="www.aspv.in")
        else:
            return False, "Login failed. Check mobile number in Settings."

    if phpsessid:
        session.cookies.set("PHPSESSID", phpsessid, domain="www.aspv.in")

    test = session.get(
        f"{config.VIVAH_URL}?page=1",
        headers={**config.BROWSER_HEADERS, "referer": config.VIVAH_URL},
        timeout=config.REQUEST_TIMEOUT,
    )
    if test.status_code != 200 or "Registration No." not in test.text:
        return False, "Session invalid. Set mobile number or PHPSESSID in Settings."
    save_session_cookies(session)
    return True, "Session is valid"
