from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from query_logic import SearchEngine, field
from repo_paths import APP_DIR


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    filters: tuple[dict[str, Any], ...]
    combine: str
    index_field: str


@dataclass(frozen=True)
class BenchmarkResult:
    case_name: str
    strategy: str
    elapsed_seconds: float
    result_count: int
    equals_linear: bool
    error_message: str = ""


def default_benchmark_cases_path() -> Path:
    return APP_DIR / "benchmark_cases.json"


def default_cases() -> list[BenchmarkCase]:
    return [
        BenchmarkCase(
            "city_eq_warszawa",
            ({"field": "city", "operator": "==", "value": "Warszawa"},),
            "and",
            "city",
        ),
        BenchmarkCase(
            "salary_gt_12000",
            ({"field": "salary", "operator": ">", "value": 12000},),
            "and",
            "salary",
        ),
        BenchmarkCase(
            "department_eq_it",
            ({"field": "department", "operator": "==", "value": "IT"},),
            "and",
            "department",
        ),
        BenchmarkCase(
            "last_name_contains_ski",
            ({"field": "last_name", "operator": "contains", "value": "ski"},),
            "and",
            "last_name",
        ),
    ]


def build_condition(filter_spec: dict[str, Any]) -> Any:
    selected = field(str(filter_spec["field"]))
    operator = str(filter_spec["operator"])
    value = filter_spec["value"]

    if operator in {"=", "=="}:
        return selected == value
    if operator == "!=":
        return selected != value
    if operator == ">":
        return selected > value
    if operator == ">=":
        return selected >= value
    if operator == "<":
        return selected < value
    if operator == "<=":
        return selected <= value
    if operator == "contains":
        return selected.contains(value)
    raise ValueError(f"Nieobslugiwany operator benchmarka: {operator}")


def case_condition(case: BenchmarkCase) -> Any:
    conditions = [build_condition(filter_spec) for filter_spec in case.filters]
    if not conditions:
        raise ValueError(f"Benchmark '{case.name}' nie ma warunkow.")

    result = conditions[0]
    for condition in conditions[1:]:
        result = result | condition if case.combine == "or" else result & condition
    return result


def describe_case(case: BenchmarkCase) -> str:
    separator = f" {case.combine.upper()} "
    return separator.join(
        f"{spec['field']} {spec['operator']} {spec['value']}"
        for spec in case.filters
    )


def normalize_case(raw_case: dict[str, Any]) -> BenchmarkCase:
    filters = tuple(dict(filter_spec) for filter_spec in raw_case.get("filters", []))
    combine = str(raw_case.get("combine", "and")).lower()
    if combine not in {"and", "or"}:
        combine = "and"
    return BenchmarkCase(
        name=str(raw_case["name"]),
        filters=filters,
        combine=combine,
        index_field=str(raw_case.get("index_field") or (filters[0]["field"] if filters else "id")),
    )


def load_benchmark_cases(path: str | Path | None = None) -> list[BenchmarkCase]:
    path = Path(path) if path is not None else default_benchmark_cases_path()
    if not path.exists():
        cases = default_cases()
        save_benchmark_cases(cases, path)
        return cases

    with path.open("r", encoding="utf-8") as json_file:
        raw_cases = json.load(json_file)
    return [normalize_case(raw_case) for raw_case in raw_cases]


def save_benchmark_cases(cases: list[BenchmarkCase], path: str | Path | None = None) -> Path:
    path = Path(path) if path is not None else default_benchmark_cases_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as json_file:
        json.dump([asdict(case) for case in cases], json_file, ensure_ascii=False, indent=2)

    return path


def extract_ids(records: list[dict[str, Any]]) -> list[Any]:
    return sorted(record.get("id") for record in records)


def run_benchmark(
    data: list[dict[str, Any]],
    workers: int = 2,
    cases: list[BenchmarkCase] | None = None,
) -> list[BenchmarkResult]:
    engine = SearchEngine()
    results: list[BenchmarkResult] = []

    for case in cases or load_benchmark_cases():
        condition = case_condition(case)
        baseline = engine.search(data, condition, strategy="linear")
        baseline_ids = extract_ids(baseline)

        for strategy in engine.available_strategies():
            options: dict[str, Any] = {}
            if strategy == "indexed":
                options["index_field"] = case.index_field
            if strategy == "parallel":
                options["workers"] = workers
            if strategy == "distributed":
                options["workers"] = workers

            start = perf_counter()
            try:
                found = engine.search(data, condition, strategy=strategy, **options)
                result_count = len(found)
                equals_linear = extract_ids(found) == baseline_ids
                error_message = ""
            except Exception as exc:
                found = []
                result_count = 0
                equals_linear = False
                error_message = str(exc)
            elapsed = perf_counter() - start

            results.append(
                BenchmarkResult(
                    case_name=case.name,
                    strategy=strategy,
                    elapsed_seconds=elapsed,
                    result_count=result_count,
                    equals_linear=equals_linear,
                    error_message=error_message,
                )
            )

    return results


def save_benchmark(results: list[BenchmarkResult], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not results:
        path.write_text("", encoding="utf-8")
        return path

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)

    return path
