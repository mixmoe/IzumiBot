import operator
import re
from abc import ABCMeta, abstractmethod
from enum import IntEnum, auto
from typing import Any, Callable, Dict, List, Optional, TypedDict

from .exceptions import TemplateError, TemplateSyntaxError
from .utils import Evaluation, resolve

T_Filter = Callable[[Any], str]


class RootContext(TypedDict, total=False):
    _filters: Dict[str, T_Filter]
    _default_filter: Optional[str]


VAR_TOKEN_START, VAR_TOKEN_END = "{{", "}}"
BLOCK_TOKEN_START, BLOCK_TOKEN_END = "{%", "%}"

FRAGMENT_MATCH = re.compile(
    r"^(?:%s|%s)(?P<command>.*?)(?:%s|%s)$"
    % (VAR_TOKEN_START, BLOCK_TOKEN_START, VAR_TOKEN_END, BLOCK_TOKEN_END)
)
TOKEN_SEPERATOR = re.compile(
    r"(%s.*?%s|%s.*?%s)"
    % (VAR_TOKEN_START, VAR_TOKEN_END, BLOCK_TOKEN_START, BLOCK_TOKEN_END),
)
WHITESPACE = re.compile(r"\s+")

OPERATORS_TAB: Dict[str, Callable[[Any, Any], bool]] = {
    "<": operator.lt,
    ">": operator.gt,
    "==": operator.eq,
    "!=": operator.ne,
    "<=": operator.le,
    ">=": operator.ge,
}


class FragmentType(IntEnum):
    VAR = auto()
    OPEN_BLOCK = auto()
    CLOSE_BLOCK = auto()
    TEXT = auto()


class Fragment(object):
    def __init__(self, raw_text: str):
        self.raw = raw_text

        match = FRAGMENT_MATCH.match(raw_text.strip())
        self.matched = match.group() if match else None
        self.clean = match.group("command").strip() if match else self.raw

    @property
    def type(self) -> FragmentType:
        if self.matched is None:
            return FragmentType.TEXT
        elif self.matched.startswith(BLOCK_TOKEN_START):
            if self.clean.startswith("end"):
                return FragmentType.CLOSE_BLOCK
            else:
                return FragmentType.OPEN_BLOCK
        elif self.matched.startswith(VAR_TOKEN_START):
            return FragmentType.VAR
        raise TemplateSyntaxError(self)

    def __repr__(self) -> str:
        return f"<{type(self).__qualname__} at 0x{id(self):x}, {self.raw=}>"


class Node(metaclass=ABCMeta):
    creates_scope: bool = False

    def __init__(
        self,
        fragment: Optional[Fragment] = None,
        parent: Optional["Node"] = None,
    ):
        self.parent = parent
        self.children: List["Node"] = []
        self.fragment = fragment
        if fragment is not None:
            self.process_fragment(fragment)

    @property
    def root(self) -> "Root":
        root = self if self.parent is None else self.parent.root
        if not isinstance(root, Root):
            raise TemplateError("hanging syntax tree, root is not inherit from Root")
        return root

    def process_fragment(self, fragment: Fragment):
        ...

    def enter_scope(self):
        ...

    def exit_scope(self):
        ...

    @abstractmethod
    def render(self, context: Dict[str, Any]):
        raise NotImplementedError

    def render_children(
        self, context: Dict[str, Any], children: Optional[List["Node"]] = None
    ):
        def render_child(child: "Node"):
            child_html = child.render(context)
            return "" if not child_html else str(child_html)

        children = self.children if children is None else children

        return "".join(map(render_child, children))

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self.children=})"


class ScopableNode(Node):
    creates_scope = True


class Root(Node):
    context = None

    def render(self, context: RootContext):  # type:ignore
        self.context = context
        return self.render_children(context)  # type:ignore


class Variable(Node):
    def process_fragment(self, fragment: Fragment):
        self.name = fragment.clean

    def render(self, context: Dict[str, Any]):
        assert self.root.context is not None

        filter: Optional[str]
        if "|" in self.name:
            name, filter = self.name.split("|", 1)
            name, filter = name.strip(), filter.strip()
        else:
            name, filter = self.name, self.root.context.get("_default_filter")

        result = resolve(name, context)
        if filter is not None:
            try:
                filter_func = self.root.context["_filters"][filter]
            except KeyError:
                raise TemplateError(f"filter {filter} does not exist in context.")
            result = filter_func(result)

        if self.fragment and self.fragment.matched:
            return self.fragment.raw.replace(self.fragment.matched, str(result))
        else:
            return result


class Each(ScopableNode):
    MATCH_REGEX = re.compile(
        r"^each\s+(?P<item>\w+?)\s+in\s+(?P<iterator>.+?)(?:\s+max\s+(?P<max>.+?))?$"
    )

    def process_fragment(self, fragment: Fragment):
        matched = self.MATCH_REGEX.match(fragment.clean)
        if matched is None:
            raise TemplateSyntaxError(fragment)
        self.item_name = matched.group("item")

        iterator = matched.group("iterator")
        max = matched.group("max")
        try:
            self.it = Evaluation.eval(iterator)
            self.max = Evaluation.eval(max) if max is not None else None
        except ValueError as e:
            raise TemplateSyntaxError(fragment) from e

    def render(self, context: Dict[str, Any]):
        max = None if self.max is None else int(self.max.resolve(context))
        items: List[Any] = [*self.it.resolve(context)]

        return "".join(
            map(
                lambda item: self.render_children(
                    {"..": context, self.item_name: item}
                ),
                items if max is None else items[:max],
            )
        )


class If(ScopableNode):
    def process_fragment(self, fragment: Fragment):
        bits = fragment.clean.split()[1:]
        if len(bits) not in (1, 3):
            raise TemplateSyntaxError(fragment)
        self.lhs = Evaluation.eval(bits[0])
        if len(bits) == 3:
            self.op = bits[1]
            self.rhs = Evaluation.eval(bits[2])

    def render(self, context: Dict[str, Any]):
        lhs = self.resolve_side(self.lhs, context)
        if hasattr(self, "op"):
            op = OPERATORS_TAB.get(self.op)
            if op is None:
                raise TemplateSyntaxError(self.op)
            rhs = self.resolve_side(self.rhs, context)
            exec_if_branch = op(lhs, rhs)
        else:
            exec_if_branch = operator.truth(lhs)
        if_branch, else_branch = self.split_children()
        return self.render_children(
            context, self.if_branch if exec_if_branch else self.else_branch
        )

    def resolve_side(self, side: Evaluation, context: Dict[str, Any]):
        return side.resolve(context)

    def exit_scope(self):
        self.if_branch, self.else_branch = self.split_children()

    def split_children(self):
        if_branch, else_branch = [], []
        cursor = if_branch
        for child in self.children:
            if isinstance(child, Else):
                cursor = else_branch
                continue
            cursor.append(child)
        return if_branch, else_branch


class Else(Node):
    def render(self, context: Dict[str, Any]):
        pass


class Call(Node):
    def process_fragment(self, fragment: Fragment):
        try:
            _, call, *args = WHITESPACE.split(fragment.clean)
            self.callable = call
            self.args, self.kwargs = self._parse_params(args)
        except (ValueError, IndexError):
            raise TemplateSyntaxError(fragment)

    def _parse_params(self, params: List[str]):
        args: List[Evaluation] = []
        kwargs: Dict[str, Evaluation] = {}
        for param in params:
            if "=" in param:
                name, value = param.split("=", 1)
                kwargs[name] = Evaluation.eval(value)
            else:
                args.append(Evaluation.eval(param))
        return args, kwargs

    def render(self, context: Dict[str, Any]):
        resolved_args, resolved_kwargs = [], {}
        for result in self.args:
            resolved_args.append(result.resolve(context))
        for key, result in self.kwargs.items():
            resolved_kwargs[key] = result.resolve(context)
        resolved_callable = resolve(self.callable, context)
        if not callable(resolved_callable):
            raise TemplateError(f"{self.callable} is not callable.")
        return resolved_callable(*resolved_args, **resolved_kwargs)


class Text(Node):
    def process_fragment(self, fragment: Fragment):
        self.text = fragment.raw

    def render(self, context: Dict[str, Any]):
        return self.text
