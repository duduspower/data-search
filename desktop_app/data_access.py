from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path
from typing import Any

from repo_paths import DATA_DIR, GENERATOR_DIR, OUTPUT_DIR, configure_imports


configure_imports()

from loader import load_from_csv


def list_datasets() -> list[Path]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(DATA_DIR.glob("employees_*.csv"), key=lambda path: path.name)


def dataset_for_count(count: int) -> Path:
    return DATA_DIR / f"employees_{count}.csv"


def ensure_dataset(count: int) -> Path:
    path = dataset_for_count(count)
    if path.exists():
        return path

    generator = GENERATOR_DIR / "syntheticalDataGenerator.py"
    if not generator.exists():
        raise FileNotFoundError(f"Brak generatora danych: {generator}")

    command = [
        sys.executable,
        str(generator),
        str(count),
        "--output-dir",
        str(DATA_DIR),
        "--filename",
        path.name,
    ]
    completed = subprocess.run(command, cwd=GENERATOR_DIR, text=True, capture_output=True)
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(
            "Nie udalo sie uruchomic generatora danych. "
            "Sprawdz, czy zainstalowana jest biblioteka Faker. "
            f"Szczegoly: {details}"
        )

    return path


def load_dataset(path: str | Path) -> list[dict[str, Any]]:
    return load_from_csv(path)


def save_records(records: list[dict[str, Any]], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        path.write_text("", encoding="utf-8")
        return path

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    return path


def default_output_path(name: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / name

