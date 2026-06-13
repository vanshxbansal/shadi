from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "config.json"
SESSION_FILE = DATA_DIR / "session.json"
HTML_DIR = DATA_DIR / "html"
EXPORTS_DIR = DATA_DIR / "exports"
SUMMARIES_DIR = DATA_DIR / "summaries"

LOGIN_URL = "https://www.aspv.in/login.php"
VIVAH_URL = "https://www.aspv.in/vivahsamiti.php"

PAGE_DELAY_SECONDS = 0.6
CONCURRENT_WORKERS = 10
MAX_RETRIES = 3
REQUEST_TIMEOUT = 60

BROWSER_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.9",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    ),
    "upgrade-insecure-requests": "1",
}

COLUMN_ORDER = [
    "profile_id",
    "registration_no",
    "registration_date",
    "name",
    "date_of_birth",
    "time_of_birth",
    "place_of_birth",
    "gender",
    "marital_status",
    "sub_caste_gotra",
    "manglik",
    "height",
    "weight",
    "complexion",
    "body_structure",
    "use_glass",
    "physical_disability",
    "monthly_income",
    "annual_income",
    "work_status",
    "state",
    "fathers_name",
    "fathers_occupation",
    "annual_family_income",
    "native_place",
    "education",
    "marriage_budget",
    "express_yourself",
    "express_your_family",
    "married_brothers",
    "unmarried_brothers",
    "married_sisters",
    "unmarried_sisters",
    "liking_of_boy_girl",
    "location",
    "phone_number",
]


def ensure_dirs():
    for path in (DATA_DIR, HTML_DIR, EXPORTS_DIR, SUMMARIES_DIR):
        path.mkdir(parents=True, exist_ok=True)
