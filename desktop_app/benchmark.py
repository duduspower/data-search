from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from query_logic import SearchEngine, field


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    condition: Any
    index_field: str


@dataclass(frozen=True)
class BenchmarkResult:
    case_name: str
    strategy: str
    elapsed_seconds: float
    result_count: int
    equals_linear: bool


def default_cases() -> list[BenchmarkCase]:
    return [
        BenchmarkCase("city_eq_warszawa", field("city") == "Warszawa", "city"),
        BenchmarkCase("salary_gt_12000", field("salary") > 12000, "salary"),
        BenchmarkCase("department_eq_it", field("department") == "IT", "department"),
        BenchmarkCase("last_name_contains_ski", field("last_name").contains("ski"), "last_name"),
    ]


def extract_ids(records: list[dict[str, Any]]) -> list[Any]:
    return sorted(record.get("id") for record in records)


def run_benchmark(data: list[dict[str, Any]], workers: int = 2) -> list[BenchmarkResult]:
    engine = SearchEngine()
    results: list[BenchmarkResult] = []

    for case in default_cases():
        baseline = engine.search(data, case.condition, strategy="linear")
        baseline_ids = extract_ids(baseline)

        for strategy in engine.available_strategies():
            options: dict[str, Any] = {}
            if strategy == "indexed":
                options["index_field"] = case.index_field
            if strategy == "parallel":
                options["workers"] = workers

            start = perf_counter()
            found = engine.search(data, case.condition, strategy=strategy, **options)
            elapsed = perf_counter() - start

            results.append(
                BenchmarkResult(
                    case_name=case.name,
                    strategy=strategy,
                    elapsed_seconds=elapsed,
                    result_count=len(found),
                    equals_linear=extract_ids(found) == baseline_ids,
                )
            )

    return results


def save_benchmark(results: list[BenchmarkResult], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)

    return path

