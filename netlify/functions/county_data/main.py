"""Netlify Function entrypoint that exposes the Flask county_data API."""

# Source: Implemented with assistance from OpenAI's GPT-5 (Codex) in the Harvard CS106 Codex CLI.

from __future__ import annotations

import sys
from pathlib import Path

from .wsgi_adapter import wsgi_handler

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[2]

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from api import index  # noqa: E402

# Point the Flask app at the copy of data.db that Netlify places next to this file.
index.DB_PATH = CURRENT_DIR / "data.db"

handler = wsgi_handler(index.APP)
