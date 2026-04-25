from concurrent.futures import ProcessPoolExecutor, as_completed
from partitioning import partition_data
from search_utils import filter_data


def filter_partition(partition: list[dict], condition: dict) -> list[dict]:
    return filter_data(partition, condition)


class ParallelSearchStrategy:
    def __init__(self, workers: int = 4):
        if workers <= 0:
            raise ValueError("workers musi być większe od 0")
        self.workers = workers

    def search(self, data: list[dict], condition: dict) -> list[dict]:
        if not data:
            return []

        partitions = partition_data(data, self.workers)
        results = []

        with ProcessPoolExecutor(max_workers=self.workers) as executor:
            futures = [
                executor.submit(filter_partition, partition, condition)
                for partition in partitions
            ]

            for future in as_completed(futures):
                results.extend(future.result())

        return results