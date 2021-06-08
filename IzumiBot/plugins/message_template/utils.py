import ast
from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Any, Dict, Type

from .exceptions import TemplateContextError


@dataclass(frozen=True)
class Evaluation:
    class ResultType(IntEnum):
        LITERAL = auto()
        NAME = auto()

    @classmethod
    def eval(cls: Type["Evaluation"], expression: str) -> "Evaluation":
        try:
            return cls(type=cls.ResultType.LITERAL, result=ast.literal_eval(expression))
        except (ValueError, SyntaxError):
            return cls(type=cls.ResultType.NAME, result=expression)

    def resolve(self, context: Dict[str, Any]) -> Any:
        return (
            self.result
            if self.type is Evaluation.ResultType.LITERAL
            else resolve(self.result, context)
        )

    type: ResultType
    result: Any


def resolve(name: str, context: Dict[str, Any]) -> Any:
    if name.startswith(".."):
        context = context.get("..", {})
        name = name[2:]

    def extract(name: str, data: Any) -> Any:
        if isinstance(data, dict) and name in data:
            return data[name]
        elif isinstance(data, list) and name.isdigit() and int(name) < len(data):
            return data[int(name)]
        elif hasattr(data, name):
            return getattr(data, name)
        raise ValueError(f"key {name!r} does not exist in {data!r}.")

    try:
        for token in name.split("."):
            context = extract(token, context)
        return context
    except (KeyError, IndexError, TypeError, ValueError) as e:
        raise TemplateContextError(name) from e
