from __future__ import annotations

from multiprocessing import freeze_support

from benchmark import run_benchmark
from data_access import list_datasets, load_dataset
from query_logic import SearchEngine, field


def main() -> None:
    datasets = list_datasets()
    if not datasets:
        raise SystemExit("Brak datasetow w generatorForSyntheticalData/data")

    data = load_dataset(datasets[0])
    engine = SearchEngine()
    results = engine.search(data, field("city") == "Warszawa", strategy="indexed", index_field="city")
    benchmark_results = run_benchmark(data[:1000], workers=2)

    print(f"Dataset: {datasets[0]}")
    print(f"Records loaded: {len(data)}")
    print(f"Warszawa results: {len(results)}")
    print(f"Benchmark rows: {len(benchmark_results)}")
    print(f"Benchmark OK: {all(result.equals_linear for result in benchmark_results)}")


if __name__ == "__main__":
    freeze_support()
    main()

