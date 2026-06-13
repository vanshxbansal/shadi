import json
import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

import config
from scraper.fetcher import fetch_page
from scraper.pagination import get_total_pages
from scraper.parser import parse_profiles_from_html
from scraper.session import create_session, ensure_authenticated, load_config, save_config
from services.excel import list_exports
from services.jobs import job_manager

app = Flask(__name__)
config.ensure_dirs()


def _seed_config_from_env():
    """Persist env credentials to disk so they survive within a running instance."""
    mobile = os.environ.get("MOBILE", "").strip()
    phpsessid = os.environ.get("PHPSESSID", "").strip()
    if not mobile and not phpsessid:
        return

    if config.CONFIG_FILE.exists():
        with open(config.CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    updates = {}
    if mobile and not (data.get("mobile") or "").strip():
        updates["mobile"] = mobile
    if phpsessid and not (data.get("phpsessid") or "").strip():
        updates["phpsessid"] = phpsessid
    if updates:
        save_config(**updates)


_seed_config_from_env()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/settings")
def settings_page():
    cfg = load_config()
    return render_template("settings.html", config=cfg)


@app.route("/history")
def history_page():
    return render_template("history.html", exports=list_exports(), config=load_config())


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "GET":
        cfg = load_config()
        return jsonify(cfg)

    data = request.get_json(silent=True) or {}
    cfg = save_config(
        mobile=data.get("mobile"),
        phpsessid=data.get("phpsessid"),
        baseline_file=data.get("baseline_file"),
    )
    return jsonify({"ok": True, "config": cfg})


@app.route("/api/test-login", methods=["POST"])
def api_test_login():
    session = create_session()
    ok, msg = ensure_authenticated(session)
    if not ok:
        return jsonify({"ok": False, "message": msg}), 400

    html = fetch_page(session, 1)
    total_pages = get_total_pages(html)
    profiles = parse_profiles_from_html(html)

    return jsonify(
        {
            "ok": True,
            "message": msg,
            "total_pages": total_pages,
            "profiles_on_page_1": len(profiles),
            "sample": profiles[0] if profiles else None,
        }
    )


@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    cfg = load_config()
    if not cfg.get("mobile") and not cfg.get("phpsessid"):
        return jsonify({"ok": False, "error": "Set mobile number or PHPSESSID in Settings first."}), 400
    job_id = job_manager.start_scrape()
    return jsonify({"ok": True, "job_id": job_id})


@app.route("/api/jobs/<job_id>")
def api_job_status(job_id):
    job = job_manager.get(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Job not found"}), 404
    return jsonify({"ok": True, "job": job})


@app.route("/api/exports")
def api_exports():
    return jsonify({"ok": True, "exports": list_exports()})


@app.route("/api/exports/<filename>")
def api_download_export(filename):
    safe_name = Path(filename).name
    if not safe_name.endswith(".xlsx"):
        return jsonify({"ok": False, "error": "Invalid file"}), 400
    return send_from_directory(config.EXPORTS_DIR, safe_name, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
