import csv
import gc
import re
import time
from pathlib import Path
from statistics import mean

from loader import load_from_csv
from linear import LinearSearchStrategy
from indexed import IndexedSearchStrategy
from parallel import ParallelSearchStrategy
from distributed import DistributedSearchStrategy


# =========================
# KONFIGURACJA BENCHMARKU
# =========================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "generatorForSyntheticalData" / "data"
RESULTS_DIR = PROJECT_ROOT / "benchmark_results"
RESULTS_FILE = RESULTS_DIR / "full_benchmark_results.csv"
SUMMARY_FILE = RESULTS_DIR / "full_benchmark_summary.csv"

WORKER_COUNTS = [1, 2, 4, 8, 12]
REPEATS = 3

CONDITIONS = [
    {
        "name": "id_eq_100",
        "condition": {"field": "id", "operator": "==", "value": 100},
    },
    {
        "name": "city_eq_warszawa",
        "condition": {"field": "city", "operator": "==", "value": "Warszawa"},
    },
    {
        "name": "department_eq_it",
        "condition": {"field": "department", "operator": "==", "value": "IT"},
    },
    {
        "name": "salary_gt_12000",
        "condition": {"field": "salary", "operator": ">", "value": 12000},
    },
    {
        "name": "age_ge_40",
        "condition": {"field": "age", "operator": ">=", "value": 40},
    },
    {
        "name": "is_manager_eq_true",
        "condition": {"field": "is_manager", "operator": "==", "value": True},
    },
    {
        "name": "last_name_contains_ski",
        "condition": {"field": "last_name", "operator": "contains", "value": "ski"},
    },
]

INDEXABLE_OPERATORS = {"=="}


# =========================
# FUNKCJE POMOCNICZE
# =========================

def get_dataset_size_from_name(filepath: Path) -> int:
    match = re.search(r"employees_(\d+)\.csv$", filepath.name)
    if not match:
        return -1
    return int(match.group(1))


def get_all_datasets(data_dir: Path) -> list[Path]:
    dataset_files = list(data_dir.glob("employees_*.csv"))
    dataset_files.sort(key=get_dataset_size_from_name)
    return dataset_files


def extract_ids(records: list[dict]) -> list[int]:
    return sorted(record["id"] for record in records)


def ensure_results_dir() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def write_csv_header_if_needed(filepath: Path, fieldnames: list[str]) -> None:
    if filepath.exists():
        return

    with filepath.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()


def append_csv_row(filepath: Path, fieldnames: list[str], row: dict) -> None:
    with filepath.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(row)


def run_timed_search(strategy, data: list[dict], condition: dict) -> tuple[list[dict], float]:
    start = time.perf_counter()
    results = strategy.search(data, condition)
    elapsed = time.perf_counter() - start
    return results, elapsed


def safe_error_message(error: Exception) -> str:
    return f"{type(error).__name__}: {str(error)}"


# =========================
# BENCHMARK STRATEGII
# =========================

def benchmark_linear(data: list[dict], condition: dict) -> tuple[list[dict], float, float, float]:
    strategy = LinearSearchStrategy()
    results, search_time = run_timed_search(strategy, data, condition)

    build_time = 0.0
    total_time = search_time

    return results, build_time, search_time, total_time


def benchmark_indexed(data: list[dict], condition: dict) -> tuple[list[dict], float, float, float]:
    field = condition["field"]
    operator_symbol = condition["operator"]

    strategy = IndexedSearchStrategy(index_field=field)

    build_time = 0.0

    if operator_symbol in INDEXABLE_OPERATORS:
        start = time.perf_counter()
        strategy.build_index(data)
        build_time = time.perf_counter() - start

    start = time.perf_counter()
    results = strategy.search(data, condition)
    search_time = time.perf_counter() - start

    total_time = build_time + search_time

    return results, build_time, search_time, total_time


def benchmark_parallel(data: list[dict], condition: dict, workers: int) -> tuple[list[dict], float, float, float]:
    strategy = ParallelSearchStrategy(workers=workers)
    results, search_time = run_timed_search(strategy, data, condition)

    build_time = 0.0
    total_time = search_time

    return results, build_time, search_time, total_time


def benchmark_distributed(data: list[dict], condition: dict, workers: int) -> tuple[list[dict], float, float, float]:
    strategy = DistributedSearchStrategy(workers=workers)
    results, search_time = run_timed_search(strategy, data, condition)

    build_time = 0.0
    total_time = search_time

    return results, build_time, search_time, total_time


# =========================
# ZAPIS WYNIKÓW
# =========================

RESULT_FIELDNAMES = [
    "dataset_size",
    "dataset_file",
    "query_name",
    "field",
    "operator",
    "value",
    "strategy",
    "workers",
    "repeat",
    "build_time_seconds",
    "search_time_seconds",
    "total_time_seconds",
    "result_count",
    "equal_to_linear",
    "error",
]


SUMMARY_FIELDNAMES = [
    "dataset_size",
    "dataset_file",
    "query_name",
    "strategy",
    "workers",
    "repeats",
    "avg_build_time_seconds",
    "avg_search_time_seconds",
    "avg_total_time_seconds",
    "min_total_time_seconds",
    "max_total_time_seconds",
    "result_count",
    "all_equal_to_linear",
    "errors_count",
]


def make_result_row(
    dataset_size: int,
    dataset_file: str,
    query_name: str,
    condition: dict,
    strategy: str,
    workers: int | str,
    repeat: int,
    build_time: float | None,
    search_time: float | None,
    total_time: float | None,
    result_count: int | None,
    equal_to_linear: bool | None,
    error: str = "",
) -> dict:
    return {
        "dataset_size": dataset_size,
        "dataset_file": dataset_file,
        "query_name": query_name,
        "field": condition["field"],
        "operator": condition["operator"],
        "value": condition["value"],
        "strategy": strategy,
        "workers": workers,
        "repeat": repeat,
        "build_time_seconds": "" if build_time is None else f"{build_time:.9f}",
        "search_time_seconds": "" if search_time is None else f"{search_time:.9f}",
        "total_time_seconds": "" if total_time is None else f"{total_time:.9f}",
        "result_count": "" if result_count is None else result_count,
        "equal_to_linear": "" if equal_to_linear is None else equal_to_linear,
        "error": error,
    }


def write_summary_from_results(results_file: Path, summary_file: Path) -> None:
    if not results_file.exists():
        print("Brak pliku z wynikami, nie tworzę summary.")
        return

    with results_file.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    grouped = {}

    for row in rows:
        key = (
            row["dataset_size"],
            row["dataset_file"],
            row["query_name"],
            row["strategy"],
            row["workers"],
        )
        grouped.setdefault(key, []).append(row)

    with summary_file.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=SUMMARY_FIELDNAMES)
        writer.writeheader()

        for key, group_rows in grouped.items():
            dataset_size, dataset_file, query_name, strategy, workers = key

            successful_rows = [r for r in group_rows if not r["error"]]
            error_rows = [r for r in group_rows if r["error"]]

            if successful_rows:
                build_times = [float(r["build_time_seconds"]) for r in successful_rows]
                search_times = [float(r["search_time_seconds"]) for r in successful_rows]
                total_times = [float(r["total_time_seconds"]) for r in successful_rows]

                result_count = successful_rows[0]["result_count"]
                all_equal = all(r["equal_to_linear"] == "True" for r in successful_rows)

                writer.writerow({
                    "dataset_size": dataset_size,
                    "dataset_file": dataset_file,
                    "query_name": query_name,
                    "strategy": strategy,
                    "workers": workers,
                    "repeats": len(group_rows),
                    "avg_build_time_seconds": f"{mean(build_times):.9f}",
                    "avg_search_time_seconds": f"{mean(search_times):.9f}",
                    "avg_total_time_seconds": f"{mean(total_times):.9f}",
                    "min_total_time_seconds": f"{min(total_times):.9f}",
                    "max_total_time_seconds": f"{max(total_times):.9f}",
                    "result_count": result_count,
                    "all_equal_to_linear": all_equal,
                    "errors_count": len(error_rows),
                })
            else:
                writer.writerow({
                    "dataset_size": dataset_size,
                    "dataset_file": dataset_file,
                    "query_name": query_name,
                    "strategy": strategy,
                    "workers": workers,
                    "repeats": len(group_rows),
                    "avg_build_time_seconds": "",
                    "avg_search_time_seconds": "",
                    "avg_total_time_seconds": "",
                    "min_total_time_seconds": "",
                    "max_total_time_seconds": "",
                    "result_count": "",
                    "all_equal_to_linear": False,
                    "errors_count": len(error_rows),
                })


# =========================
# GŁÓWNY BENCHMARK
# =========================

def run_single_measurement(
    dataset_size: int,
    dataset_file: str,
    data: list[dict],
    query_name: str,
    condition: dict,
    strategy_name: str,
    workers: int | str,
    repeat: int,
    linear_ids: list[int],
) -> None:
    print(
        f"      {strategy_name:12s} | workers={str(workers):>2s} | repeat={repeat}/{REPEATS}",
        flush=True,
    )

    try:
        if strategy_name == "linear":
            results, build_time, search_time, total_time = benchmark_linear(data, condition)
        elif strategy_name == "indexed":
            results, build_time, search_time, total_time = benchmark_indexed(data, condition)
        elif strategy_name == "parallel":
            results, build_time, search_time, total_time = benchmark_parallel(data, condition, int(workers))
        elif strategy_name == "distributed":
            results, build_time, search_time, total_time = benchmark_distributed(data, condition, int(workers))
        else:
            raise ValueError(f"Nieznana strategia: {strategy_name}")

        result_ids = extract_ids(results)
        equal_to_linear = result_ids == linear_ids

        row = make_result_row(
            dataset_size=dataset_size,
            dataset_file=dataset_file,
            query_name=query_name,
            condition=condition,
            strategy=strategy_name,
            workers=workers,
            repeat=repeat,
            build_time=build_time,
            search_time=search_time,
            total_time=total_time,
            result_count=len(results),
            equal_to_linear=equal_to_linear,
            error="",
        )

        append_csv_row(RESULTS_FILE, RESULT_FIELDNAMES, row)

        print(
            f"        -> time={total_time:.6f}s | count={len(results)} | equal={equal_to_linear}",
            flush=True,
        )

    except Exception as error:
        error_msg = safe_error_message(error)

        row = make_result_row(
            dataset_size=dataset_size,
            dataset_file=dataset_file,
            query_name=query_name,
            condition=condition,
            strategy=strategy_name,
            workers=workers,
            repeat=repeat,
            build_time=None,
            search_time=None,
            total_time=None,
            result_count=None,
            equal_to_linear=None,
            error=error_msg,
        )

        append_csv_row(RESULTS_FILE, RESULT_FIELDNAMES, row)

        print(f"        -> ERROR: {error_msg}", flush=True)


def run_benchmark_for_condition(
    dataset_size: int,
    dataset_file: str,
    data: list[dict],
    query_name: str,
    condition: dict,
) -> None:
    print("-" * 120)
    print(f"  QUERY: {query_name}")
    print(f"  CONDITION: {condition}")

    # Linear liczymy jako referencję dla każdego repeat.
    # Do porównywania wystarczy wynik z pierwszego linear run, ale zapisujemy wszystkie powtórzenia.
    linear_reference_results = LinearSearchStrategy().search(data, condition)
    linear_ids = extract_ids(linear_reference_results)

    print(f"  Reference linear count: {len(linear_reference_results)}")

    for repeat in range(1, REPEATS + 1):
        run_single_measurement(
            dataset_size=dataset_size,
            dataset_file=dataset_file,
            data=data,
            query_name=query_name,
            condition=condition,
            strategy_name="linear",
            workers="-",
            repeat=repeat,
            linear_ids=linear_ids,
        )

        run_single_measurement(
            dataset_size=dataset_size,
            dataset_file=dataset_file,
            data=data,
            query_name=query_name,
            condition=condition,
            strategy_name="indexed",
            workers="-",
            repeat=repeat,
            linear_ids=linear_ids,
        )

        for workers in WORKER_COUNTS:
            run_single_measurement(
                dataset_size=dataset_size,
                dataset_file=dataset_file,
                data=data,
                query_name=query_name,
                condition=condition,
                strategy_name="parallel",
                workers=workers,
                repeat=repeat,
                linear_ids=linear_ids,
            )

        for workers in WORKER_COUNTS:
            run_single_measurement(
                dataset_size=dataset_size,
                dataset_file=dataset_file,
                data=data,
                query_name=query_name,
                condition=condition,
                strategy_name="distributed",
                workers=workers,
                repeat=repeat,
                linear_ids=linear_ids,
            )


def run_benchmark_for_dataset(dataset_path: Path) -> None:
    dataset_size = get_dataset_size_from_name(dataset_path)
    dataset_file = dataset_path.name

    print("=" * 120)
    print(f"DATASET: {dataset_file}")
    print(f"PATH: {dataset_path}")
    print(f"SIZE FROM NAME: {dataset_size}")

    start_load = time.perf_counter()
    data = load_from_csv(dataset_path)
    load_time = time.perf_counter() - start_load

    print(f"Loaded records: {len(data)}")
    print(f"Load time: {load_time:.6f}s")

    for item in CONDITIONS:
        run_benchmark_for_condition(
            dataset_size=dataset_size,
            dataset_file=dataset_file,
            data=data,
            query_name=item["name"],
            condition=item["condition"],
        )

        # Lekka przerwa porządkowa dla GC między query.
        gc.collect()

    del data
    gc.collect()


def main() -> None:
    ensure_results_dir()
    write_csv_header_if_needed(RESULTS_FILE, RESULT_FIELDNAMES)

    datasets = get_all_datasets(DATA_DIR)

    if not datasets:
        print(f"Brak plików employees_*.csv w katalogu: {DATA_DIR}")
        return

    print("FULL BENCHMARK START")
    print(f"Data dir: {DATA_DIR}")
    print(f"Results file: {RESULTS_FILE}")
    print(f"Summary file: {SUMMARY_FILE}")
    print(f"Repeats: {REPEATS}")
    print(f"Workers: {WORKER_COUNTS}")
    print("Datasets:")
    for dataset in datasets:
        print(f"  - {dataset.name}")

    global_start = time.perf_counter()

    for dataset_path in datasets:
        run_benchmark_for_dataset(dataset_path)

    total_elapsed = time.perf_counter() - global_start

    print("=" * 120)
    print("Tworzę plik summary...")
    write_summary_from_results(RESULTS_FILE, SUMMARY_FILE)

    print("=" * 120)
    print("FULL BENCHMARK DONE")
    print(f"Total time: {total_elapsed:.2f}s")
    print(f"Raw results: {RESULTS_FILE}")
    print(f"Summary: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()