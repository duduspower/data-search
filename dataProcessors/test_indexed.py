from loader import load_from_csv
from linear import LinearSearchStrategy
from indexed import IndexedSearchStrategy


def extract_ids(records: list[dict]) -> list[int]:
    return sorted(record["id"] for record in records)


def main():
    data = load_from_csv("generatorForSyntheticalData/data/employees_10000.csv")

    linear_strategy = LinearSearchStrategy()
    indexed_strategy = IndexedSearchStrategy(index_field="city")

    condition = {
        "field": "city",
        "operator": "==",
        "value": "Warszawa"
    }

    linear_results = linear_strategy.search(data, condition)
    indexed_results = indexed_strategy.search(data, condition)

    print(f"Linear: {len(linear_results)} wyników")
    print(f"Indexed: {len(indexed_results)} wyników")
    print("Czy wyniki są identyczne?")
    print(extract_ids(linear_results) == extract_ids(indexed_results))


if __name__ == "__main__":
    main()