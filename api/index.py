"""
Vercel Serverless Function Entrypoint for Nivesh FastAPI Backend.
This file lives at the repo root api/index.py so Vercel's @vercel/python
builder picks it up and routes all /api/* requests here.
"""

import sys
import os

# Add the backend directory to Python path so all imports resolve correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app  # noqa: F401 — 'app' is what Vercel's ASGI adapter looks for
