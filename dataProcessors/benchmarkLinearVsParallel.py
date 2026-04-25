import time
from loader import load_from_csv
from linear import LinearSearchStrategy
from parallel import ParallelSearchStrategy


def benchmark():
    data = load_from_csv("generatorForSyntheticalData/data/employees_1000000.csv")
    condition = {"field": "salary", "operator": ">", "value": 12000}

    linear_strategy = LinearSearchStrategy()
    parallel_strategy = ParallelSearchStrategy(workers=4)

    start = time.perf_counter()
    linear_results = linear_strategy.search(data, condition)
    linear_time = time.perf_counter() - start

    start = time.perf_counter()
    parallel_results = parallel_strategy.search(data, condition)
    parallel_time = time.perf_counter() - start

    print(f"Linear time: {linear_time:.6f}s")
    print(f"Parallel time: {parallel_time:.6f}s")
    print(f"Equal results: {sorted(r['id'] for r in linear_results) == sorted(r['id'] for r in parallel_results)}")


if __name__ == "__main__":
    benchmark()