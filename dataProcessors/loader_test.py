from loader import load_from_csv

data = load_from_csv("generatorForSyntheticalData/data/employees_1000.csv")

print(f"Liczba rekordów: {len(data)}")
print(data[0])
print(type(data[0]["id"]))
print(type(data[0]["salary"]))
print(type(data[0]["is_manager"]))