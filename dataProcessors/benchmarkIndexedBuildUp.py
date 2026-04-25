import time
from loader import load_from_csv
from linear import LinearSearchStrategy
from indexed import IndexedSearchStrategy


def main():
    data = load_from_csv("generatorForSyntheticalData/data/employees_100000.csv")
    condition = {
        "field": "city",
        "operator": "==",
        "value": "Warszawa"
    }

    linear_strategy = LinearSearchStrategy()

    start = time.perf_counter()
    linear_results = linear_strategy.search(data, condition)
    linear_time = time.perf_counter() - start

    indexed_strategy = IndexedSearchStrategy(index_field="city")

    start = time.perf_counter()
    indexed_strategy.build_index(data)
    index_build_time = time.perf_counter() - start

    start = time.perf_counter()
    indexed_results = indexed_strategy.search(data, condition)
    indexed_search_time = time.perf_counter() - start

    print(f"Linear search time: {linear_time:.6f}s")
    print(f"Index build time: {index_build_time:.6f}s")
    print(f"Indexed search time: {indexed_search_time:.6f}s")
    print(f"Equal results: {sorted(r['id'] for r in linear_results) == sorted(r['id'] for r in indexed_results)}")


if __name__ == "__main__":
    main()