from loader import load_from_csv
from linear import LinearSearchStrategy
from indexed import IndexedSearchStrategy


def extract_ids(records: list[dict]) -> list[int]:
    return sorted(record["id"] for record in records)


def run_test(data, condition, indexed_field):
    linear_strategy = LinearSearchStrategy()
    indexed_strategy = IndexedSearchStrategy(index_field=indexed_field)

    linear_results = linear_strategy.search(data, condition)
    indexed_results = indexed_strategy.search(data, condition)

    print(f"\nCondition: {condition}")
    print(f"Linear count: {len(linear_results)}")
    print(f"Indexed count: {len(indexed_results)}")
    print(f"Equal ids: {extract_ids(linear_results) == extract_ids(indexed_results)}")


def main():
    data = load_from_csv("generatorForSyntheticalData/data/employees_1000.csv")

    run_test(
        data,
        {"field": "city", "operator": "==", "value": "Warszawa"},
        indexed_field="city"
    )

    run_test(
        data,
        {"field": "salary", "operator": ">", "value": 12000},
        indexed_field="city"
    )

    run_test(
        data,
        {"field": "department", "operator": "==", "value": "IT"},
        indexed_field="department"
    )


if __name__ == "__main__":
    main()