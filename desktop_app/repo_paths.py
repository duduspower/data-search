from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
DATA_PROCESSORS_DIR = REPO_ROOT / "dataProcessors"
GENERATOR_DIR = REPO_ROOT / "generatorForSyntheticalData"
DATA_DIR = GENERATOR_DIR / "data"
OUTPUT_DIR = APP_DIR / "output"


def configure_imports() -> None:
    python_path_entries = []
    for path in (REPO_ROOT, DATA_PROCESSORS_DIR):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)
        python_path_entries.append(path_text)

    existing_python_path = os.environ.get("PYTHONPATH", "")
    existing_entries = [entry for entry in existing_python_path.split(os.pathsep) if entry]
    for path_text in reversed(python_path_entries):
        if path_text not in existing_entries:
            existing_entries.insert(0, path_text)
    os.environ["PYTHONPATH"] = os.pathsep.join(existing_entries)


configure_imports()
