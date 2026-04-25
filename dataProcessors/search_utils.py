from operator import eq, ne, gt, ge, lt, le


OPERATOR_MAP = {
    "==": eq,
    "!=": ne,
    ">": gt,
    ">=": ge,
    "<": lt,
    "<=": le,
    "contains": lambda a, b: b in a if a is not None else False,
}


def filter_data(data: list[dict], condition: dict) -> list[dict]:
    field = condition["field"]
    operator_symbol = condition["operator"]
    expected_value = condition["value"]

    if operator_symbol not in OPERATOR_MAP:
        raise ValueError(f"Nieobsługiwany operator: {operator_symbol}")

    op = OPERATOR_MAP[operator_symbol]
    results = []

    for record in data:
        actual_value = record.get(field)

        try:
            if op(actual_value, expected_value):
                results.append(record)
        except Exception:
            pass

    return results