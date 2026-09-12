"""Isolated synthetic test environment; never load developer model credentials."""
import os
from pathlib import Path

os.environ["DJANGO_SKIP_ENV_FILE"] = "1"
os.environ["DATABASE_URL"] = ""
os.environ["DJANGO_SECRET_KEY"] = "synthetic-test-signing-key"
os.environ["LLM_PROVIDER"] = "openai_compatible"
os.environ["LLM_API_KEY"] = "synthetic-only"
os.environ["LLM_BASE_URL"] = "http://127.0.0.1:8766/v1"
os.environ["LLM_MODEL"] = "fixture-model"
os.environ["LLM_TIMEOUT_SECONDS"] = "5"

from .settings import *  # noqa: E402,F403

TEST_ROOT = Path(__file__).resolve().parents[2] / ".e2e-runtime"
MEDIA_ROOT = TEST_ROOT / "media"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": TEST_ROOT / "db.sqlite3"}}
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = ["http://127.0.0.1:4173"]
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
DEBUG = False
