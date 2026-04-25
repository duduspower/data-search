from search_utils import filter_data


class LinearSearchStrategy:
    def search(self, data: list[dict], condition: dict) -> list[dict]:
        return filter_data(data, condition)