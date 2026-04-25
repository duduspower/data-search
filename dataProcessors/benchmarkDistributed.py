import time

from loader import load_from_csv
from linear import LinearSearchStrategy
from parallel import ParallelSearchStrategy
from distributed import DistributedSearchStrategy


def extract_ids(records: list[dict]) -> list[int]:
    return sorted(record["id"] for record in records)


def main():
    data = load_from_csv("generatorForSyntheticalData/data/employees_100000.csv")
    condition = {"field": "salary", "operator": ">", "value": 12000}

    linear_strategy = LinearSearchStrategy()
    parallel_strategy = ParallelSearchStrategy(workers=4)
    distributed_strategy = DistributedSearchStrategy(workers=4)

    start = time.perf_counter()
    linear_results = linear_strategy.search(data, condition)
    linear_time = time.perf_counter() - start

    start = time.perf_counter()
    parallel_results = parallel_strategy.search(data, condition)
    parallel_time = time.perf_counter() - start

    start = time.perf_counter()
    distributed_results = distributed_strategy.search(data, condition)
    distributed_time = time.perf_counter() - start

    linear_ids = extract_ids(linear_results)
    parallel_ids = extract_ids(parallel_results)
    distributed_ids = extract_ids(distributed_results)

    print(f"Linear time: {linear_time:.6f}s")
    print(f"Parallel time: {parallel_time:.6f}s")
    print(f"Distributed time: {distributed_time:.6f}s")

    print(f"Linear == Parallel: {linear_ids == parallel_ids}")
    print(f"Linear == Distributed: {linear_ids == distributed_ids}")


if __name__ == "__main__":
    main()