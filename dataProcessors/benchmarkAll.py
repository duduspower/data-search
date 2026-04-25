import re
import time
from pathlib import Path

from loader import load_from_csv
from linear import LinearSearchStrategy
from indexed import IndexedSearchStrategy
from parallel import ParallelSearchStrategy
from distributed import DistributedSearchStrategy


DATA_DIR = Path("generatorForSyntheticalData/data")
WORKER_COUNTS = [1, 2, 4, 8, 12]

CONDITIONS = [
    {"name": "city_eq_warszawa", "condition": {"field": "city", "operator": "==", "value": "Warszawa"}},
    {"name": "salary_gt_12000", "condition": {"field": "salary", "operator": ">", "value": 12000}},
    {"name": "department_eq_it", "condition": {"field": "department", "operator": "==", "value": "IT"}},
    {"name": "id_eq_100", "condition": {"field": "id", "operator": "==", "value": 100}},
]

INDEX_FIELDS = {"city", "department", "id"}


def extract_ids(records: list[dict]) -> list[int]:
    return sorted(record["id"] for record in records)


def get_dataset_size_from_name(filepath: Path) -> int:
    match = re.search(r"employees_(\d+)\.csv$", filepath.name)
    if not match:
        return -1
    return int(match.group(1))


def get_all_datasets(data_dir: Path) -> list[Path]:
    dataset_files = list(data_dir.glob("employees_*.csv"))
    dataset_files.sort(key=get_dataset_size_from_name)
    return dataset_files


def benchmark_linear(data: list[dict], condition: dict) -> tuple[list[dict], float]:
    strategy = LinearSearchStrategy()

    start = time.perf_counter()
    results = strategy.search(data, condition)
    elapsed = time.perf_counter() - start

    return results, elapsed


def benchmark_indexed(data: list[dict], condition: dict) -> tuple[list[dict], float, float]:
    field = condition["field"]

    if field not in INDEX_FIELDS or condition["operator"] != "==":
        strategy = IndexedSearchStrategy(index_field=field)

        start = time.perf_counter()
        results = strategy.search(data, condition)
        elapsed = time.perf_counter() - start

        return results, 0.0, elapsed

    strategy = IndexedSearchStrategy(index_field=field)

    start = time.perf_counter()
    strategy.build_index(data)
    build_time = time.perf_counter() - start

    start = time.perf_counter()
    results = strategy.search(data, condition)
    search_time = time.perf_counter() - start

    return results, build_time, search_time


def benchmark_parallel(data: list[dict], condition: dict, workers: int) -> tuple[list[dict], float]:
    strategy = ParallelSearchStrategy(workers=workers)

    start = time.perf_counter()
    results = strategy.search(data, condition)
    elapsed = time.perf_counter() - start

    return results, elapsed


def benchmark_distributed(data: list[dict], condition: dict, workers: int) -> tuple[list[dict], float]:
    strategy = DistributedSearchStrategy(workers=workers)

    start = time.perf_counter()
    results = strategy.search(data, condition)
    elapsed = time.perf_counter() - start

    return results, elapsed


def run_benchmark_for_dataset(dataset_path: Path) -> None:
    print("=" * 140)
    print(f"DATASET: {dataset_path}")

    if not dataset_path.exists():
        print("Plik nie istnieje, pomijam.")
        return

    data = load_from_csv(dataset_path)
    print(f"Liczba rekordów: {len(data)}")

    for item in CONDITIONS:
        test_name = item["name"]
        condition = item["condition"]

        print("-" * 140)
        print(f"TEST: {test_name}")
        print(f"CONDITION: {condition}")

        # Linear
        linear_results, linear_time = benchmark_linear(data, condition)
        linear_ids = extract_ids(linear_results)

        print(f"Linear -> time: {linear_time:.6f}s | count: {len(linear_results)}")

        # Indexed
        indexed_results, index_build_time, indexed_time = benchmark_indexed(data, condition)
        indexed_ids = extract_ids(indexed_results)

        print(
            f"Indexed -> build: {index_build_time:.6f}s | search: {indexed_time:.6f}s | "
            f"count: {len(indexed_results)} | equal_to_linear: {indexed_ids == linear_ids}"
        )

        # Parallel for many worker counts
        print("Parallel:")
        for workers in WORKER_COUNTS:
            try:
                parallel_results, parallel_time = benchmark_parallel(data, condition, workers=workers)
                parallel_ids = extract_ids(parallel_results)

                print(
                    f"  workers={workers:<2} -> time: {parallel_time:.6f}s | "
                    f"count: {len(parallel_results)} | equal_to_linear: {parallel_ids == linear_ids}"
                )
            except Exception as e:
                print(f"  workers={workers:<2} -> ERROR: {e}")

        # Distributed for many worker counts
        print("Distributed:")
        for workers in WORKER_COUNTS:
            try:
                distributed_results, distributed_time = benchmark_distributed(data, condition, workers=workers)
                distributed_ids = extract_ids(distributed_results)

                print(
                    f"  workers={workers:<2} -> time: {distributed_time:.6f}s | "
                    f"count: {len(distributed_results)} | equal_to_linear: {distributed_ids == linear_ids}"
                )
            except Exception as e:
                print(f"  workers={workers:<2} -> ERROR: {e}")


def main() -> None:
    datasets = get_all_datasets(DATA_DIR)

    if not datasets:
        print(f"Brak plików employees_*.csv w folderze: {DATA_DIR}")
        return

    print("Znalezione datasety:")
    for ds in datasets:
        print(f" - {ds.name}")

    print(f"\nTestowane liczby workerów: {WORKER_COUNTS}\n")

    for dataset_path in datasets:
        run_benchmark_for_dataset(dataset_path)


if __name__ == "__main__":
    main()