import sys
import os

# Add root directory and backend directory to sys.path so all imports resolve
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
backend_dir = os.path.join(root_dir, "backend")

sys.path.insert(0, root_dir)
sys.path.insert(0, backend_dir)

from main import app  # noqa: F401
