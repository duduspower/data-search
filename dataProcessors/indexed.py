from search_utils import filter_data


class IndexedSearchStrategy:
    def __init__(self, index_field: str):
        self.index_field = index_field
        self.index: dict = {}
        self.index_built = False

    def build_index(self, data: list[dict]) -> None:
        self.index.clear()

        for record in data:
            key = record.get(self.index_field)
            self.index.setdefault(key, []).append(record)

        self.index_built = True

    def search(self, data: list[dict], condition: dict) -> list[dict]:
        field = condition["field"]
        operator_symbol = condition["operator"]
        expected_value = condition["value"]

        # Jeśli indeks nie jest jeszcze zbudowany, budujemy go przy pierwszym użyciu
        if not self.index_built:
            self.build_index(data)

        # Szybka ścieżka tylko dla zapytań równościowych po indeksowanym polu
        if field == self.index_field and operator_symbol == "==":
            return self.index.get(expected_value, [])

        # Fallback dla innych zapytań
        return filter_data(data, condition)