import csv
from pathlib import Path


INT_FIELDS = {"id", "age", "salary", "years_experience", "join_year"}
BOOL_FIELDS = {"is_manager"}


def convert_row_types(row: dict) -> dict:
    converted = {}

    for key, value in row.items():
        if key in INT_FIELDS:
            converted[key] = int(value)
        elif key in BOOL_FIELDS:
            converted[key] = value == "True"
        else:
            converted[key] = value

    return converted


def load_from_csv(filepath: str | Path) -> list[dict]:
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Plik nie istnieje: {filepath}")

    data = []

    with filepath.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            data.append(convert_row_types(row))

    return data