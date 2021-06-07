import ast
from typing import Any, Dict, Type
from enum import IntEnum, auto
from dataclasses import dataclass

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

    type: ResultType
    result: Any


def resolve(name: str, context: Dict[str, Any]) -> Any:
    if name.startswith(".."):
        context = context.get("..", {})
        name = name[2:]
    try:
        for tok in name.split("."):
            context = context[tok]
        return context
    except KeyError:
        raise TemplateContextError(name)
