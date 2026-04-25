def partition_data(data: list[dict], num_partitions: int) -> list[list[dict]]:
    if num_partitions <= 0:
        raise ValueError("num_partitions musi być większe od 0")

    n = len(data)

    if n == 0:
        return []

    if num_partitions > n:
        num_partitions = n

    base_size = n // num_partitions
    remainder = n % num_partitions

    partitions = []
    start = 0

    for i in range(num_partitions):
        current_size = base_size + (1 if i < remainder else 0)
        end = start + current_size
        partitions.append(data[start:end])
        start = end

    return partitions