from loader import load_from_csv
from linear import LinearSearchStrategy
from parallel import ParallelSearchStrategy


def extract_ids(records: list[dict]) -> list[int]:
    return sorted(record["id"] for record in records)


data = load_from_csv("generatorForSyntheticalData/data/employees_1000.csv")

condition = {
    "field": "department",
    "operator": "==",
    "value": "IT"
}

linear_strategy = LinearSearchStrategy()
parallel_strategy = ParallelSearchStrategy(workers=4)

linear_results = linear_strategy.search(data, condition)
parallel_results = parallel_strategy.search(data, condition)

print(f"Linear: {len(linear_results)} wyników")
print(f"Parallel: {len(parallel_results)} wyników")

print("Czy liczba wyników jest taka sama?")
print(len(linear_results) == len(parallel_results))

print("Czy identyfikatory rekordów są takie same?")
print(extract_ids(linear_results) == extract_ids(parallel_results))