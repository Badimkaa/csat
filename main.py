import secrets
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import threading
import time
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta
from pathlib import Path

# Get app directory and ensure directories exist
APP_DIR = Path(__file__).parent
DATA_DIR = Path(os.environ.get("CSAT_DATA_DIR", "/var/lib/csat"))
LOG_DIR = Path(os.environ.get("CSAT_LOG_DIR", "/var/log/csat"))

# Create directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging with automatic rotation
log_file = LOG_DIR / "app.log"
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Timed rotating file handler: rotates daily at midnight, keeps 7 days of backups
file_handler = TimedRotatingFileHandler(
    filename=str(log_file),
    when='midnight',
    interval=1,
    backupCount=7,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)

# Stream handler for console output
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, stream_handler]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load surveys from disk
    load_surveys()
    # Clean up any expired surveys from the previous session
    cleanup_expired_surveys()
    yield
    # Shutdown: Save surveys to disk
    save_surveys()
 
app = FastAPI(lifespan=lifespan)

# CORS configuration - restrict to specific domains in production
ALLOWED_ORIGINS = os.environ.get("CSAT_ALLOWED_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

pending_surveys = {}  # token: {"issue_key": str, "is_used": bool, "language": str, "created_at": datetime}
surveys_lock = threading.Lock()
SURVEY_EXPIRY_HOURS = int(os.environ.get("CSAT_SURVEY_EXPIRY_HOURS", "24"))
SURVEYS_FILE = DATA_DIR / "surveys.json"

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
# r
def save_surveys():
    """Persist pending_surveys to a JSON file with atomic writes"""
    try:
        with surveys_lock:
            # Convert datetime objects to ISO format strings for JSON serialization
            surveys_to_save = {}
            for token, survey in pending_surveys.items():
                surveys_to_save[token] = {
                    "issue_key": survey["issue_key"],
                    "is_used": survey["is_used"],
                    "language": survey["language"],
                    "created_at": survey["created_at"].isoformat()
                }
            # Write to temporary file first, then atomically rename
            # This prevents file corruption if write is interrupted
            temp_file = SURVEYS_FILE.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(surveys_to_save, f)
            temp_file.replace(SURVEYS_FILE)  # Atomic operation on most filesystems
    except Exception as e:
        logger.error(f"Error saving surveys: {e}")

def load_surveys():
    """Load pending_surveys from JSON file at startup"""
    global pending_surveys
    try:
        if SURVEYS_FILE.exists():
            with open(SURVEYS_FILE, 'r') as f:
                surveys_data = json.load(f)
                for token, survey in surveys_data.items():
                    pending_surveys[token] = {
                        "issue_key": survey["issue_key"],
                        "is_used": survey["is_used"],
                        "language": survey["language"],
                        "created_at": datetime.fromisoformat(survey["created_at"])
                    }
            logger.info(f"Loaded {len(pending_surveys)} surveys from disk")
        else:
            logger.info(f"Starting with no surveys on disk")
    except Exception as e:
        logger.error(f"Error loading surveys: {e}", exc_info=True)
        pending_surveys = {}

def cleanup_expired_surveys():
    """Remove surveys that are older than SURVEY_EXPIRY_HOURS or already used"""
    with surveys_lock:
        now = datetime.now()
        expired_tokens = [
            token for token, survey in pending_surveys.items()
            if now - survey["created_at"] > timedelta(hours=SURVEY_EXPIRY_HOURS) or survey["is_used"]
        ]
        for token in expired_tokens:
            del pending_surveys[token]
    if expired_tokens:
        save_surveys()

@app.post("/survey/create")
def create_survey(issue_key: str = Form(...), language: str = Form('en')):
    cleanup_expired_surveys()
    token = secrets.token_urlsafe(16)
    with surveys_lock:
        pending_surveys[token] = {
            "issue_key": issue_key,
            "is_used": False,
            "language": language,
            "created_at": datetime.now()
        }
    save_surveys()

    # Determine domain based on language
    domain = "survey.ostrovok.ru" if language == "ru" else "survey.emergingtravel.com"
    return {"link": f"https://{domain}/survey/{token}"}

@app.get("/survey/{token}", response_class=HTMLResponse)
def get_survey(token: str, request: Request, lang: str = Query(None)):
    # Copy survey data inside lock to prevent race condition
    # where survey might be deleted by cleanup_expired_surveys
    survey_data = None
    with surveys_lock:
        survey = pending_surveys.get(token)

        # If token not found in memory, it might have been created by another worker
        # Reload surveys from disk to check if it exists
        if survey is None and SURVEYS_FILE.exists():
            try:
                with open(SURVEYS_FILE, 'r') as f:
                    surveys_data = json.load(f)
                    if token in surveys_data:
                        survey_data_from_file = surveys_data[token]
                        pending_surveys[token] = {
                            "issue_key": survey_data_from_file["issue_key"],
                            "is_used": survey_data_from_file["is_used"],
                            "language": survey_data_from_file["language"],
                            "created_at": datetime.fromisoformat(survey_data_from_file["created_at"])
                        }
                        survey = pending_surveys[token]
                        logger.info(f"Survey {token} loaded from disk (created by another worker)")
            except Exception as e:
                logger.error(f"Error reloading surveys from disk: {e}")

        # Check if survey is expired
        if survey:
            now = datetime.now()
            if now - survey["created_at"] > timedelta(hours=SURVEY_EXPIRY_HOURS):
                survey = None
            else:
                # Copy data inside lock to safe local variables
                survey_data = {
                    "issue_key": survey["issue_key"],
                    "language": survey["language"]
                }

    # Determine language: from query param, then from Host header, then from survey storage
    if not lang:  # If no ?lang= parameter provided
        host = request.headers.get("host", "").lower()
        if "ostrovok.ru" in host:
            lang = "ru"
        elif "emergingtravel.com" in host:
            lang = "en"
        elif survey_data:
            # Fallback to survey language if stored
            lang = survey_data["language"]
        else:
            # Final fallback to English
            lang = "en"
    elif lang not in ("ru", "en"):
        # Invalid lang parameter, use survey language or default
        lang = survey_data["language"] if survey_data else "en"

    if not survey_data:
        status = 403
        if lang == "ru":
            title = "Ссылка недействительна или уже использована"
            desc = "Похоже, опрос по этой задаче больше недоступен."
            note = "Если вы считаете, что это ошибка, свяжитесь с поддержкой."
        else:
            title = "Link is invalid or already used"
            desc = "It looks like the survey for this ticket is no longer available."
            note = "If you believe this is a mistake, please contact support."

        ctx = {"request": request, "title": title, "desc": desc, "note": note}
        return templates.TemplateResponse("403.html", ctx, status_code=status)

    with open(os.path.join("static", "index.html"), encoding='utf-8') as f:
        data = f.read()
        # Extract project key from issue_key (e.g., "APIR-123" -> "APIR")
        issue_key = survey_data["issue_key"]
        project_key = issue_key.split('-')[0] if '-' in issue_key else ""

        # Inject as JSON-encoded literals to keep JS-safe
        data = data.replace("__TOKEN__", json.dumps(token))
        data = data.replace("__LANG__", json.dumps(lang))
        data = data.replace("__ISSUE_KEY__", json.dumps(issue_key))
        data = data.replace("__PROJECT_KEY__", json.dumps(project_key))

        return HTMLResponse(data)

@app.post("/survey/{token}/submit")
def submit_survey(token: str, score: int = Form(...), comment: str = Form("")):
    with surveys_lock:
        survey = pending_surveys.get(token)

        # If token not found in memory, try reloading from disk
        if survey is None and SURVEYS_FILE.exists():
            try:
                with open(SURVEYS_FILE, 'r') as f:
                    surveys_data = json.load(f)
                    if token in surveys_data:
                        survey_data_from_file = surveys_data[token]
                        pending_surveys[token] = {
                            "issue_key": survey_data_from_file["issue_key"],
                            "is_used": survey_data_from_file["is_used"],
                            "language": survey_data_from_file["language"],
                            "created_at": datetime.fromisoformat(survey_data_from_file["created_at"])
                        }
                        survey = pending_surveys[token]
                        logger.info(f"Survey {token} loaded from disk (created by another worker)")
            except Exception as e:
                logger.error(f"Error reloading surveys from disk: {e}")

        lang = (survey["language"] if survey and "language" in survey else 'en')
        if not survey:
            msg = "Ссылка недействительна или уже использована" if lang == "ru" else "Link is invalid or already used"
            raise HTTPException(403, detail=msg)
        if score not in (1, 2, 3, 4, 5):
            msg = "Некорректная оценка (должна быть 1..5)" if lang == "ru" else "Invalid score (must be 1..5)."
            raise HTTPException(400, detail=msg)
        if score <= 4 and not comment.strip():
            msg = "Если вы ставите 4 или ниже, комментарий обязателен." if lang == "ru" else "Comment is required if the score is 4 or less."
            raise HTTPException(400, detail=msg)
        issue_key = survey["issue_key"]
        # Remove the link after validation (to prevent reuse)
        del pending_surveys[token]

    # Save state after removing the link
    save_surveys()

    # Send to Jira in a background thread to avoid blocking the response
    thread = threading.Thread(target=send_to_jira, args=(issue_key, score, comment), daemon=True)
    thread.start()
    return {"status": "ok"}

def send_to_jira(issue_key, score, comment, max_retries=3, base_delay=1):
    """
    Send survey data to Jira with retry mechanism and exponential backoff.

    Args:
        issue_key: Jira issue key
        score: Survey score (1-5)
        comment: Survey comment
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds before first retry
    """
    jira_webhook_url = os.environ.get("JIRA_WEBHOOK_URL")
    if not jira_webhook_url:
        logger.warning("JIRA_WEBHOOK_URL is not set; skipping webhook call")
        return

    body = {
        "issue_key": issue_key,
        "score": score,
        "comment": comment
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(jira_webhook_url, json=body, timeout=10)

            # Success on 2xx status codes
            if 200 <= resp.status_code < 300:
                logger.info(f"Webhook successful for {issue_key}: {resp.status_code}")
                return

            # Retry on 5xx errors (server errors)
            if 500 <= resp.status_code < 600:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Server error {resp.status_code}. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Server error {resp.status_code}. Max retries reached for {issue_key}")
                    return

            # Don't retry on 4xx errors (client errors)
            logger.error(f"Client error {resp.status_code} for {issue_key}: {resp.text}")
            return

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Timeout. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                logger.error(f"Timeout. Max retries reached for {issue_key}")
                return

        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Connection error. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                logger.error(f"Connection error. Max retries reached for {issue_key}")
                return

        except Exception as e:
            logger.error(f"Unexpected error sending to Jira: {e}")
            return

if __name__ == "__main__":
    import uvicorn
    # Use environment variables for production settings
    host = os.environ.get("CSAT_HOST", "127.0.0.1")
    port = int(os.environ.get("CSAT_PORT", "8000"))
    workers = int(os.environ.get("CSAT_WORKERS", "4"))
    reload = os.environ.get("CSAT_RELOAD", "false").lower() == "true"

    logger.info(f"Starting CSAT service on {host}:{port} with {workers} workers (reload={reload})")
    uvicorn.run("main:app", host=host, port=port, workers=workers, reload=reload)