from loader import load_from_csv
from linear import LinearSearchStrategy


data = load_from_csv("generatorForSyntheticalData/data/employees_1000.csv")
strategy = LinearSearchStrategy()

condition_1 = {
    "field": "city",
    "operator": "==",
    "value": "Warszawa"
}

condition_2 = {
    "field": "salary",
    "operator": ">",
    "value": 12000
}

condition_3 = {
    "field": "last_name",
    "operator": "contains",
    "value": "ski"
}

results_1 = strategy.search(data, condition_1)
results_2 = strategy.search(data, condition_2)
results_3 = strategy.search(data, condition_3)

print(f"Warszawa: {len(results_1)} wyników")
print(f"Salary > 12000: {len(results_2)} wyników")
print(f"Nazwisko contains 'ski': {len(results_3)} wyników")

print("Przykład wyniku:")
if results_1:
    print(results_1[0])