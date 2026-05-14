import ray

from partitioning import partition_data
from search_utils import filter_data


import threading
import ray


def ensure_ray_initialized(address: str | None = None) -> None:
    print(
        "[RAY INIT DEBUG]",
        "current_thread=",
        threading.current_thread().name,
        "is_main_thread=",
        threading.current_thread() is threading.main_thread(),
    )

    if not ray.is_initialized():
        if address:
            ray.init(address=address, ignore_reinit_error=True)
        else:
            ray.init(ignore_reinit_error=True)


@ray.remote
def filter_partition_remote(partition: list[dict], condition: dict) -> list[dict]:
    return filter_data(partition, condition)


class DistributedSearchStrategy:
    def __init__(self, workers: int = 4, address: str | None = None):
        if workers <= 0:
            raise ValueError("workers musi być większe od 0")
        self.workers = workers
        self.address = address
        ensure_ray_initialized(address=self.address)

    def search(self, data: list[dict], condition: dict) -> list[dict]:
        if not data:
            return []

        partitions = partition_data(data, self.workers)

        futures = [
            filter_partition_remote.remote(partition, condition)
            for partition in partitions
        ]

        partial_results = ray.get(futures)

        merged = []
        for part in partial_results:
            merged.extend(part)

        return merged