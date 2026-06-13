import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import config
from bs4 import BeautifulSoup, Tag

LABEL_MAP = {
    "registration no.": "registration_no",
    "registration date": "registration_date",
    "name": "name",
    "date of birth": "date_of_birth",
    "time-of-birth": "time_of_birth",
    "place of birth": "place_of_birth",
    "gender": "gender",
    "marital status": "marital_status",
    "sub caste/gotra": "sub_caste_gotra",
    "manglik": "manglik",
    "height": "height",
    "weight": "weight",
    "complexion": "complexion",
    "body structure": "body_structure",
    "use glass": "use_glass",
    "physicl disability": "physical_disability",
    "monthly income": "monthly_income",
    "annual income": "annual_income",
    "work status": "work_status",
    "state": "state",
    "father's name": "fathers_name",
    "father's occupation": "fathers_occupation",
    "annual family income": "annual_family_income",
    "native place": "native_place",
    "education": "education",
    "marriage budget": "marriage_budget",
    "express yourself": "express_yourself",
    "express your family": "express_your_family",
    "married brothers": "married_brothers",
    "unmarried brothers": "unmarried_brothers",
    "married sisters": "married_sisters",
    "unmarried sisters": "unmarried_sisters",
    "liking of boy/girl": "liking_of_boy_girl",
    "location": "location",
    "phone number": "phone_number",
}


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def _normalize_label(label: str) -> str:
    label = _clean_text(label).lower().rstrip(":").strip()
    return LABEL_MAP.get(label, "")


def _cell_text(cell: Optional[Tag]) -> str:
    if cell is None:
        return ""
    return _clean_text(cell.get_text(" ", strip=True))


def _extract_profile_id(table: Tag) -> str:
    html = str(table)
    match = re.search(r"getElementById\('(\d+)'\)", html)
    return match.group(1) if match else ""


def _parse_profile_table(table: Tag) -> dict[str, Any]:
    record: dict[str, Any] = {"profile_id": _extract_profile_id(table)}

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        if len(cells) >= 4:
            pairs = [(cells[0], cells[1]), (cells[2], cells[3])]
        else:
            pairs = [(cells[0], cells[1])]

        for label_cell, value_cell in pairs:
            key = _normalize_label(_cell_text(label_cell))
            if not key:
                continue
            if key == "express_yourself" and record.get("express_yourself"):
                continue
            record[key] = _cell_text(value_cell)

    return record


def parse_profiles_from_html(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    profiles: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for table in soup.find_all("table"):
        style = table.get("style", "")
        if "d99e00" not in style:
            continue
        if "Registration No." not in table.get_text():
            continue
        record = _parse_profile_table(table)
        if not record.get("registration_no") and not record.get("profile_id"):
            continue
        dedupe_key = record.get("profile_id") or record.get("registration_no", "")
        if dedupe_key in seen_ids:
            continue
        seen_ids.add(dedupe_key)
        profiles.append(record)

    return profiles


def parse_profiles_from_pages(pages: list[str]) -> list[dict[str, Any]]:
    if not pages:
        return []

    workers = min(config.CONCURRENT_WORKERS, len(pages))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        page_results = list(executor.map(parse_profiles_from_html, pages))

    all_profiles: list[dict[str, Any]] = []
    seen: set[str] = set()

    for records in page_results:
        for record in records:
            key = record.get("profile_id") or record.get("registration_no", "")
            if key in seen:
                continue
            seen.add(key)
            all_profiles.append(record)

    return all_profiles
