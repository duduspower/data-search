from partitioning import partition_data


def print_partition_info(data, num_partitions):
    partitions = partition_data(data, num_partitions)

    print(f"\nDane: {data}")
    print(f"Liczba partycji: {num_partitions}")
    print(f"Rozmiary partycji: {[len(p) for p in partitions]}")
    print(f"Partycje: {partitions}")


data1 = list(range(10))
print_partition_info(data1, 3)

data2 = list(range(100))
print_partition_info(data2, 4)

data3 = list(range(5))
print_partition_info(data3, 10)