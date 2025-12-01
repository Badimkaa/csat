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
import sched

# ==============================================================================
# Configuration
# ==============================================================================

APP_DIR = Path(__file__).parent
DATA_DIR = Path(os.environ.get("CSAT_DATA_DIR", "/var/lib/csat"))
LOG_DIR = Path(os.environ.get("CSAT_LOG_DIR", "/var/log/csat"))

CSAT_HOST = os.environ.get("CSAT_HOST", "127.0.0.1")
CSAT_PORT = int(os.environ.get("CSAT_PORT", "8000"))
CSAT_WORKERS = int(os.environ.get("CSAT_WORKERS", "4"))
CSAT_RELOAD = os.environ.get("CSAT_RELOAD", "false").lower() == "true"
ALLOWED_ORIGINS = os.environ.get("CSAT_ALLOWED_ORIGINS", "http://localhost:8000").split(",")
SURVEY_EXPIRY_HOURS = int(os.environ.get("CSAT_SURVEY_EXPIRY_HOURS", "168"))
JIRA_WEBHOOK_URL = os.environ.get("JIRA_WEBHOOK_URL")

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# Logging Setup
# ==============================================================================

log_file = LOG_DIR / "app.log"
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_handler = TimedRotatingFileHandler(filename=str(log_file), when='midnight', interval=1, backupCount=7, encoding='utf-8')
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler])
logger = logging.getLogger(__name__)

# ==============================================================================
# Survey Data Store (Thread-Safe & Multi-Process-Safe)
# ==============================================================================

class SurveyStore:
    def __init__(self, file_path, expiry_hours):
        self._file_path = file_path
        self._expiry_delta = timedelta(hours=expiry_hours)
        self._surveys = {}
        self._lock = threading.Lock()
        with self._lock:
            self._load_from_disk()

    def _load_from_disk(self):
        try:
            if self._file_path.exists():
                with open(self._file_path, 'r') as f:
                    surveys_data = json.load(f)
                self._surveys = {
                    token: {
                        "issue_key": survey["issue_key"],
                        "is_used": survey["is_used"],
                        "language": survey["language"],
                        "created_at": datetime.fromisoformat(survey["created_at"])
                    } for token, survey in surveys_data.items()
                }
            else:
                self._surveys = {}
        except Exception as e:
            logger.error(f"Could not load surveys from disk: {e}", exc_info=True)

    def _save_to_disk(self):
        try:
            surveys_to_save = {
                token: {
                    "issue_key": survey["issue_key"],
                    "is_used": survey["is_used"],
                    "language": survey["language"],
                    "created_at": survey["created_at"].isoformat()
                } for token, survey in self._surveys.items()
            }
            temp_file = self._file_path.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(surveys_to_save, f)
            temp_file.replace(self._file_path)
        except Exception as e:
            logger.error(f"Error saving surveys: {e}")

    def add(self, issue_key, language):
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._load_from_disk()
            self._surveys[token] = {
                "issue_key": issue_key,
                "is_used": False,
                "language": language,
                "created_at": datetime.now()
            }
            self._save_to_disk()
        return token

    def get(self, token):
        with self._lock:
            self._load_from_disk()
            survey = self._surveys.get(token)
            if survey and not survey["is_used"]:
                if datetime.now() - survey["created_at"] <= self._expiry_delta:
                    return survey.copy()
        return None

    def use(self, token):
        with self._lock:
            self._load_from_disk()
            if token in self._surveys:
                survey = self._surveys.pop(token)
                self._save_to_disk()
                return survey
        return None

    def cleanup_expired(self):
        with self._lock:
            self._load_from_disk()
            now = datetime.now()
            expired_tokens = [
                token for token, survey in self._surveys.items()
                if survey["is_used"] or (now - survey["created_at"] > self._expiry_delta)
            ]
            if expired_tokens:
                for token in expired_tokens:
                    del self._surveys[token]
                self._save_to_disk()

survey_store = SurveyStore(
    file_path=DATA_DIR / "surveys.json",
    expiry_hours=SURVEY_EXPIRY_HOURS
)

scheduler = sched.scheduler(time.time, time.sleep)
stop_scheduler = threading.Event()

def scheduled_cleanup(sc):
    if not stop_scheduler.is_set():
        survey_store.cleanup_expired()
        scheduler.enter(3600, 1, scheduled_cleanup, (sc,))

def run_scheduler():
    scheduler.enter(3600, 1, scheduled_cleanup, (scheduler,))
    scheduler.run()

@asynccontextmanager
async def lifespan(app: FastAPI):
    survey_store.cleanup_expired()
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    yield
    stop_scheduler.set()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")

@app.post("/survey/create")
async def create_survey(issue_key: str = Form(...), language: str = Form('en')):
    token = survey_store.add(issue_key, language)
    domain = "survey.ostrovok.ru" if language == "ru" else "survey.emergingtravel.com"
    return {"link": f"https://{domain}/survey/{token}"}

@app.get("/survey/{token}", response_class=HTMLResponse)
async def get_survey(request: Request, token: str, lang: str = Query(None)):
    survey = survey_store.get(token)
    if not lang or lang not in ("ru", "en"):
        host = request.headers.get("host", "").lower()
        lang = "ru" if "ostrovok.ru" in host else "en"
    if not survey:
        details = {"title": "Invalid Link", "desc": "Survey unavailable.", "note": "Contact support."}
        return templates.TemplateResponse("403.html", {"request": request, **details}, status_code=403)

    return templates.TemplateResponse("index.html", {
        "request": request, "token": token, "lang": lang,
        "issue_key": survey["issue_key"],
        "project_key": survey["issue_key"].split('-')[0]
    })

@app.post("/survey/{token}/submit")
async def submit_survey(token: str, score: int = Form(...), comment: str = Form(...)):
    survey = survey_store.get(token)
    lang = survey.get("language", "en") if survey else 'en'
    if not survey: raise HTTPException(403, "Invalid link")
    if not 1 <= score <= 5: raise HTTPException(400, "Invalid score")
    if score <= 4 and not comment.strip(): raise HTTPException(400, "Comment required")

    used_survey = survey_store.use(token)
    if not used_survey: raise HTTPException(409, "Already submitted")

    threading.Thread(target=send_to_jira, args=(used_survey["issue_key"], score, comment), daemon=True).start()
    return {"status": "ok"}

def send_to_jira(issue_key, score, comment, max_retries=3, base_delay=1):
    if not JIRA_WEBHOOK_URL: return
    body = {"issue_key": issue_key, "score": score, "comment": comment}
    for i in range(max_retries):
        try:
            r = requests.post(JIRA_WEBHOOK_URL, json=body, timeout=10)
            if r.ok: return
        except requests.RequestException: pass
        time.sleep(base_delay * (2 ** i))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=CSAT_HOST, port=CSAT_PORT, workers=CSAT_WORKERS, reload=CSAT_RELOAD)