from __future__ import annotations

import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
DATA_PROCESSORS_DIR = REPO_ROOT / "dataProcessors"
GENERATOR_DIR = REPO_ROOT / "generatorForSyntheticalData"
DATA_DIR = GENERATOR_DIR / "data"
OUTPUT_DIR = APP_DIR / "output"


def configure_imports() -> None:
    for path in (REPO_ROOT, DATA_PROCESSORS_DIR):
        path_text = str(path)
        if path_text not in sys.path:
            sys.path.insert(0, path_text)


configure_imports()

