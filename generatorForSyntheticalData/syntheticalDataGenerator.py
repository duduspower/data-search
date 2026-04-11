from faker import Faker
import random
import csv
import argparse
from pathlib import Path


fake = Faker("pl_PL")
Faker.seed(42)
random.seed(42)

CITIES = [
    "Warszawa", "Kraków", "Wrocław", "Poznań", "Gdańsk",
    "Łódź", "Katowice", "Lublin", "Białystok", "Rzeszów"
]

DEPARTMENTS = [
    "IT", "HR", "Finance", "Sales", "Marketing", "Operations", "Support"
]

SKILL_LEVELS = ["junior", "mid", "senior", "lead"]


def generate_record(record_id: int) -> dict:
    age = random.randint(22, 65)
    years_experience = random.randint(0, max(0, age - 22))

    skill_level = random.choices(
        SKILL_LEVELS,
        weights=[30, 40, 20, 10],
        k=1
    )[0]

    city = random.choices(
        CITIES,
        weights=[20, 12, 10, 8, 8, 8, 7, 7, 5, 5],
        k=1
    )[0]

    department = random.choices(
        DEPARTMENTS,
        weights=[25, 10, 12, 18, 12, 13, 10],
        k=1
    )[0]

    is_manager = random.random() < 0.12

    base_salary = {
        "junior": 5000,
        "mid": 8000,
        "senior": 12000,
        "lead": 16000
    }[skill_level]

    department_bonus = {
        "IT": 2500,
        "HR": 500,
        "Finance": 1500,
        "Sales": 1800,
        "Marketing": 1200,
        "Operations": 1000,
        "Support": 700
    }[department]

    manager_bonus = 3000 if is_manager else 0
    salary_noise = random.randint(-1000, 1500)

    salary = max(4000, base_salary + department_bonus + manager_bonus + salary_noise)
    join_year = random.randint(2010, 2025)

    return {
        "id": record_id,
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "age": age,
        "city": city,
        "department": department,
        "salary": salary,
        "years_experience": years_experience,
        "is_manager": is_manager,
        "skill_level": skill_level,
        "join_year": join_year
    }


def generate_dataset(n: int) -> list[dict]:
    return [generate_record(i) for i in range(1, n + 1)]


def save_to_csv(data: list[dict], filename: str) -> None:
    if not data:
        raise ValueError("Brak danych do zapisu.")

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generator syntetycznych danych pracowników do benchmarków."
    )
    parser.add_argument(
        "n",
        type=int,
        help="Liczba rekordów do wygenerowania, np. 1000, 10000, 100000"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data",
        help="Folder wyjściowy, domyślnie: data"
    )
    parser.add_argument(
        "--filename",
        type=str,
        default=None,
        help="Opcjonalna nazwa pliku, np. employees_test.csv"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    n = args.n
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = args.filename if args.filename else f"employees_{n}.csv"
    output_path = output_dir / filename

    print(f"Generowanie datasetu: {n} rekordów...")
    data = generate_dataset(n)

    print(f"Zapis do pliku: {output_path}")
    save_to_csv(data, str(output_path))

    print("Gotowe.")
    print(f"Wygenerowano plik: {output_path}")


if __name__ == "__main__":
    main()