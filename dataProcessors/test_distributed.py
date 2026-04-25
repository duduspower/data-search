from loader import load_from_csv
from linear import LinearSearchStrategy
from distributed import DistributedSearchStrategy


def extract_ids(records: list[dict]) -> list[int]:
    return sorted(record["id"] for record in records)


def main():
    data = load_from_csv("generatorForSyntheticalData/data/employees_1000.csv")

    conditions = [
        {"field": "city", "operator": "==", "value": "Warszawa"},
        {"field": "salary", "operator": ">", "value": 12000},
        {"field": "id", "operator": "==", "value": 100},
        {"field": "last_name", "operator": "contains", "value": "ski"},
    ]

    linear_strategy = LinearSearchStrategy()
    distributed_strategy = DistributedSearchStrategy(workers=4)

    for condition in conditions:
        linear_results = linear_strategy.search(data, condition)
        distributed_results = distributed_strategy.search(data, condition)

        print(f"\nCondition: {condition}")
        print(f"Linear count: {len(linear_results)}")
        print(f"Distributed count: {len(distributed_results)}")
        print(f"Equal ids: {extract_ids(linear_results) == extract_ids(distributed_results)}")


if __name__ == "__main__":
    main()