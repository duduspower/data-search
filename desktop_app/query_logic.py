from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from repo_paths import configure_imports


configure_imports()

from indexed import IndexedSearchStrategy
from linear import LinearSearchStrategy
from parallel import ParallelSearchStrategy


class Condition:
    def __and__(self, other: "Condition") -> "AndCondition":
        return AndCondition.of(self, other)

    def __or__(self, other: "Condition") -> "OrCondition":
        return OrCondition.of(self, other)


@dataclass(frozen=True)
class ComparisonCondition(Condition):
    field: str
    operator: str
    value: Any

    def to_person2_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "operator": "==" if self.operator == "=" else self.operator,
            "value": self.value,
        }


@dataclass(frozen=True)
class AndCondition(Condition):
    conditions: tuple[Condition, ...]

    @classmethod
    def of(cls, *conditions: Condition) -> "AndCondition":
        flattened = []
        for condition in conditions:
            if isinstance(condition, AndCondition):
                flattened.extend(condition.conditions)
            else:
                flattened.append(condition)
        return cls(tuple(flattened))


@dataclass(frozen=True)
class OrCondition(Condition):
    conditions: tuple[Condition, ...]

    @classmethod
    def of(cls, *conditions: Condition) -> "OrCondition":
        flattened = []
        for condition in conditions:
            if isinstance(condition, OrCondition):
                flattened.extend(condition.conditions)
            else:
                flattened.append(condition)
        return cls(tuple(flattened))


@dataclass(frozen=True)
class Field:
    name: str

    def __eq__(self, value: Any) -> ComparisonCondition:  # type: ignore[override]
        return ComparisonCondition(self.name, "==", value)

    def __ne__(self, value: Any) -> ComparisonCondition:  # type: ignore[override]
        return ComparisonCondition(self.name, "!=", value)

    def __gt__(self, value: Any) -> ComparisonCondition:
        return ComparisonCondition(self.name, ">", value)

    def __ge__(self, value: Any) -> ComparisonCondition:
        return ComparisonCondition(self.name, ">=", value)

    def __lt__(self, value: Any) -> ComparisonCondition:
        return ComparisonCondition(self.name, "<", value)

    def __le__(self, value: Any) -> ComparisonCondition:
        return ComparisonCondition(self.name, "<=", value)

    def contains(self, value: Any) -> ComparisonCondition:
        return ComparisonCondition(self.name, "contains", value)

    def isin(self, values: Iterable[Any]) -> OrCondition:
        return OrCondition.of(*(self == value for value in values))


def field(name: str) -> Field:
    return Field(name)


def record_key(record: dict[str, Any]) -> Any:
    if "id" in record:
        return ("id", record["id"])
    return tuple(sorted(record.items()))


class SearchEngine:
    def available_strategies(self) -> list[str]:
        return ["indexed", "linear", "parallel"]

    def create_strategy(self, name: str, **options: Any):
        if name == "linear":
            return LinearSearchStrategy()
        if name == "indexed":
            return IndexedSearchStrategy(index_field=options.get("index_field", "id"))
        if name == "parallel":
            return ParallelSearchStrategy(workers=options.get("workers", 2))
        raise ValueError(f"Nieznana strategia: {name}")

    def search(
        self,
        data: list[dict[str, Any]],
        condition: Condition,
        strategy: str = "linear",
        **strategy_options: Any,
    ) -> list[dict[str, Any]]:
        return self._execute(data, condition, strategy, strategy_options)

    def _execute(
        self,
        data: list[dict[str, Any]],
        condition: Condition,
        strategy_name: str,
        strategy_options: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if isinstance(condition, ComparisonCondition):
            strategy = self.create_strategy(strategy_name, **strategy_options)
            return strategy.search(data, condition.to_person2_dict())

        if isinstance(condition, AndCondition):
            matching_keys: set[Any] | None = None
            for child in condition.conditions:
                child_keys = {
                    record_key(record)
                    for record in self._execute(data, child, strategy_name, strategy_options)
                }
                matching_keys = child_keys if matching_keys is None else matching_keys & child_keys
            if matching_keys is None:
                return []
            return [record for record in data if record_key(record) in matching_keys]

        if isinstance(condition, OrCondition):
            matching_keys: set[Any] = set()
            for child in condition.conditions:
                matching_keys.update(
                    record_key(record)
                    for record in self._execute(data, child, strategy_name, strategy_options)
                )
            return [record for record in data if record_key(record) in matching_keys]

        raise TypeError(f"Nieobslugiwany typ warunku: {type(condition).__name__}")

