from loader import load_from_csv
from linear import LinearSearchStrategy


def main():
    data = load_from_csv("generatorForSyntheticalData/data/employees_1000.csv")

    condition = {
        "field": "department",
        "operator": "==",
        "value": "IT"
    }

    strategy = LinearSearchStrategy()
    results = strategy.search(data, condition)

    print(f"Znaleziono {len(results)} rekordów")
    for record in results[:5]:
        print(record)


if __name__ == "__main__":
    main()